# ============================
# API MundoTEA — Arquivo Único
# Flask + PostgreSQL + JWT + CORS + Flask-RESTful
# ============================

from flask import Flask, request, jsonify
from flask_restful import Resource, Api
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token
import psycopg2
import bcrypt
from datetime import timedelta
import json

# ============================
# CONFIGURAÇÃO
# ============================

DB_HOST = "localhost"
DB_NAME = "MundoTea"
DB_USER = "postgres"
DB_PASSWORD = "1234"
SECRET_KEY = "chave_super_secreta"

# ============================
# FUNÇÃO DE CONEXÃO
# ============================

def get_conn():
    return psycopg2.connect(
        dbname=DB_NAME, user=DB_USER,
        password=DB_PASSWORD, host=DB_HOST
    )

# ============================
# INICIAR APP
# ============================

app = Flask(__name__)
CORS(app)
api = Api(app)

app.config["JWT_SECRET_KEY"] = SECRET_KEY
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=1)
jwt = JWTManager(app)

# ============================
# FUNÇÕES DE AUTENTICAÇÃO
# ============================

def hash_senha(senha):
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()

def verificar_senha(senha, senha_hash):
    return bcrypt.checkpw(senha.encode(), senha_hash.encode())

# ============================
# RECURSOS
# ============================

# ===== HOME =====
class Home(Resource):
    def get(self):
        return {"status": "API MundoTEA funcionando!"}, 200

# ===== LOGIN E CADASTRO =====
class Registrar(Resource):
    def post(self):
        data = request.json

        # Campos obrigatórios
        email = data.get("email")
        senha = data.get("senha")
        nome_crianca = data.get("nome_crianca")
        data_nascimento = data.get("data_nascimento")
        nivel_autismo = data.get("nivel_autismo")
        nome_pai = data.get("pai")
        nome_mae = data.get("mae")
        telefone_responsavel = data.get("telefone_resp")
        email_responsavel = data.get("email_resp")

        # Campo opcional
        necessidades = data.get("necessidades")

        # Validar campos obrigatórios
        obrigatorios = [email, senha, nome_crianca, data_nascimento,
                        nivel_autismo, nome_pai, nome_mae,
                        telefone_responsavel, email_responsavel]
        if not all(obrigatorios):
            return {"erro": "Todos os campos obrigatórios devem ser preenchidos!"}, 400

        conn = get_conn()
        cur = conn.cursor()

        # Verificar se email já existe
        cur.execute("SELECT email FROM login WHERE email=%s", (email,))
        if cur.fetchone():
            cur.close()
            conn.close()
            return {"erro": "Email já cadastrado"}, 400

        # Criar login
        senha_hash = hash_senha(senha)
        cur.execute("""
            INSERT INTO login (email, senha_hash)
            VALUES (%s, %s) RETURNING login_id
        """, (email, senha_hash))
        login_id = cur.fetchone()[0]

        # Inserir dados da criança e dos responsáveis
        cur.execute("""
            INSERT INTO crianca (
                login_id, nome, data_nascimento, nivel_autismo, necessidades,
                nome_pai, nome_mae, telefone_responsavel, email_responsavel
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            login_id, nome_crianca, data_nascimento, nivel_autismo, necessidades,
            nome_pai, nome_mae, telefone_responsavel, email_responsavel
        ))

        conn.commit()
        cur.close()
        conn.close()

        # Gerar token JWT
        token = create_access_token(identity=login_id)
        return {"mensagem": "Cadastro realizado com sucesso!", "token": token}, 201

class Login(Resource):
    def post(self):
        data = request.json
        email = data.get("email")
        senha = data.get("senha")

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT login_id, senha_hash FROM login WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if not user:
            return {"erro": "Usuário não existe"}, 404

        login_id, senha_hash = user
        if not verificar_senha(senha, senha_hash):
            return {"erro": "Senha incorreta"}, 401

        token = create_access_token(identity=login_id)
        return {"token": token}, 200

# ===== CRIAR ATIVIDADE =====
class CriarAtividade(Resource):
    @jwt_required()
    def post(self):
        data = request.json

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO atividades (
                titulo, descricao, categoria, dificuldade, tempo_estimado_min, recursos
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING atividade_id
        """, (
            data["titulo"],
            data.get("descricao"),
            data.get("categoria"),
            data.get("dificuldade"),
            data.get("tempo_estimado_min"),
            json.dumps(data.get("recursos")) if data.get("recursos") else None
        ))

        atividade_id = cur.fetchone()[0]

        conn.commit()
        cur.close()
        conn.close()

        return {"atividade_id": atividade_id}, 201

# ===== LISTAR ATIVIDADES =====
class ListarAtividades(Resource):
    def get(self):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT atividade_id, titulo, descricao, categoria, dificuldade,
                   tempo_estimado_min, recursos
            FROM atividades
            WHERE ativo=true
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        atividades = []
        for r in rows:
            atividades.append({
                "atividade_id": r[0],
                "titulo": r[1],
                "descricao": r[2],
                "categoria": r[3],
                "dificuldade": r[4],
                "tempo_estimado_min": r[5],
                "recursos": json.loads(r[6]) if r[6] else None
            })

        return {"atividades": atividades}, 200

# ============================
# ADICIONAR RECURSOS AO API
# ============================

api.add_resource(Home, "/")
api.add_resource(Registrar, "/registrar")
api.add_resource(Login, "/login")
api.add_resource(CriarAtividade, "/atividades")
api.add_resource(ListarAtividades, "/atividades/listar")

# ============================
# EXECUÇÃO
# ============================

if __name__ == "__main__":
    app.run(debug=True)

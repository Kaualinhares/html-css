# api_mundotea.py
"""
API MundoTEA - Visualização de perfil apenas
Flask + Flask-RESTful + Flask-JWT-Extended + psycopg2 + CORS
"""

import base64
import uuid
from flask import Flask, request, jsonify
from flask_restful import Resource, Api
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import psycopg2
import bcrypt
from datetime import timedelta
import os

# -----------------------
# CONFIGURAÇÃO
# -----------------------
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "MundoTea")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "1234")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "chave_super_secreta")
JWT_EXPIRES_DAYS = int(os.getenv("JWT_EXPIRES_DAYS", "1"))

API_ALLOWED_ORIGINS = [
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]

# -----------------------
# UTIL - conexão
# -----------------------
def get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

def dict_from_row(row, cols):
    return {cols[i]: row[i] for i in range(len(cols))}

# -----------------------
# APP
# -----------------------
app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=JWT_EXPIRES_DAYS)

CORS(app, resources={r"/*": {"origins": API_ALLOWED_ORIGINS}})
api = Api(app)
jwt = JWTManager(app)

# -----------------------
# HELPERS DE SENHA
# -----------------------
def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verificar_senha(senha: str, senha_hash: str) -> bool:
    return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))

# -----------------------
# ENDPOINTS
# -----------------------
class Home(Resource):
    def get(self):
        return {"status": "API MundoTEA funcionando!"}, 200

class Registrar(Resource):
    def post(self):
        data = request.get_json(force=True)
        email = data.get("email")
        senha = data.get("senha")
        nome_crianca = data.get("nome_crianca") or data.get("nome")
        data_nascimento = data.get("data_nascimento")
        nivel_autismo = data.get("nivel_autismo")
        nome_pai = data.get("pai") or data.get("nome_pai")
        nome_mae = data.get("mae") or data.get("nome_mae")
        telefone_responsavel = data.get("telefone_resp") or data.get("telefone_responsavel")
        email_responsavel = data.get("email_resp") or data.get("email_responsavel")

        # Verifica campos obrigatórios
        obrigatorios = [email, senha, nome_crianca, data_nascimento,
                        nivel_autismo, nome_pai, nome_mae, telefone_responsavel, email_responsavel]
        if not all(obrigatorios):
            return {"erro": "Todos os campos obrigatórios devem ser preenchidos!"}, 400

        conn = get_conn()
        cur = conn.cursor()
        try:
            # Verifica se email já existe
            cur.execute("SELECT login_id FROM login WHERE email = %s", (email,))
            if cur.fetchone():
                return {"erro": "Email já cadastrado"}, 400

            # Cria login
            senha_hash = hash_senha(senha)
            cur.execute(
                "INSERT INTO login (email, senha_hash) VALUES (%s, %s) RETURNING login_id",
                (email, senha_hash)
            )
            login_id = cur.fetchone()[0]

            # Cria criança
            cur.execute("""
                INSERT INTO crianca (
                    login_id, nome, data_nascimento, nivel_autismo,
                    nome_pai, nome_mae, telefone_responsavel, email_responsavel
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING crianca_id
            """, (
                login_id, nome_crianca, data_nascimento,
                int(nivel_autismo),
                nome_pai, nome_mae, telefone_responsavel, email_responsavel
            ))
            crianca_id = cur.fetchone()[0]

            # -------------------------------
            # Conquistas iniciais
            # -------------------------------
            conquistas_iniciais = ["Primeira Sessão", "Primeiro Colorir", "Primeiro Quebra-Cabeça"]
            for nome_conquista in conquistas_iniciais:
                cur.execute("""
                    INSERT INTO conquistas(crianca_id, nome, atingido)
                    VALUES (%s, %s, %s)
                    ON CONFLICT(crianca_id, nome) DO NOTHING
                """, (crianca_id, nome_conquista, False))

            # -------------------------------
            # Preferências iniciais
            # -------------------------------
            preferencias_iniciais = {"tema": "claro", "som": "on", "dificuldade": "1"}
            for chave, valor in preferencias_iniciais.items():
                cur.execute("""
                    INSERT INTO preferencias(crianca_id, chave, valor)
                    VALUES (%s, %s, %s)
                    ON CONFLICT(crianca_id, chave) DO NOTHING
                """, (crianca_id, chave, valor))

            # -------------------------------
            # Recomendações iniciais
            # -------------------------------
            cur.execute("SELECT atividade_id FROM atividades")
            atividades = cur.fetchall()
            for (atividade_id,) in atividades:
                cur.execute("""
                    INSERT INTO recomendacoes(crianca_id, atividade_id, score, versao_algoritmo)
                    VALUES (%s, %s, %s, %s)
                """, (crianca_id, atividade_id, 0, "v1"))

            # Commit final
            conn.commit()

            # Cria token JWT
            token = create_access_token(identity=str(login_id))
            return {
                "mensagem": "Cadastro realizado com sucesso!",
                "token": token,
                "login_id": login_id,
                "crianca_id": crianca_id
            }, 201

        except Exception as e:
            conn.rollback()
            return {"erro": "Erro interno ao cadastrar", "detalhes": str(e)}, 500
        finally:
            cur.close()
            conn.close()


class Login(Resource):
    def post(self):
        data = request.get_json(force=True)
        email = data.get("email")
        senha = data.get("senha")
        if not email or not senha:
            return {"erro": "Email e senha são obrigatórios"}, 400

        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute("SELECT login_id, senha_hash, ativo FROM login WHERE email = %s", (email,))
            row = cur.fetchone()
            if not row:
                return {"erro": "Usuário não existe"}, 404

            login_id, senha_hash, ativo = row
            if not ativo:
                return {"erro": "Conta desativada"}, 403

            if not verificar_senha(senha, senha_hash):
                return {"erro": "Senha incorreta"}, 401

            token = create_access_token(identity=str(login_id))
            return {"token": token, "login_id": login_id}, 200

        finally:
            cur.close()
            conn.close()

class Perfil(Resource):
    @jwt_required()
    def get(self):
        # login_id do JWT
        login_id = int(get_jwt_identity())  # garante que seja inteiro
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT c.nome AS nome_crianca, c.data_nascimento, c.nivel_autismo,
                       c.nome_pai, c.nome_mae, c.telefone_responsavel, c.email_responsavel,
                       l.email AS email_login
                FROM crianca c
                INNER JOIN login l ON c.login_id = l.login_id
                WHERE c.login_id = %s
            """, (login_id,))
            row = cur.fetchone()
            if not row:
                return {"erro": "Usuário não encontrado"}, 404

            cols = ["nome_crianca","data_nascimento","nivel_autismo",
                    "nome_pai","nome_mae","telefone_responsavel","email_responsavel","email_login"]
            perfil = dict_from_row(row, cols)

            # transforma date em string
            if perfil.get("data_nascimento"):
                perfil["data_nascimento"] = perfil["data_nascimento"].isoformat()

            return perfil, 200
        finally:
            cur.close()
            conn.close()

class AtualizarPerfil(Resource):
    @jwt_required()
    def put(self):
        login_id = int(get_jwt_identity())
        data = request.get_json(force=True)

        nome = data.get("nome")
        data_nascimento = data.get("data_nascimento")
        nivel_autismo = data.get("nivel_autismo")
        nome_pai = data.get("nome_pai")
        nome_mae = data.get("nome_mae")
        telefone_responsavel = data.get("telefone_responsavel")
        email_responsavel = data.get("email_responsavel")

        # Validação simples
        obrigatorios = [nome, data_nascimento, nivel_autismo, nome_pai, nome_mae, telefone_responsavel, email_responsavel]
        if not all(obrigatorios):
            return {"erro": "Todos os campos obrigatórios devem ser preenchidos"}, 400

        conn = get_conn()
        cur = conn.cursor()

        try:
            cur.execute("""
                UPDATE crianca
                SET nome = %s,
                    data_nascimento = %s,
                    nivel_autismo = %s,
                    nome_pai = %s,
                    nome_mae = %s,
                    telefone_responsavel = %s,
                    email_responsavel = %s
                WHERE login_id = %s
            """, (
                nome,
                data_nascimento,
                int(nivel_autismo),
                nome_pai,
                nome_mae,
                telefone_responsavel,
                email_responsavel,
                login_id
            ))

            if cur.rowcount == 0:
                return {"erro": "Usuário não encontrado"}, 404

            conn.commit()
            return {"mensagem": "Perfil atualizado com sucesso!"}, 200

        except Exception as e:
            conn.rollback()
            return {"erro": "Erro ao atualizar perfil", "detalhes": str(e)}, 500

        finally:
            cur.close()
            conn.close()

class CriarSessao(Resource):
    @jwt_required()
    def post(self):
        login_id = int(get_jwt_identity())
        data = request.get_json(force=True)
        atividade_id = data.get("atividade_id")

        if not atividade_id:
            return {"erro":"atividade_id é obrigatório"},400

        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute("SELECT crianca_id FROM crianca WHERE login_id=%s",(login_id,))
            crianca_id = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO sessoes(crianca_id,atividade_id)
                VALUES(%s,%s) RETURNING sessao_id
            """,(crianca_id,atividade_id))
            sessao_id = cur.fetchone()[0]
            conn.commit()
            return {"sessao_id":sessao_id},201
        finally:
            cur.close()
            conn.close()
            
class AtualizarSessao(Resource):
    @jwt_required()
    def put(self):
        data = request.get_json(force=True)
        sessao_id = data.get("sessao_id")
        tempo_gasto = data.get("tempo_gasto_segundos", 0)
        score = data.get("score", 0)
        acuracia = data.get("acuracia", 0)

        if not sessao_id:
            return {"erro": "sessao_id é obrigatório"}, 400

        conn = get_conn()
        cur = conn.cursor()
        try:
            # Atualiza a sessão
            cur.execute("""
                UPDATE sessoes
                SET terminado_em = now(), tempo_gasto_segundos = %s, score = %s, acuracia = %s
                WHERE sessao_id = %s
            """, (tempo_gasto, score, acuracia, sessao_id))

            # Pega crianca_id e título da atividade dessa sessão
            cur.execute("""
                SELECT s.crianca_id, a.titulo
                FROM sessoes s
                INNER JOIN atividades a ON s.atividade_id = a.atividade_id
                WHERE s.sessao_id = %s
            """, (sessao_id,))
            row = cur.fetchone()
            if row:
                crianca_id, titulo_atividade = row

                # Exemplo: se o título for "Colorir", desbloqueia conquista "Primeiro Colorir"
                if titulo_atividade == "Colorir":
                    cur.execute("""
                        UPDATE conquistas
                        SET atingido = TRUE
                        WHERE crianca_id = %s AND nome = 'Primeiro Colorir'
                    """, (crianca_id,))
                elif titulo_atividade == "Quebra-Cabeça":
                    cur.execute("""
                        UPDATE conquistas
                        SET atingido = TRUE
                        WHERE crianca_id = %s AND nome = 'Primeiro Quebra-Cabeça'
                    """, (crianca_id,))
                elif titulo_atividade == "Jogo da Memória":
                    cur.execute("""
                        UPDATE conquistas
                        SET atingido = TRUE
                        WHERE crianca_id = %s AND nome = 'Missão Cumprida!'
                    """, (crianca_id,))

            conn.commit()
            return {"mensagem": "Sessão atualizada e conquistas desbloqueadas"}, 200

        except Exception as e:
            conn.rollback()
            return {"erro": "Erro ao atualizar sessão", "detalhes": str(e)}, 500
        finally:
            cur.close()
            conn.close()


class SalvarImagem(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json(force=True)
        sessao_id = data.get("sessao_id")
        imagem = data.get("imagem")  # Base64
        if not sessao_id or not imagem:
            return {"erro":"sessao_id e imagem são obrigatórios"},400

        token_login_id = int(get_jwt_identity())
        conn = get_conn()
        cur = conn.cursor()
        try:
            # Salvar imagem no servidor
            filename = f"{uuid.uuid4()}.png"
            filepath = f"static/imagens/{filename}"
            with open(filepath,"wb") as f:
                f.write(base64.b64decode(imagem.split(",")[1]))

            # Descobrir a criança
            cur.execute("SELECT crianca_id FROM crianca WHERE login_id=%s", (token_login_id,))
            crianca_id = cur.fetchone()[0]

            # Atualizar conquista "Primeiro Colorir" se ainda não atingida
            cur.execute("""
                UPDATE conquistas
                SET atingido = TRUE
                WHERE crianca_id = %s AND nome = 'Primeiro Colorir' AND atingido = FALSE
            """, (crianca_id,))

            conn.commit()
            return {"mensagem":"Imagem salva e conquista atualizada se aplicável","arquivo":filename},201
        except Exception as e:
            conn.rollback()
            return {"erro":"Erro ao salvar imagem/conquista","detalhes": str(e)},500
        finally:
            cur.close()
            conn.close()


class Conquistas(Resource):
    @jwt_required()
    def get(self):
        login_id = get_jwt_identity()
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT nome, imagem FROM conquistas 
                WHERE crianca_id = (SELECT crianca_id FROM crianca WHERE login_id=%s)
                AND atingido = TRUE
            """, (login_id,))
            conquistas = [{"nome": nome, "imagem": imagem} for nome, imagem in cur.fetchall()]
            return conquistas, 200
        finally:
            cur.close()


# -----------------------
# REGISTRAR ROTAS
# -----------------------
api.add_resource(Home, "/")
api.add_resource(Registrar, "/registrar")
api.add_resource(Login, "/login")
api.add_resource(Perfil, "/perfil")
api.add_resource(AtualizarPerfil, "/perfil/atualizar")

api.add_resource(CriarSessao,"/sessoes")
api.add_resource(AtualizarSessao,"/sessoes/atualizar")
api.add_resource(SalvarImagem,"/sessoes/salvar_imagem")
api.add_resource(Conquistas,"/conquistas")

# -----------------------
# RUN
# -----------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

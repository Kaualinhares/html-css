# ============================
# API MundoTEA — Arquivo Único
# Flask + PostgreSQL + JWT + CORS
# ============================

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token
import psycopg2
import bcrypt
from datetime import timedelta

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
# ROTAS
# ============================

# ===== LOGIN E CADASTRO =====

@app.route("/registrar", methods=["POST"])
def registrar():
    data = request.json
    email = data["email"]
    senha = data["senha"]
    nome = data["nome"]

    conn = get_conn()
    cur = conn.cursor()

    # Verifica se existe email
    cur.execute("SELECT email FROM login WHERE email=%s", (email,))
    if cur.fetchone():
        return jsonify({"erro": "Email já cadastrado"}), 400

    senha_hash = hash_senha(senha)

    # Cria login
    cur.execute("""
        INSERT INTO login (email, senha_hash)
        VALUES (%s, %s) RETURNING login_id
    """, (email, senha_hash))
    login_id = cur.fetchone()[0]

    # Cria terapeuta
    cur.execute("""
        INSERT INTO terapeuta (login_id, nome)
        VALUES (%s, %s)
    """, (login_id, nome))

    conn.commit()
    cur.close()
    conn.close()

    token = create_access_token(identity=login_id)

    return jsonify({"mensagem": "Cadastro OK", "token": token})


@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data["email"]
    senha = data["senha"]

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT login_id, senha_hash FROM login WHERE email=%s", (email,))
    user = cur.fetchone()

    if not user:
        return jsonify({"erro": "Usuário não existe"}), 404

    login_id, senha_hash = user

    if not verificar_senha(senha, senha_hash):
        return jsonify({"erro": "Senha incorreta"}), 401

    token = create_access_token(identity=login_id)

    return jsonify({"token": token})


# ===== TERAPEUTA =====

@app.route("/terapeuta/me", methods=["GET"])
@jwt_required()
def terapeuta_me():
    login_id = get_jwt_identity()

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT nome, telefone, especialidade FROM terapeuta WHERE login_id=%s", (login_id,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return jsonify({"erro": "Terapeuta não encontrado"}), 404

    return jsonify({
        "nome": row[0],
        "telefone": row[1],
        "especialidade": row[2]
    })


# ===== CRIAR CRIANÇA =====

@app.route("/crianca", methods=["POST"])
@jwt_required()
def criar_crianca():
    data = request.json
    login_id = get_jwt_identity()

    conn = get_conn()
    cur = conn.cursor()

    # Obtém terapeuta_id
    cur.execute("SELECT terapeuta_id FROM terapeuta WHERE login_id=%s", (login_id,))
    terapeuta_id = cur.fetchone()[0]

    cur.execute("""
        INSERT INTO crianca (
            terapeuta_id, nome, data_nascimento, nivel_autismo,
            necessidades, nome_pai, nome_mae,
            telefone_responsavel, email_responsavel
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING crianca_id
    """, (
        terapeuta_id,
        data["nome"],
        data.get("data_nascimento"),
        data.get("nivel_autismo"),
        data.get("necessidades"),
        data.get("nome_pai"),
        data.get("nome_mae"),
        data.get("telefone_responsavel"),
        data.get("email_responsavel")
    ))

    crianca_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"mensagem": "Criança cadastrada", "crianca_id": crianca_id})


# ===== CADASTRAR ATIVIDADE =====

@app.route("/atividades", methods=["POST"])
@jwt_required()
def criar_atividade():
    data = request.json
    login_id = get_jwt_identity()

    conn = get_conn()
    cur = conn.cursor()

    # Pega terapeuta criador
    cur.execute("SELECT terapeuta_id FROM terapeuta WHERE login_id=%s", (login_id,))
    terapeuta_id = cur.fetchone()[0]

    cur.execute("""
        INSERT INTO atividades (
            titulo, descricao, categoria, dificuldade, tempo_estimado_min,
            recursos, criado_por
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        RETURNING atividade_id
    """, (
        data["titulo"],
        data.get("descricao"),
        data.get("categoria"),
        data.get("dificuldade"),
        data.get("tempo_estimado_min"),
        data.get("recursos"),
        terapeuta_id
    ))

    atividade_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"atividade_id": atividade_id})


# ===== HOME =====

@app.route("/")
def home():
    return jsonify({"status": "API MundoTEA funcionando!"})


# ============================
# EXECUÇÃO
# ============================

if __name__ == "__main__":
    app.run(debug=True)

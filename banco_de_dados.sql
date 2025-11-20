CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-------------------------------------------------------
-- LOGIN
-- Apenas TERAPEUTAS fazem login
-------------------------------------------------------
CREATE TABLE login (
  login_id SERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  senha_hash VARCHAR(255) NOT NULL,
  criado_em TIMESTAMP WITH TIME ZONE DEFAULT now(),
  ativo BOOLEAN DEFAULT true
);

-------------------------------------------------------
-- TERAPEUTA
-- Agora possui nome direto + login
-------------------------------------------------------
CREATE TABLE terapeuta (
  terapeuta_id SERIAL PRIMARY KEY,
  login_id INT UNIQUE REFERENCES login(login_id) ON DELETE CASCADE,
  nome VARCHAR(200) NOT NULL,
  telefone VARCHAR(20),
  especialidade VARCHAR(120),
  criado_em TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-------------------------------------------------------
-- CRIANÇA
-- Contém nome + dados e terapeuta responsável
-------------------------------------------------------
CREATE TABLE crianca (
  crianca_id SERIAL PRIMARY KEY,
  terapeuta_id INT REFERENCES terapeuta(terapeuta_id) ON DELETE SET NULL,
  
  nome VARCHAR(200) NOT NULL,
  data_nascimento DATE,
  nivel_autismo SMALLINT,
  necessidades TEXT,

  -- Responsáveis
  nome_pai VARCHAR(200),
  nome_mae VARCHAR(200),
  telefone_responsavel VARCHAR(20),
  email_responsavel VARCHAR(255),

  criado_em TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-------------------------------------------------------
-- ATIVIDADES
-------------------------------------------------------
CREATE TABLE atividades (
  atividade_id SERIAL PRIMARY KEY,
  titulo VARCHAR(200) NOT NULL,
  descricao TEXT,
  categoria VARCHAR(100),
  dificuldade SMALLINT,
  tempo_estimado_min INT,
  recursos JSONB,
  criado_por INT REFERENCES terapeuta(terapeuta_id),
  ativo BOOLEAN DEFAULT true,
  criado_em TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-------------------------------------------------------
-- SESSÕES
-------------------------------------------------------
CREATE TABLE sessoes (
  sessao_id SERIAL PRIMARY KEY,
  crianca_id INT REFERENCES crianca(crianca_id) ON DELETE CASCADE,
  atividade_id INT REFERENCES atividades(atividade_id),
  iniciado_em TIMESTAMP WITH TIME ZONE DEFAULT now(),
  terminado_em TIMESTAMP WITH TIME ZONE,
  score NUMERIC,
  acuracia NUMERIC,
  tempo_gasto_segundos INT,
  tentativas INT DEFAULT 1,
  iniciado_por INT REFERENCES terapeuta(terapeuta_id)
);

-------------------------------------------------------
-- PREFERÊNCIAS DA CRIANÇA
-------------------------------------------------------
CREATE TABLE preferencias (
  preferencia_id SERIAL PRIMARY KEY,
  crianca_id INT REFERENCES crianca(crianca_id),
  chave VARCHAR(100) NOT NULL,
  valor TEXT,
  atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT now(),
  UNIQUE(crianca_id, chave)
);

-------------------------------------------------------
-- RECOMENDAÇÕES
-------------------------------------------------------
CREATE TABLE recomendacoes (
  recomendacao_id SERIAL PRIMARY KEY,
  crianca_id INT REFERENCES crianca(crianca_id),
  atividade_id INT REFERENCES atividades(atividade_id),
  score NUMERIC,
  versao_algoritmo VARCHAR(50),
  criado_em TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-------------------------------------------------------
-- ÍNDICES
-------------------------------------------------------
CREATE INDEX idx_login_email ON login(email);
CREATE INDEX idx_sessoes_crianca_data ON sessoes(crianca_id, iniciado_em);
CREATE INDEX idx_atividades_categoria ON atividades(categoria);
CREATE INDEX idx_recomendacoes_crianca ON recomendacoes(crianca_id, criado_em);

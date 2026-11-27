CREATE TABLE IF NOT EXISTS sessoes (
    session_id TEXT PRIMARY KEY,
    inicio_em TIMESTAMPTZ,
    fim_em TIMESTAMPTZ,
    origem TEXT NOT NULL DEFAULT 'aplicacao',
    metadados JSONB NOT NULL DEFAULT '{}'::jsonb,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS telemetria (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessoes(session_id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL,
    frame BIGINT,
    estado TEXT,
    escore_total DOUBLE PRECISION,
    escore_olhos DOUBLE PRECISION,
    escore_boca DOUBLE PRECISION,
    escore_cabeca DOUBLE PRECISION,
    perclos DOUBLE PRECISION,
    dados JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (session_id, timestamp, frame)
);
CREATE INDEX IF NOT EXISTS idx_telemetria_sessao_tempo ON telemetria(session_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_telemetria_estado_tempo ON telemetria(estado, timestamp DESC);

CREATE TABLE IF NOT EXISTS eventos (
    event_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessoes(session_id) ON DELETE CASCADE,
    origem TEXT,
    tipo TEXT,
    descricao TEXT,
    inicio_em TIMESTAMPTZ,
    fim_em TIMESTAMPTZ,
    duracao_segundos DOUBLE PRECISION,
    confirmado BOOLEAN,
    motivo TEXT,
    dados JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_eventos_sessao_inicio ON eventos(session_id, inicio_em DESC);

CREATE TABLE IF NOT EXISTS capturas (
    captura_id BIGSERIAL PRIMARY KEY,
    session_id TEXT REFERENCES sessoes(session_id) ON DELETE CASCADE,
    caminho_arquivo TEXT NOT NULL,
    url_relativa TEXT,
    timestamp TIMESTAMPTZ NOT NULL,
    tipo TEXT,
    motivo TEXT,
    sha256 TEXT,
    metadados JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_capturas_sessao_tempo ON capturas(session_id, timestamp DESC);

CREATE TABLE IF NOT EXISTS evento_captura (
    event_id TEXT NOT NULL REFERENCES eventos(event_id) ON DELETE CASCADE,
    captura_id BIGINT NOT NULL REFERENCES capturas(captura_id) ON DELETE CASCADE,
    PRIMARY KEY (event_id, captura_id)
);

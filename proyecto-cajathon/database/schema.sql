-- CAJA INTELIGENTE - esquema de producción para Supabase PostgreSQL.
-- La aplicación se conecta desde el servidor con DATABASE_URL; no expongas
-- credenciales de base de datos ni habilites políticas públicas de escritura.
-- SQLite se conserva únicamente para desarrollo local.

CREATE TABLE IF NOT EXISTS usuarios (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    nombre TEXT NOT NULL,
    rol TEXT NOT NULL,
    cargo TEXT DEFAULT 'Funcionario de Créditos',
    agencia TEXT DEFAULT 'Sede Central - CMAC',
    avatar_url TEXT,
    activo SMALLINT NOT NULL DEFAULT 1,
    ultimo_acceso TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS clientes (
    id TEXT PRIMARY KEY,
    codigo_cliente TEXT UNIQUE NOT NULL,
    nombres TEXT NOT NULL,
    apellidos TEXT NOT NULL,
    dni VARCHAR(8) UNIQUE NOT NULL,
    edad INTEGER NOT NULL,
    ocupacion TEXT NOT NULL,
    sector_economico TEXT DEFAULT 'Comercio',
    ingresos_mensuales DOUBLE PRECISION NOT NULL,
    gastos_mensuales DOUBLE PRECISION NOT NULL,
    deudas_actuales DOUBLE PRECISION NOT NULL DEFAULT 0,
    score_interno INTEGER NOT NULL DEFAULT 70,
    nivel_riesgo TEXT NOT NULL DEFAULT 'BAJO',
    telefono TEXT,
    email TEXT,
    direccion TEXT,
    departamento TEXT DEFAULT 'Lima',
    activo SMALLINT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS solicitudes_credito (
    id TEXT PRIMARY KEY,
    numero_solicitud TEXT UNIQUE NOT NULL,
    cliente_id TEXT NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    monto_solicitado DOUBLE PRECISION NOT NULL,
    plazo_meses INTEGER NOT NULL,
    tasa_interes_mensual DOUBLE PRECISION NOT NULL DEFAULT 0.028,
    cuota_mensual_estimada DOUBLE PRECISION NOT NULL,
    tipo_credito TEXT NOT NULL,
    historial_pagos TEXT NOT NULL,
    situacion_laboral TEXT NOT NULL,
    ingresos_declarados DOUBLE PRECISION NOT NULL,
    gastos_declarados DOUBLE PRECISION NOT NULL,
    deudas_declaradas DOUBLE PRECISION NOT NULL,
    capacidad_pago DOUBLE PRECISION NOT NULL,
    ratio_dti DOUBLE PRECISION NOT NULL,
    ingreso_disponible DOUBLE PRECISION NOT NULL,
    estado TEXT NOT NULL DEFAULT 'PENDIENTE',
    motivo_rechazo TEXT,
    fecha_solicitud TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evaluaciones_riesgo (
    id TEXT PRIMARY KEY,
    solicitud_id TEXT UNIQUE NOT NULL REFERENCES solicitudes_credito(id) ON DELETE CASCADE,
    cliente_id TEXT NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    score_riesgo INTEGER NOT NULL,
    nivel_riesgo TEXT NOT NULL,
    resumen_evaluacion TEXT NOT NULL,
    factores_positivos TEXT NOT NULL DEFAULT '[]',
    factores_negativos TEXT NOT NULL DEFAULT '[]',
    senales_alerta TEXT NOT NULL DEFAULT '[]',
    probabilidad_morosidad_30d DOUBLE PRECISION NOT NULL DEFAULT 0,
    probabilidad_morosidad_90d DOUBLE PRECISION NOT NULL DEFAULT 0,
    recomendaciones TEXT NOT NULL,
    modelo_ia_utilizado TEXT DEFAULT 'OpenAI GPT-4o-mini',
    es_modo_demo SMALLINT NOT NULL DEFAULT 0,
    dictamen_humano TEXT NOT NULL DEFAULT 'EN_REVISION',
    observaciones_analista TEXT,
    evaluado_por TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pagos (
    id TEXT PRIMARY KEY,
    solicitud_id TEXT NOT NULL REFERENCES solicitudes_credito(id) ON DELETE CASCADE,
    cliente_id TEXT NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    numero_cuota INTEGER NOT NULL,
    total_cuotas INTEGER NOT NULL,
    monto_cuota DOUBLE PRECISION NOT NULL,
    fecha_vencimiento DATE NOT NULL,
    fecha_pago TIMESTAMPTZ,
    dias_atraso INTEGER NOT NULL DEFAULT 0,
    estado_pago TEXT NOT NULL DEFAULT 'PENDIENTE',
    clasificacion_sbs TEXT NOT NULL DEFAULT 'Normal (0 días)',
    penalidad DOUBLE PRECISION NOT NULL DEFAULT 0,
    metodo_pago TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alertas (
    id TEXT PRIMARY KEY,
    cliente_id TEXT REFERENCES clientes(id) ON DELETE CASCADE,
    solicitud_id TEXT REFERENCES solicitudes_credito(id) ON DELETE CASCADE,
    tipo_alerta TEXT NOT NULL,
    severidad TEXT NOT NULL,
    mensaje TEXT NOT NULL,
    leido SMALLINT NOT NULL DEFAULT 0,
    accion_recomendada TEXT,
    fecha_alerta TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS historial_crediticio (
    id TEXT PRIMARY KEY,
    cliente_id TEXT NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    entidad_financiera TEXT NOT NULL,
    tipo_credito TEXT NOT NULL,
    monto_original DOUBLE PRECISION NOT NULL,
    saldo_deudor DOUBLE PRECISION NOT NULL,
    calificacion_sbs TEXT NOT NULL,
    dias_morosidad_maxima INTEGER NOT NULL DEFAULT 0,
    estado_credito TEXT NOT NULL DEFAULT 'VIGENTE',
    fecha_consulta DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_clientes_dni ON clientes(dni);
CREATE INDEX IF NOT EXISTS idx_clientes_codigo ON clientes(codigo_cliente);
CREATE INDEX IF NOT EXISTS idx_clientes_nivel_riesgo ON clientes(nivel_riesgo);
CREATE INDEX IF NOT EXISTS idx_solicitudes_cliente ON solicitudes_credito(cliente_id);
CREATE INDEX IF NOT EXISTS idx_solicitudes_estado ON solicitudes_credito(estado);
CREATE INDEX IF NOT EXISTS idx_solicitudes_numero ON solicitudes_credito(numero_solicitud);
CREATE INDEX IF NOT EXISTS idx_evaluaciones_solicitud ON evaluaciones_riesgo(solicitud_id);
CREATE INDEX IF NOT EXISTS idx_evaluaciones_nivel ON evaluaciones_riesgo(nivel_riesgo);
CREATE INDEX IF NOT EXISTS idx_pagos_solicitud ON pagos(solicitud_id);
CREATE INDEX IF NOT EXISTS idx_pagos_cliente ON pagos(cliente_id);
CREATE INDEX IF NOT EXISTS idx_pagos_estado ON pagos(estado_pago);
CREATE INDEX IF NOT EXISTS idx_pagos_vencimiento ON pagos(fecha_vencimiento);
CREATE INDEX IF NOT EXISTS idx_alertas_severidad ON alertas(severidad);
CREATE INDEX IF NOT EXISTS idx_alertas_leido ON alertas(leido);
CREATE INDEX IF NOT EXISTS idx_historial_cliente ON historial_crediticio(cliente_id);

-- Las consultas del navegador no acceden directamente a estas tablas: Flask
-- es el único backend y se autentica con DATABASE_URL, almacenada como secreto
-- de Render. RLS bloquea el acceso público por la API REST de Supabase.
ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE clientes ENABLE ROW LEVEL SECURITY;
ALTER TABLE solicitudes_credito ENABLE ROW LEVEL SECURITY;
ALTER TABLE evaluaciones_riesgo ENABLE ROW LEVEL SECURITY;
ALTER TABLE pagos ENABLE ROW LEVEL SECURITY;
ALTER TABLE alertas ENABLE ROW LEVEL SECURITY;
ALTER TABLE historial_crediticio ENABLE ROW LEVEL SECURITY;

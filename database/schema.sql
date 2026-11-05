-- ============================================================================
-- PROYECTO: CAJA INTELIGENTE - Sistema de Evaluación de Riesgo Crediticio con IA
-- Base de Datos PostgreSQL para Supabase
-- Diseñado para Cajas Municipales de Ahorro y Crédito (CMAC) del Perú
-- ============================================================================

-- Habilitar extensión para generación de UUIDs si no está habilitada
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ----------------------------------------------------------------------------
-- 1. TABLA: usuarios
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    rol VARCHAR(50) NOT NULL CHECK (rol IN ('Administrador', 'Analista de créditos', 'Personal de cobranza')),
    cargo VARCHAR(100) DEFAULT 'Funcionario de Créditos',
    agencia VARCHAR(100) DEFAULT 'Sede Central - CMAC',
    avatar_url TEXT,
    activo BOOLEAN DEFAULT TRUE,
    ultimo_acceso TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 2. TABLA: clientes
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clientes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    codigo_cliente VARCHAR(50) UNIQUE NOT NULL,
    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    dni VARCHAR(8) UNIQUE NOT NULL CHECK (dni ~ '^[0-9]{8}$'),
    edad INTEGER NOT NULL CHECK (edad >= 18 AND edad <= 95),
    ocupacion VARCHAR(150) NOT NULL,
    sector_economico VARCHAR(100) DEFAULT 'Comercio',
    ingresos_mensuales NUMERIC(12, 2) NOT NULL CHECK (ingresos_mensuales >= 0),
    gastos_mensuales NUMERIC(12, 2) NOT NULL CHECK (gastos_mensuales >= 0),
    deudas_actuales NUMERIC(12, 2) DEFAULT 0 CHECK (deudas_actuales >= 0),
    score_interno INTEGER DEFAULT 70 CHECK (score_interno BETWEEN 0 AND 100),
    nivel_riesgo VARCHAR(20) DEFAULT 'BAJO' CHECK (nivel_riesgo IN ('BAJO', 'MEDIO', 'ALTO')),
    telefono VARCHAR(20),
    email VARCHAR(150),
    direccion VARCHAR(255),
    departamento VARCHAR(100) DEFAULT 'Lima',
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 3. TABLA: solicitudes_credito
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS solicitudes_credito (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    numero_solicitud VARCHAR(50) UNIQUE NOT NULL,
    cliente_id UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    monto_solicitado NUMERIC(12, 2) NOT NULL CHECK (monto_solicitado > 0),
    plazo_meses INTEGER NOT NULL CHECK (plazo_meses >= 1 AND plazo_meses <= 120),
    tasa_interes_mensual NUMERIC(6, 4) DEFAULT 0.0280,
    cuota_mensual_estimada NUMERIC(12, 2) NOT NULL CHECK (cuota_mensual_estimada > 0),
    tipo_credito VARCHAR(50) NOT NULL CHECK (tipo_credito IN ('Microempresa / MYPE', 'Consumo Personal', 'Hipotecario', 'Capital de Trabajo', 'Mejora de Vivienda')),
    historial_pagos VARCHAR(50) NOT NULL CHECK (historial_pagos IN ('Puntual sin atrasos', 'Atrasos leves ocasionales (1-8 días)', 'Morosidad previa regularizada', 'Cliente nuevo sin historial')),
    situacion_laboral VARCHAR(50) NOT NULL CHECK (situacion_laboral IN ('Dependiente formal', 'Independiente formal', 'Microempresario / Negocio propio', 'Independiente informal')),
    ingresos_declarados NUMERIC(12, 2) NOT NULL,
    gastos_declarados NUMERIC(12, 2) NOT NULL,
    deudas_declaradas NUMERIC(12, 2) NOT NULL,
    capacidad_pago NUMERIC(12, 2) NOT NULL,
    ratio_dti NUMERIC(6, 2) NOT NULL,
    ingreso_disponible NUMERIC(12, 2) NOT NULL,
    estado VARCHAR(30) DEFAULT 'PENDIENTE' CHECK (estado IN ('PENDIENTE', 'EVALUADO', 'APROBADO', 'RECHAZADO', 'OBSERVADO')),
    motivo_rechazo TEXT,
    fecha_solicitud TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 4. TABLA: evaluaciones_riesgo
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS evaluaciones_riesgo (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    solicitud_id UUID UNIQUE NOT NULL REFERENCES solicitudes_credito(id) ON DELETE CASCADE,
    cliente_id UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    score_riesgo INTEGER NOT NULL CHECK (score_riesgo BETWEEN 0 AND 100),
    nivel_riesgo VARCHAR(20) NOT NULL CHECK (nivel_riesgo IN ('BAJO', 'MEDIO', 'ALTO')),
    resumen_evaluacion TEXT NOT NULL,
    factores_positivos JSONB DEFAULT '[]'::jsonb,
    factores_negativos JSONB DEFAULT '[]'::jsonb,
    senales_alerta JSONB DEFAULT '[]'::jsonb,
    probabilidad_morosidad_30d NUMERIC(5, 2) DEFAULT 0.00,
    probabilidad_morosidad_90d NUMERIC(5, 2) DEFAULT 0.00,
    recomendaciones TEXT NOT NULL,
    modelo_ia_utilizado VARCHAR(100) DEFAULT 'OpenAI GPT-4o-mini',
    es_modo_demo BOOLEAN DEFAULT FALSE,
    dictamen_humano VARCHAR(50) DEFAULT 'EN_REVISION' CHECK (dictamen_humano IN ('EN_REVISION', 'CONFORME', 'REQUIERE_GARANTIA', 'DENEGADO')),
    observaciones_analista TEXT,
    evaluado_por VARCHAR(150),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 5. TABLA: pagos
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pagos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    solicitud_id UUID NOT NULL REFERENCES solicitudes_credito(id) ON DELETE CASCADE,
    cliente_id UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    numero_cuota INTEGER NOT NULL,
    total_cuotas INTEGER NOT NULL,
    monto_cuota NUMERIC(12, 2) NOT NULL,
    fecha_vencimiento DATE NOT NULL,
    fecha_pago TIMESTAMP WITH TIME ZONE,
    dias_atraso INTEGER DEFAULT 0 CHECK (dias_atraso >= 0),
    estado_pago VARCHAR(30) DEFAULT 'PENDIENTE' CHECK (estado_pago IN ('PAGADO', 'PENDIENTE', 'VENCIDO', 'EN_MORA')),
    clasificacion_sbs VARCHAR(50) DEFAULT 'Normal (0 días)' CHECK (clasificacion_sbs IN ('Normal (0 días)', 'Con Problemas Potenciales CPP (9-30 días)', 'Deficiente (31-60 días)', 'Dudoso (61-120 días)', 'Pérdida (>120 días)')),
    penalidad NUMERIC(10, 2) DEFAULT 0.00,
    metodo_pago VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 6. TABLA: alertas
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alertas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cliente_id UUID REFERENCES clientes(id) ON DELETE CASCADE,
    solicitud_id UUID REFERENCES solicitudes_credito(id) ON DELETE CASCADE,
    tipo_alerta VARCHAR(100) NOT NULL,
    severidad VARCHAR(20) NOT NULL CHECK (severidad IN ('BAJA', 'MEDIA', 'ALTA', 'CRITICA')),
    mensaje TEXT NOT NULL,
    leido BOOLEAN DEFAULT FALSE,
    accion_recomendada TEXT,
    fecha_alerta TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 7. TABLA: historial_crediticio
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS historial_crediticio (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cliente_id UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    entidad_financiera VARCHAR(150) NOT NULL,
    tipo_credito VARCHAR(100) NOT NULL,
    monto_original NUMERIC(12, 2) NOT NULL,
    saldo_deudor NUMERIC(12, 2) NOT NULL,
    calificacion_sbs VARCHAR(50) NOT NULL CHECK (calificacion_sbs IN ('Normal (0)', 'CPP (1)', 'Deficiente (2)', 'Dudoso (3)', 'Pérdida (4)')),
    dias_morosidad_maxima INTEGER DEFAULT 0,
    estado_credito VARCHAR(50) DEFAULT 'VIGENTE' CHECK (estado_credito IN ('VIGENTE', 'CANCELADO', 'REFINANCIADO', 'JUDICIAL')),
    fecha_consulta DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- ÍNDICES PARA ALTO RENDIMIENTO
-- ----------------------------------------------------------------------------
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

-- ----------------------------------------------------------------------------
-- TRIGGERS PARA UPDATED_AT AUTOMÁTICO
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION actualizar_timestamp_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_usuarios_updated_at ON usuarios;
CREATE TRIGGER trg_usuarios_updated_at
BEFORE UPDATE ON usuarios
FOR EACH ROW EXECUTE FUNCTION actualizar_timestamp_updated_at();

DROP TRIGGER IF EXISTS trg_clientes_updated_at ON clientes;
CREATE TRIGGER trg_clientes_updated_at
BEFORE UPDATE ON clientes
FOR EACH ROW EXECUTE FUNCTION actualizar_timestamp_updated_at();

DROP TRIGGER IF EXISTS trg_solicitudes_updated_at ON solicitudes_credito;
CREATE TRIGGER trg_solicitudes_updated_at
BEFORE UPDATE ON solicitudes_credito
FOR EACH ROW EXECUTE FUNCTION actualizar_timestamp_updated_at();

DROP TRIGGER IF EXISTS trg_pagos_updated_at ON pagos;
CREATE TRIGGER trg_pagos_updated_at
BEFORE UPDATE ON pagos
FOR EACH ROW EXECUTE FUNCTION actualizar_timestamp_updated_at();

-- ----------------------------------------------------------------------------
-- POLÍTICAS DE SEGURIDAD RLS (Row Level Security) PARA SUPABASE
-- ----------------------------------------------------------------------------
ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE clientes ENABLE ROW LEVEL SECURITY;
ALTER TABLE solicitudes_credito ENABLE ROW LEVEL SECURITY;
ALTER TABLE evaluaciones_riesgo ENABLE ROW LEVEL SECURITY;
ALTER TABLE pagos ENABLE ROW LEVEL SECURITY;
ALTER TABLE alertas ENABLE ROW LEVEL SECURITY;
ALTER TABLE historial_crediticio ENABLE ROW LEVEL SECURITY;

-- Políticas de lectura para usuarios autenticados
CREATE POLICY "Lectura pública para usuarios autenticados en usuarios" 
ON usuarios FOR SELECT TO authenticated USING (true);

CREATE POLICY "Lectura completa en clientes" 
ON clientes FOR SELECT TO authenticated USING (true);

CREATE POLICY "Insertar clientes personal autorizado" 
ON clientes FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Actualizar clientes personal autorizado" 
ON clientes FOR UPDATE TO authenticated USING (true);

CREATE POLICY "Eliminar clientes administradores" 
ON clientes FOR DELETE TO authenticated USING (true);

CREATE POLICY "Lectura de solicitudes" 
ON solicitudes_credito FOR SELECT TO authenticated USING (true);

CREATE POLICY "Inserción de solicitudes" 
ON solicitudes_credito FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Actualización de solicitudes" 
ON solicitudes_credito FOR UPDATE TO authenticated USING (true);

CREATE POLICY "Lectura de evaluaciones" 
ON evaluaciones_riesgo FOR SELECT TO authenticated USING (true);

CREATE POLICY "Inserción de evaluaciones" 
ON evaluaciones_riesgo FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Lectura de pagos" 
ON pagos FOR SELECT TO authenticated USING (true);

CREATE POLICY "Modificación de pagos cobranzas" 
ON pagos FOR ALL TO authenticated USING (true);

CREATE POLICY "Lectura de alertas" 
ON alertas FOR SELECT TO authenticated USING (true);

CREATE POLICY "Gestión de alertas" 
ON alertas FOR ALL TO authenticated USING (true);

CREATE POLICY "Lectura historial crediticio" 
ON historial_crediticio FOR SELECT TO authenticated USING (true);

-- Permisos para rol de servicio anónimo (en demostración)
CREATE POLICY "Acceso demo anon clientes" ON clientes FOR ALL TO anon USING (true);
CREATE POLICY "Acceso demo anon solicitudes" ON solicitudes_credito FOR ALL TO anon USING (true);
CREATE POLICY "Acceso demo anon evaluaciones" ON evaluaciones_riesgo FOR ALL TO anon USING (true);
CREATE POLICY "Acceso demo anon pagos" ON pagos FOR ALL TO anon USING (true);
CREATE POLICY "Acceso demo anon alertas" ON alertas FOR ALL TO anon USING (true);
CREATE POLICY "Acceso demo anon historial" ON historial_crediticio FOR ALL TO anon USING (true);


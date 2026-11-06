import os
import sqlite3
import json
from config import Config
from database.seed_data import (
    get_demo_users,
    get_demo_clients,
    get_demo_solicitudes,
    get_demo_evaluaciones,
    get_demo_pagos,
    get_demo_alertas,
    get_demo_historial
)

def get_supabase():
    """Crea un cliente de autenticación aislado para evitar compartir sesiones."""
    if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL y SUPABASE_KEY son obligatorios para Supabase Auth.")

    from supabase import create_client
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

def get_connection():
    """Retorna una conexión a PostgreSQL de Supabase o a SQLite local."""
    if Config.DATABASE_URL:
        import psycopg2
        from psycopg2.extensions import parse_dsn
        from psycopg2.extras import RealDictCursor

        connection_options = parse_dsn(Config.DATABASE_URL)
        connection_options.setdefault("sslmode", "require")
        connection_options["connect_timeout"] = "10"
        return psycopg2.connect(cursor_factory=RealDictCursor, **connection_options)

    os.makedirs(os.path.dirname(Config.SQLITE_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(Config.SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def query_db(query, args=(), one=False):
    """Ejecuta una consulta SELECT y retorna una lista de diccionarios o un único diccionario."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        if Config.DATABASE_URL:
            query = query.replace("?", "%s")
            if args:
                cur.execute(query, args)
            else:
                cur.execute(query)
        else:
            cur.execute(query, args)
        rv = cur.fetchall()
        cur.close()
        res = [dict(ix) for ix in rv]
        return (res[0] if res else None) if one else res
    finally:
        conn.close()

def execute_db(query, args=()):
    """Ejecuta INSERT, UPDATE o DELETE y retorna el rowid y filas afectadas."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        if Config.DATABASE_URL:
            query = query.replace("?", "%s")
            if args:
                cur.execute(query, args)
            else:
                cur.execute(query)
        else:
            cur.execute(query, args)
        conn.commit()
        last_id = cur.lastrowid
        row_count = cur.rowcount
        cur.close()
        return last_id, row_count
    finally:
        conn.close()

def execute_transaction(statements):
    """Run a sequence of parameterized writes atomically."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        row_counts = []
        for query, args in statements:
            if Config.DATABASE_URL:
                query = query.replace("?", "%s")
            cur.execute(query, args)
            row_counts.append(cur.rowcount)
        conn.commit()
        cur.close()
        return row_counts
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def new_id(prefix):
    """Genera UUIDs compatibles con Supabase y prefijos legibles en SQLite demo."""
    import uuid

    return str(uuid.uuid4()) if Config.DATABASE_URL else f"{prefix}-{uuid.uuid4().hex[:8]}"

def init_db():
    """Inicializa las tablas de la base de datos y carga datos de demostración si está vacía."""
    if Config.DATABASE_URL:
        expected_tables = {
            "usuarios", "clientes", "solicitudes_credito", "evaluaciones_riesgo",
            "pagos", "alertas", "historial_crediticio", "historial_decisiones",
            "promesas_pago", "transacciones_pago", "telegram_notifications"
        }
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name = ANY(%s)
                """, (list(expected_tables),))
                existing_tables = {row["table_name"] for row in cur.fetchall()}
            missing_tables = expected_tables - existing_tables
            if missing_tables:
                raise RuntimeError(
                    "Faltan tablas en Supabase: " + ", ".join(sorted(missing_tables))
                    + ". Ejecuta database/schema.sql en el SQL Editor de Supabase."
                )
        finally:
            conn.close()
        return

    conn = get_connection()
    cur = conn.cursor()

    # Creación de tablas compatibles con SQLite
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nombre TEXT NOT NULL,
        rol TEXT NOT NULL,
        cargo TEXT DEFAULT 'Funcionario de Créditos',
        agencia TEXT DEFAULT 'Sede Central - CMAC',
        avatar_url TEXT,
        activo INTEGER DEFAULT 1,
        ultimo_acceso TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS clientes (
        id TEXT PRIMARY KEY,
        codigo_cliente TEXT UNIQUE NOT NULL,
        nombres TEXT NOT NULL,
        apellidos TEXT NOT NULL,
        dni TEXT UNIQUE NOT NULL,
        edad INTEGER NOT NULL,
        ocupacion TEXT NOT NULL,
        sector_economico TEXT DEFAULT 'Comercio',
        ingresos_mensuales REAL NOT NULL,
        gastos_mensuales REAL NOT NULL,
        deudas_actuales REAL DEFAULT 0,
        score_interno INTEGER DEFAULT 70,
        nivel_riesgo TEXT DEFAULT 'BAJO',
        telefono TEXT,
        email TEXT,
        direccion TEXT,
        departamento TEXT DEFAULT 'Lima',
        provincia TEXT,
        distrito TEXT,
        latitud REAL CHECK (latitud IS NULL OR (latitud BETWEEN -18.5 AND 0.0)),
        longitud REAL CHECK (longitud IS NULL OR (longitud BETWEEN -82.0 AND -68.0)),
        activo INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS solicitudes_credito (
        id TEXT PRIMARY KEY,
        numero_solicitud TEXT UNIQUE NOT NULL,
        cliente_id TEXT NOT NULL,
        monto_solicitado REAL NOT NULL,
        plazo_meses INTEGER NOT NULL,
        tasa_interes_mensual REAL DEFAULT 0.0280,
        cuota_mensual_estimada REAL NOT NULL,
        tipo_credito TEXT NOT NULL,
        historial_pagos TEXT NOT NULL,
        situacion_laboral TEXT NOT NULL,
        ingresos_declarados REAL NOT NULL,
        gastos_declarados REAL NOT NULL,
        deudas_declaradas REAL NOT NULL,
        capacidad_pago REAL NOT NULL,
        ratio_dti REAL NOT NULL,
        ingreso_disponible REAL NOT NULL,
        estado TEXT DEFAULT 'PENDIENTE',
        motivo_rechazo TEXT,
        monto_desembolsado REAL CHECK (monto_desembolsado IS NULL OR monto_desembolsado >= 0),
        fecha_desembolso TEXT,
        fecha_solicitud TEXT DEFAULT CURRENT_TIMESTAMP,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS evaluaciones_riesgo (
        id TEXT PRIMARY KEY,
        solicitud_id TEXT UNIQUE NOT NULL,
        cliente_id TEXT NOT NULL,
        score_riesgo INTEGER NOT NULL,
        nivel_riesgo TEXT NOT NULL,
        resumen_evaluacion TEXT NOT NULL,
        factores_positivos TEXT DEFAULT '[]',
        factores_negativos TEXT DEFAULT '[]',
        senales_alerta TEXT DEFAULT '[]',
        probabilidad_morosidad_30d REAL DEFAULT 0.0,
        probabilidad_morosidad_90d REAL DEFAULT 0.0,
        recomendaciones TEXT NOT NULL,
        modelo_ia_utilizado TEXT DEFAULT 'OpenAI GPT-4o-mini',
        es_modo_demo INTEGER DEFAULT 0,
        dictamen_humano TEXT DEFAULT 'EN_REVISION',
        observaciones_analista TEXT,
        evaluado_por TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (solicitud_id) REFERENCES solicitudes_credito(id) ON DELETE CASCADE,
        FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS pagos (
        id TEXT PRIMARY KEY,
        solicitud_id TEXT NOT NULL,
        cliente_id TEXT NOT NULL,
        numero_cuota INTEGER NOT NULL,
        total_cuotas INTEGER NOT NULL,
        monto_cuota REAL NOT NULL,
        fecha_vencimiento TEXT NOT NULL,
        fecha_pago TEXT,
        dias_atraso INTEGER DEFAULT 0,
        estado_pago TEXT DEFAULT 'PENDIENTE',
        clasificacion_sbs TEXT DEFAULT 'Normal (0 días)',
        penalidad REAL DEFAULT 0.0,
        metodo_pago TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (solicitud_id) REFERENCES solicitudes_credito(id) ON DELETE CASCADE,
        FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS alertas (
        id TEXT PRIMARY KEY,
        cliente_id TEXT,
        solicitud_id TEXT,
        tipo_alerta TEXT NOT NULL,
        severidad TEXT NOT NULL,
        mensaje TEXT NOT NULL,
        leido INTEGER DEFAULT 0,
        accion_recomendada TEXT,
        fecha_alerta TEXT DEFAULT CURRENT_TIMESTAMP,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE,
        FOREIGN KEY (solicitud_id) REFERENCES solicitudes_credito(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS historial_crediticio (
        id TEXT PRIMARY KEY,
        cliente_id TEXT NOT NULL,
        entidad_financiera TEXT NOT NULL,
        tipo_credito TEXT NOT NULL,
        monto_original REAL NOT NULL,
        saldo_deudor REAL NOT NULL,
        calificacion_sbs TEXT NOT NULL,
        dias_morosidad_maxima INTEGER DEFAULT 0,
        estado_credito TEXT DEFAULT 'VIGENTE',
        fecha_consulta TEXT DEFAULT CURRENT_DATE,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS historial_decisiones (
        id TEXT PRIMARY KEY,
        solicitud_id TEXT NOT NULL REFERENCES solicitudes_credito(id) ON DELETE RESTRICT,
        cliente_id TEXT NOT NULL REFERENCES clientes(id) ON DELETE RESTRICT,
        actor_id TEXT NOT NULL,
        actor_nombre TEXT NOT NULL,
        tipo_evento TEXT NOT NULL,
        estado_decision TEXT,
        nivel_riesgo TEXT,
        score_riesgo INTEGER,
        observaciones TEXT,
        snapshot_json TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS promesas_pago (
        id TEXT PRIMARY KEY,
        cliente_id TEXT NOT NULL,
        monto_comprometido REAL NOT NULL CHECK (monto_comprometido > 0),
        fecha_prometida TEXT NOT NULL,
        observaciones TEXT,
        responsable_id TEXT NOT NULL,
        responsable_nombre TEXT NOT NULL,
        registrado_por TEXT NOT NULL,
        estado TEXT NOT NULL DEFAULT 'PENDIENTE'
            CHECK (estado IN ('PENDIENTE', 'VENCIDA', 'CUMPLIDA', 'INCUMPLIDA')),
        alerta_proxima_enviada INTEGER NOT NULL DEFAULT 0,
        alerta_incumplimiento_enviada INTEGER NOT NULL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE RESTRICT
    );

    CREATE TABLE IF NOT EXISTS transacciones_pago (
        id TEXT PRIMARY KEY,
        cuota_id TEXT NOT NULL,
        solicitud_id TEXT NOT NULL REFERENCES solicitudes_credito(id) ON DELETE RESTRICT,
        cliente_id TEXT NOT NULL,
        promesa_id TEXT,
        monto REAL NOT NULL CHECK (monto > 0),
        metodo_pago TEXT NOT NULL,
        registrado_por TEXT NOT NULL,
        fecha_pago TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (cuota_id) REFERENCES pagos(id) ON DELETE RESTRICT,
        FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE RESTRICT,
        FOREIGN KEY (promesa_id) REFERENCES promesas_pago(id) ON DELETE RESTRICT
    );

    CREATE TABLE IF NOT EXISTS telegram_notifications (
        event_key TEXT PRIMARY KEY,
        sent_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Additive migrations for SQLite databases created by earlier app versions.
    client_columns = {row["name"] for row in cur.execute("PRAGMA table_info(clientes)").fetchall()}
    for column, definition in (
        ("provincia", "TEXT"),
        ("distrito", "TEXT"),
        ("latitud", "REAL"),
        ("longitud", "REAL"),
    ):
        if column not in client_columns:
            cur.execute(f"ALTER TABLE clientes ADD COLUMN {column} {definition}")

    application_columns = {row["name"] for row in cur.execute("PRAGMA table_info(solicitudes_credito)").fetchall()}
    for column, definition in (
        ("monto_desembolsado", "REAL"),
        ("fecha_desembolso", "TEXT"),
    ):
        if column not in application_columns:
            cur.execute(f"ALTER TABLE solicitudes_credito ADD COLUMN {column} {definition}")

    cur.execute("""
        CREATE TRIGGER IF NOT EXISTS historial_decisiones_no_update
        BEFORE UPDATE ON historial_decisiones
        BEGIN SELECT RAISE(ABORT, 'historial_decisiones is append-only'); END
    """)
    cur.execute("""
        CREATE TRIGGER IF NOT EXISTS historial_decisiones_no_delete
        BEFORE DELETE ON historial_decisiones
        BEGIN SELECT RAISE(ABORT, 'historial_decisiones is append-only'); END
    """)
    cur.execute("""
        CREATE TRIGGER IF NOT EXISTS solicitudes_con_historial_no_delete
        BEFORE DELETE ON solicitudes_credito
        WHEN EXISTS (SELECT 1 FROM historial_decisiones WHERE solicitud_id = OLD.id)
        BEGIN SELECT RAISE(ABORT, 'credit decision history prevents deletion'); END
    """)
    cur.execute("""
        CREATE TRIGGER IF NOT EXISTS clientes_con_historial_no_delete
        BEFORE DELETE ON clientes
        WHEN EXISTS (SELECT 1 FROM historial_decisiones WHERE cliente_id = OLD.id)
        BEGIN SELECT RAISE(ABORT, 'credit decision history prevents deletion'); END
    """)

    # Verificar si ya existen usuarios
    cur.execute("SELECT COUNT(*) as cnt FROM usuarios")
    users_count = cur.fetchone()["cnt"]

    if users_count == 0:
        print("[INFO] Sembrando datos de demostración en la base de datos...")
        # 1. Usuarios
        for u in get_demo_users():
            cur.execute("""
            INSERT INTO usuarios (id, email, password_hash, nombre, rol, cargo, agencia, avatar_url, activo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (u["id"], u["email"], u["password_hash"], u["nombre"], u["rol"], u["cargo"], u["agencia"], u["avatar_url"], u["activo"]))

        # 2. Clientes
        for c in get_demo_clients():
            cur.execute("""
            INSERT INTO clientes (id, codigo_cliente, nombres, apellidos, dni, edad, ocupacion, sector_economico, ingresos_mensuales, gastos_mensuales, deudas_actuales, score_interno, nivel_riesgo, telefono, email, direccion, departamento)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (c["id"], c["codigo_cliente"], c["nombres"], c["apellidos"], c["dni"], c["edad"], c["ocupacion"], c["sector_economico"], c["ingresos_mensuales"], c["gastos_mensuales"], c["deudas_actuales"], c["score_interno"], c["nivel_riesgo"], c["telefono"], c["email"], c["direccion"], c["departamento"]))

        # 3. Solicitudes
        for s in get_demo_solicitudes():
            cur.execute("""
            INSERT INTO solicitudes_credito (id, numero_solicitud, cliente_id, monto_solicitado, plazo_meses, tasa_interes_mensual, cuota_mensual_estimada, tipo_credito, historial_pagos, situacion_laboral, ingresos_declarados, gastos_declarados, deudas_declaradas, capacidad_pago, ratio_dti, ingreso_disponible, estado, fecha_solicitud)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (s["id"], s["numero_solicitud"], s["cliente_id"], s["monto_solicitado"], s["plazo_meses"], s["tasa_interes_mensual"], s["cuota_mensual_estimada"], s["tipo_credito"], s["historial_pagos"], s["situacion_laboral"], s["ingresos_declarados"], s["gastos_declarados"], s["deudas_declaradas"], s["capacidad_pago"], s["ratio_dti"], s["ingreso_disponible"], s["estado"], s["fecha_solicitud"]))

        # 4. Evaluaciones
        for ev in get_demo_evaluaciones():
            cur.execute("""
            INSERT INTO evaluaciones_riesgo (id, solicitud_id, cliente_id, score_riesgo, nivel_riesgo, resumen_evaluacion, factores_positivos, factores_negativos, senales_alerta, probabilidad_morosidad_30d, probabilidad_morosidad_90d, recomendaciones, modelo_ia_utilizado, es_modo_demo, dictamen_humano, observaciones_analista, evaluado_por)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ev["id"], ev["solicitud_id"], ev["cliente_id"], ev["score_riesgo"], ev["nivel_riesgo"], ev["resumen_evaluacion"], ev["factores_positivos"], ev["factores_negativos"], ev["senales_alerta"], ev["probabilidad_morosidad_30d"], ev["probabilidad_morosidad_90d"], ev["recomendaciones"], ev["modelo_ia_utilizado"], ev["es_modo_demo"], ev["dictamen_humano"], ev["observaciones_analista"], ev["evaluado_por"]))

        # 5. Pagos
        for p in get_demo_pagos():
            cur.execute("""
            INSERT INTO pagos (id, solicitud_id, cliente_id, numero_cuota, total_cuotas, monto_cuota, fecha_vencimiento, fecha_pago, dias_atraso, estado_pago, clasificacion_sbs, penalidad, metodo_pago)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (p["id"], p["solicitud_id"], p["cliente_id"], p["numero_cuota"], p["total_cuotas"], p["monto_cuota"], p["fecha_vencimiento"], p["fecha_pago"], p["dias_atraso"], p["estado_pago"], p["clasificacion_sbs"], p["penalidad"], p["metodo_pago"]))

        # 6. Alertas
        for a in get_demo_alertas():
            cur.execute("""
            INSERT INTO alertas (id, cliente_id, solicitud_id, tipo_alerta, severidad, mensaje, leido, accion_recomendada, fecha_alerta)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (a["id"], a["cliente_id"], a["solicitud_id"], a["tipo_alerta"], a["severidad"], a["mensaje"], a["leido"], a["accion_recomendada"], a["fecha_alerta"]))

        # 7. Historial Crediticio
        for h in get_demo_historial():
            cur.execute("""
            INSERT INTO historial_crediticio (id, cliente_id, entidad_financiera, tipo_credito, monto_original, saldo_deudor, calificacion_sbs, dias_morosidad_maxima, estado_credito)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (h["id"], h["cliente_id"], h["entidad_financiera"], h["tipo_credito"], h["monto_original"], h["saldo_deudor"], h["calificacion_sbs"], h["dias_morosidad_maxima"], h["estado_credito"]))

        conn.commit()
        print("[INFO] Datos de demostración sembrados con éxito (17 clientes, 20 solicitudes, pagos, alertas, historial).")

    cur.execute("""
        UPDATE usuarios
        SET activo = 0
        WHERE id IN ('u-004', 'u-005', 'u-006')
          AND email IN (
              'admin@cajainteligente.pe',
              'analista@cajainteligente.pe',
              'cobranzas@cajainteligente.pe'
          )
    """)
    conn.commit()
    conn.close()

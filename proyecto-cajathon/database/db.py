import os
import sqlite3
from flask import g, has_app_context
from werkzeug.security import generate_password_hash
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

def _uses_postgres():
    return bool(Config.DATABASE_URL)


def _prepare_query(query):
    """Translate SQLite parameter markers to psycopg2 markers for Supabase PostgreSQL."""
    return query.replace("?", "%s") if _uses_postgres() else query

def get_connection():
    """Reuse one request connection; select Supabase PostgreSQL or local SQLite."""
    if has_app_context():
        existing_connection = g.get("_database_connection")
        if existing_connection is not None:
            return existing_connection

    if _uses_postgres():
        import psycopg2
        from psycopg2.extras import RealDictCursor

        conn = psycopg2.connect(
            Config.DATABASE_URL,
            cursor_factory=RealDictCursor,
            connect_timeout=10,
            sslmode="require",
        )
    else:
        database_dir = os.path.dirname(os.path.abspath(Config.SQLITE_DB_PATH))
        os.makedirs(database_dir, exist_ok=True)
        conn = sqlite3.connect(Config.SQLITE_DB_PATH, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 30000")

    if has_app_context():
        g._database_connection = conn
    return conn


def close_connection(conn):
    """Close connections outside requests; Flask request connections close at teardown."""
    if not has_app_context() or g.get("_database_connection") is not conn:
        conn.close()


def close_app_connection(_error=None):
    """Release the request-scoped database connection."""
    conn = g.pop("_database_connection", None)
    if conn is not None:
        close_connection(conn)


def query_db(query, args=(), one=False):
    """Ejecuta una consulta SELECT y retorna una lista de diccionarios o un único diccionario."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        if args:
            cur.execute(_prepare_query(query), args)
        else:
            cur.execute(query)
        rv = cur.fetchall()
        cur.close()
        res = [dict(ix) for ix in rv]
        return (res[0] if res else None) if one else res
    finally:
        close_connection(conn)

def execute_db(query, args=()):
    """Execute a write query and return the inserted id (SQLite) and affected row count."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        if args:
            cur.execute(_prepare_query(query), args)
        else:
            cur.execute(query)
        conn.commit()
        last_id = getattr(cur, "lastrowid", None)
        row_count = cur.rowcount
        cur.close()
        return last_id, row_count
    finally:
        close_connection(conn)

def init_db():
    """Inicializa las tablas de la base de datos y carga datos de demostración si está vacía."""
    if _uses_postgres():
        init_supabase_db()
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
    """)

    # Verificar si ya existen usuarios
    cur.execute("SELECT COUNT(*) as cnt FROM usuarios")
    users_count = cur.fetchone()["cnt"]

    if users_count == 0:
        print("[INFO] Sembrando datos de demostración en la base de datos...")
        # 1. Usuarios
        demo_users = get_demo_users() if Config.DEMO_LOGIN_ENABLED else []
        for u in demo_users:
            cur.execute("""
            INSERT INTO usuarios (id, email, password_hash, nombre, rol, cargo, agencia, avatar_url, activo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (u["id"], u["email"], u["password_hash"], u["nombre"], u["rol"], u["cargo"], u["agencia"], u["avatar_url"], u["activo"]))

        if Config.IS_PRODUCTION:
            from werkzeug.security import generate_password_hash

            cur.execute("""
            INSERT INTO usuarios (id, email, password_hash, nombre, rol, cargo, agencia, activo)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                "u-initial-admin",
                Config.INITIAL_ADMIN_EMAIL,
                generate_password_hash(Config.INITIAL_ADMIN_PASSWORD),
                "Administrador inicial",
                "Administrador",
                "Administrador del sistema",
                "Sede Central - CMAC",
            ))

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

    conn.close()


def init_supabase_db():
    """Apply the Supabase PostgreSQL schema and create the first production administrator."""
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, encoding="utf-8") as schema_file:
        schema_sql = schema_file.read()

    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                # Serialize worker startup so schema setup/admin creation runs once at a time.
                cur.execute("SELECT pg_advisory_xact_lock(734621908)")
                cur.execute(schema_sql)
                cur.execute("SELECT COUNT(*) AS cnt FROM usuarios")
                if cur.fetchone()["cnt"] == 0:
                    cur.execute("""
                        INSERT INTO usuarios (
                            id, email, password_hash, nombre, rol, cargo, agencia, activo
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, 1)
                        ON CONFLICT (email) DO NOTHING
                    """, (
                        "u-initial-admin",
                        Config.INITIAL_ADMIN_EMAIL,
                        generate_password_hash(Config.INITIAL_ADMIN_PASSWORD),
                        "Administrador inicial",
                        "Administrador",
                        "Administrador del sistema",
                        "Sede Central - CMAC",
                    ))
    finally:
        close_connection(conn)

    print("[INFO] Conectado a Supabase PostgreSQL; esquema verificado.")

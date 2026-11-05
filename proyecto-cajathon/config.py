import os
import secrets
from datetime import timedelta
from dotenv import load_dotenv

# Cargar variables de entorno desde .env si existe
load_dotenv()


def _env_bool(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("true", "1", "yes", "on")


class Config:
    ENV = os.getenv("FLASK_ENV", "development").lower()
    IS_PRODUCTION = ENV == "production"
    SECRET_KEY = os.getenv("SECRET_KEY") or (
        None if IS_PRODUCTION else secrets.token_hex(32)
    )
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY es obligatorio en producción.")
    DEBUG = _env_bool("FLASK_DEBUG", not IS_PRODUCTION)
    if IS_PRODUCTION and DEBUG:
        raise RuntimeError("FLASK_DEBUG no puede estar activado en producción.")

    # Supabase PostgreSQL connection URI; required in production.
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    if IS_PRODUCTION and not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL es obligatorio en producción. Configura la URI de "
            "conexión PostgreSQL de Supabase."
        )

    # SQLite is a local development fallback only; production uses Supabase PostgreSQL.
    SQLITE_DB_PATH = os.getenv(
        "SQLITE_DB_PATH",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "database", "caja_inteligente.db"),
    )
    INITIAL_ADMIN_EMAIL = os.getenv("INITIAL_ADMIN_EMAIL", "").strip().lower()
    INITIAL_ADMIN_PASSWORD = os.getenv("INITIAL_ADMIN_PASSWORD", "")
    if (IS_PRODUCTION or DATABASE_URL) and not (INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD):
        raise RuntimeError(
            "Configura INITIAL_ADMIN_EMAIL e INITIAL_ADMIN_PASSWORD para crear "
            "el administrador inicial de PostgreSQL."
        )
    if (IS_PRODUCTION or DATABASE_URL) and len(INITIAL_ADMIN_PASSWORD) < 12:
        raise RuntimeError("INITIAL_ADMIN_PASSWORD debe tener al menos 12 caracteres.")

    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Modo Demostración IA (se activa automáticamente si no hay API key o si se fuerza)
    DEMO_MODE = _env_bool("DEMO_MODE", not IS_PRODUCTION)
    DEMO_LOGIN_ENABLED = DEMO_MODE and not IS_PRODUCTION and not DATABASE_URL
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = IS_PRODUCTION
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # Parámetros Financieros CMAC / SBS Perú
    TASA_INTERES_MENSUAL_REF = float(os.getenv("TASA_INTERES_MENSUAL_REF", "0.028")) # 2.8% mensual (TEA ~39%)
    DTI_UMBRAL_BAJO = float(os.getenv("DTI_UMBRAL_BAJO", "35.0")) # < 35% Bajo Riesgo
    DTI_UMBRAL_MEDIO = float(os.getenv("DTI_UMBRAL_MEDIO", "50.0")) # 35% - 50% Riesgo Medio

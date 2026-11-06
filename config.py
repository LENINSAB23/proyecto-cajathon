import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env si existe
load_dotenv()

class Config:
    ENV = os.getenv("FLASK_ENV", "development")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-caja-inteligente-key")
    DEBUG = os.getenv("FLASK_DEBUG", "True" if ENV != "production" else "False").lower() in ("true", "1", "yes")

    # Supabase Configuration
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
    DATABASE_URL = os.getenv("DATABASE_URL", "")

    # SQLite Local Database (para desarrollo local sin necesidad de configurar Supabase de inmediato)
    SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database", "caja_inteligente.db")

    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Modo Demostración IA (se activa automáticamente si no hay API key o si se fuerza)
    DEMO_MODE = os.getenv("DEMO_MODE", "True" if ENV != "production" else "False").lower() in ("true", "1", "yes")
    USE_SUPABASE_AUTH = bool(SUPABASE_URL and SUPABASE_KEY and not DEMO_MODE)
    DEMO_LOGIN_ENABLED = os.getenv(
        "DEMO_LOGIN_ENABLED",
        "True" if ENV != "production" and DEMO_MODE else "False"
    ).lower() in ("true", "1", "yes")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = ENV == "production"

    # Parámetros Financieros CMAC / SBS Perú
    TASA_INTERES_MENSUAL_REF = float(os.getenv("TASA_INTERES_MENSUAL_REF", "0.028")) # 2.8% mensual (TEA ~39%)
    DTI_UMBRAL_BAJO = float(os.getenv("DTI_UMBRAL_BAJO", "35.0")) # < 35% Bajo Riesgo
    DTI_UMBRAL_MEDIO = float(os.getenv("DTI_UMBRAL_MEDIO", "50.0")) # 35% - 50% Riesgo Medio

    @classmethod
    def validate(cls):
        if cls.ENV == "production":
            if not os.getenv("SECRET_KEY"):
                raise RuntimeError("SECRET_KEY es obligatorio en producción.")
            if cls.DEBUG:
                raise RuntimeError("FLASK_DEBUG debe estar desactivado en producción.")
            if cls.DEMO_MODE:
                raise RuntimeError("DEMO_MODE debe estar desactivado en producción.")
            if cls.DEMO_LOGIN_ENABLED:
                raise RuntimeError("DEMO_LOGIN_ENABLED debe estar desactivado en producción.")
            missing = [
                name for name, value in (
                    ("DATABASE_URL", cls.DATABASE_URL),
                    ("SUPABASE_URL", cls.SUPABASE_URL),
                    ("SUPABASE_KEY", cls.SUPABASE_KEY),
                ) if not value
            ]
            if missing:
                raise RuntimeError(
                    "Faltan variables obligatorias para producción: " + ", ".join(missing)
                )
        if cls.USE_SUPABASE_AUTH and not cls.DATABASE_URL:
            raise RuntimeError("DATABASE_URL es obligatorio cuando se usa Supabase Auth.")

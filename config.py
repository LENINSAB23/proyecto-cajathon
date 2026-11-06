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

    # Google Gemini & Bank-ito AI Configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")

    # Telegram Bot Configuration (Alertas Automáticas de Riesgo)
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

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
    HEALTH_MORA_WARNING = float(os.getenv("HEALTH_MORA_WARNING", "5.0"))
    HEALTH_MORA_CRITICAL = float(os.getenv("HEALTH_MORA_CRITICAL", "10.0"))
    GEO_MORA_MEDIUM = float(os.getenv("GEO_MORA_MEDIUM", "8.0"))
    GEO_MORA_HIGH = float(os.getenv("GEO_MORA_HIGH", "20.0"))

    @classmethod
    def validate(cls):
        if not (0 <= cls.HEALTH_MORA_WARNING < cls.HEALTH_MORA_CRITICAL <= 100):
            raise RuntimeError(
                "Los umbrales de morosidad deben cumplir 0 <= advertencia < crítico <= 100."
            )
        if not (0 <= cls.GEO_MORA_MEDIUM < cls.GEO_MORA_HIGH <= 100):
            raise RuntimeError(
                "Los umbrales de morosidad geográfica deben cumplir 0 <= medio < alto <= 100."
            )
        if cls.ENV == "production":
            if not os.getenv("SECRET_KEY"):
                raise RuntimeError("SECRET_KEY es obligatorio en producción.")
            if cls.DEBUG:
                raise RuntimeError("FLASK_DEBUG debe estar desactivado en producción.")
            if cls.DEMO_MODE:
                raise RuntimeError("DEMO_MODE debe estar desactivado en producción.")
            if cls.DEMO_LOGIN_ENABLED:
                raise RuntimeError("DEMO_LOGIN_ENABLED debe estar desactivado en producción.")
            if not cls.DATABASE_URL:
                raise RuntimeError("DATABASE_URL es obligatorio en producción.")
            if not cls.SUPABASE_URL or not cls.SUPABASE_KEY:
                raise RuntimeError(
                    "SUPABASE_URL y SUPABASE_KEY son obligatorios en producción "
                    "para autenticar cuentas con Supabase Auth."
                )
            if not cls.USE_SUPABASE_AUTH:
                raise RuntimeError("Supabase Auth debe estar habilitado en producción.")
        if cls.USE_SUPABASE_AUTH and not cls.DATABASE_URL:
            raise RuntimeError("DATABASE_URL es obligatorio cuando se usa Supabase Auth.")

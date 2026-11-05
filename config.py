import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env si existe
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "caja-inteligente-super-secret-key-senati-2026")
    ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")

    # Supabase Configuration
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    DATABASE_URL = os.getenv("DATABASE_URL", "")

    # SQLite Local Database (para desarrollo local sin necesidad de configurar Supabase de inmediato)
    SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database", "caja_inteligente.db")

    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Modo Demostración IA (se activa automáticamente si no hay API key o si se fuerza)
    DEMO_MODE = os.getenv("DEMO_MODE", "True").lower() in ("true", "1", "yes")

    # Parámetros Financieros CMAC / SBS Perú
    TASA_INTERES_MENSUAL_REF = float(os.getenv("TASA_INTERES_MENSUAL_REF", "0.028")) # 2.8% mensual (TEA ~39%)
    DTI_UMBRAL_BAJO = float(os.getenv("DTI_UMBRAL_BAJO", "35.0")) # < 35% Bajo Riesgo
    DTI_UMBRAL_MEDIO = float(os.getenv("DTI_UMBRAL_MEDIO", "50.0")) # 35% - 50% Riesgo Medio

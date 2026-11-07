# CREDIT RISK &bull; Sistema de Riesgo Crediticio con Bank-ito IA

Plataforma Fintech SaaS empresarial diseñada para la prevención, identificación y evaluación de riesgos crediticios en Cajas Municipales de Ahorro y Crédito (CMAC) del Perú. Integra a **Bank-ito**, copiloto y asesor de Inteligencia Artificial potenciado por la API de **Google Gemini**, garantizando evaluaciones explicables bajo la normativa regulatoria SBS (Res. N° 11356-2008).

## Características Principales

- **Dashboard Financiero Integral:** Monitoreo en tiempo real de colocaciones, solicitudes, cuotas en mora, distribución de riesgo y alertas preventivas.
- **Bank-ito Copilot IA (Google Gemini):** Asistente financiero inteligente integrado en el drawer lateral y en la evaluación técnica de solicitudes (Score 0-100, fortalezas, factores de riesgo, alertas rojas y probabilidades de morosidad a 30 y 90 días).
- **Simulador de Crédito en Tiempo Real:** Cálculo dinámico con sistema francés de amortización, evaluación de capacidad de pago mensual y ratio de endeudamiento DTI (*Debt-to-Income*).
- **Gestión 360° de Clientes & Centrales de Riesgo:** Historial crediticio unificado, expediente financiero y clasificación regulatoria SBS.
- **Registro de cuentas con aprobación:** Creación de credenciales mediante Supabase Auth; cada perfil nuevo queda inactivo y sin acceso hasta que un administrador lo aprueba.
- **Validación de datos de clientes:** Verificación de edad (18 a 95 años), ocupación e importes financieros finitos y dentro de rangos válidos al registrar o editar clientes.
- **Centro de Cobranzas y Morosidad:** Detección de mora temprana (1-8 días), seguimiento de cartera pesada (>30 días) y contacto prioritario de deudores.
- **Reportes Financieros Auditables:** Exportación oficial en formato PDF con membrete institucional y hojas de cálculo Excel bancario (.xlsx).
- **Diseño Fintech SaaS Profesional:** Estética de software financiero corporativo (azul marino `#0A192F`, azul petróleo `#0284C7`, grises neutros y semáforos de riesgo SBS sin adornos superfluos).

## Tecnologías

Python 3.10+, Flask, PostgreSQL/Supabase, Supabase Auth, SQLite para demostración local, OpenAI API opcional, Chart.js, ReportLab, OpenPyXL, Gunicorn y Render.

## Ejecución local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

En local, la configuración predeterminada usa SQLite y datos ficticios. La base local se crea y se siembra automáticamente al iniciar la aplicación. Abre <http://127.0.0.1:5000>.

### Cuentas locales de demostración

Estas cuentas solo están habilitadas para la demostración local (`DEMO_MODE=True`). El rol y los permisos se asignan desde la cuenta autenticada, no desde el formulario.

| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | `admin@creditrisk.pe` | `admin123` |
| Analista de créditos | `analista@creditrisk.pe` | `analista123` |
| Personal de cobranza | `cobranzas@creditrisk.pe` | `cobranza123` |

Usa únicamente los datos ficticios incluidos para pruebas y demostración. No pongas datos financieros reales en este entorno.

## Supabase Auth y PostgreSQL

La aplicación no cambia a SQLite silenciosamente cuando se configura PostgreSQL. En producción, verifica que las credenciales funcionen y que el esquema esté aplicado.

1. Crea un proyecto en Supabase.
2. En **SQL Editor**, ejecuta `database/schema.sql`. El esquema crea las siete tablas, índices, claves foráneas, timestamps y políticas RLS; la tabla `usuarios` enlaza cada perfil con el UUID de `auth.users`.
3. En **Authentication > Users**, puedes crear las cuentas manualmente. También se pueden solicitar desde **Crear cuenta** en el login publicado: Supabase Auth crea las credenciales y la aplicación guarda un perfil inactivo con rol de analista. La persona debe confirmar su correo si Supabase tiene habilitada esa opción, y un administrador debe aprobar el perfil antes de permitirle entrar.

Para aprobar una solicitud, localiza el UUID de la cuenta en Supabase Auth, verifica la identidad y ejecuta una actualización como esta en **SQL Editor**. Asigna únicamente el rol autorizado:

```sql
UPDATE public.usuarios
SET activo = TRUE,
    rol = 'Analista de créditos',
    cargo = 'Analista de Créditos',
    agencia = 'Sede Central',
    updated_at = CURRENT_TIMESTAMP
WHERE id = 'UUID_DE_AUTH'
  AND email = 'correo-institucional'
  AND activo = FALSE;
```

Para crear manualmente el perfil de una cuenta en Supabase Auth, copia su UUID y ejecuta:

   ```sql
   INSERT INTO public.usuarios (id, email, password_hash, nombre, rol, cargo, agencia, activo)
   VALUES (
       'UUID_DE_AUTH',
       'correo-institucional',
       NULL,
       'Nombre del funcionario',
       'Analista de créditos',
       'Analista de Créditos',
       'Sede Central',
       TRUE
   );
   ```

   Sustituye el UUID, correo, nombre y rol por los valores de la cuenta que creaste en Supabase Auth. Los roles válidos son `Administrador`, `Analista de créditos` y `Personal de cobranza`. La aplicación valida que el UUID y correo autenticados coincidan con el perfil activo.
4. Copia `.env.example` a `.env` y configura:
   - `DEMO_MODE=False`
   - `DEMO_LOGIN_ENABLED=False`
   - `SUPABASE_URL` y `SUPABASE_KEY` (clave pública/anon o publishable; nunca uses la `service_role` en el navegador).
   - `DATABASE_URL` con la URI PostgreSQL de Supabase y SSL habilitado. En Render, usa el pooler recomendado por Supabase si la conexión directa no está disponible.
   - `SECRET_KEY` con un valor aleatorio privado.
   - `OPENAI_API_KEY` es opcional; sin ella se usa el motor heurístico.
5. Inicia la aplicación. Al arrancar, verifica la conexión y que existan todas las tablas requeridas; si falta el esquema, muestra un error de configuración explícito.

El backend accede a PostgreSQL mediante una URI privada del servidor. Mantén `DATABASE_URL` y las claves fuera del repositorio. Los permisos de la aplicación también se comprueban en Flask; RLS no sustituye esas validaciones.

### Si el inicio de sesión falla en producción

- Usa el correo y la contraseña de una cuenta creada en **Supabase Authentication > Users**. Las cuentas `admin@creditrisk.pe`, `analista@creditrisk.pe` y `cobranzas@creditrisk.pe` son exclusivamente para SQLite local y no se crean en la base de producción.
- Confirma que el correo de Supabase esté verificado y que el perfil en `public.usuarios` tenga el mismo UUID y correo, además de `activo = TRUE`.
- Las solicitudes del formulario se guardan inicialmente con `activo = FALSE`; un administrador debe aprobarlas antes de iniciar sesión. Mientras tanto, el login indica que el acceso está pendiente.
- Si Supabase acepta las credenciales pero falta el perfil, el login indicará que el administrador debe vincular la cuenta. Usa la consulta SQL del paso 3 para hacerlo.
- En Render, verifica `SUPABASE_URL`, `SUPABASE_KEY`, `DATABASE_URL`, `DEMO_MODE=False` y `DEMO_LOGIN_ENABLED=False`. La aplicación ahora falla al arrancar si falta la configuración de Supabase Auth en producción, en vez de aceptar credenciales que no puede validar.

## Despliegue en Render

1. Crea un repositorio en GitHub. Desde la carpeta del proyecto, publica el código (sin incluir `.env`, contraseñas reales ni archivos de base local):

   ```powershell
   git init
   git add .
   git commit -m "Preparar Credit Risk"
   git branch -M main
   git remote add origin https://github.com/USUARIO/REPOSITORIO.git
   git push -u origin main
   ```

   Sustituye `USUARIO/REPOSITORIO` por la dirección de tu repositorio. El `.gitignore` excluye `.env` y la base SQLite local.
2. En Render, crea un **Blueprint** desde el repositorio para usar `render.yaml`, o crea un Web Service con:
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn app:app --bind 0.0.0.0:$PORT`
3. En las variables del servicio, configura `SUPABASE_URL`, `SUPABASE_KEY` y `DATABASE_URL`. Render genera `SECRET_KEY`; comprueba que `FLASK_ENV=production`, `DEMO_MODE=False` y `DEMO_LOGIN_ENABLED=False`.
4. Ejecuta `database/schema.sql` en Supabase antes de iniciar el servicio. Crea en Supabase Auth las cuentas de los funcionarios e inserta sus perfiles con el rol correcto.
5. Añade `OPENAI_API_KEY` solo si deseas activar análisis con OpenAI; sin ella queda disponible el motor heurístico de respaldo.
6. Despliega y comprueba `/health`, el login de cada rol y sus rutas permitidas.

## Pruebas

```powershell
python test_app.py
python -m compileall -q app.py routes database test_app.py
```

La suite usa la base de datos local ficticia e integra autenticación por rol, módulos, IA de respaldo y exportaciones. Las pruebas no requieren claves de Supabase ni OpenAI.
También comprueba que el registro rechace edades fuera del rango permitido e importes financieros no válidos, como `NaN`.

## Estructura principal

```text
app.py                  Aplicación Flask y configuración de contexto
config.py               Variables de entorno y validación de producción
database/db.py          Acceso a SQLite local o PostgreSQL de Supabase
database/schema.sql     Esquema PostgreSQL, índices y RLS
database/seed_data.py   Datos ficticios para SQLite local
routes/                 Autenticación y módulos de la plataforma
services/               Scoring, análisis IA y reportes
templates/              Vistas HTML/Jinja
static/                 CSS, JavaScript e imágenes
render.yaml             Configuración de despliegue
```

La carpeta raíz es la única copia del proyecto. Los módulos que solo existían en una versión anterior, como decisiones, salud financiera, promesas de pago y alertas por Telegram, se conservaron en esta estructura principal. Se retiraron la carpeta anidada duplicada `proyecto-cajathon/` y el archivo ZIP que contenía otra copia del proyecto. La consolidación no modificó las credenciales locales de demostración ni las claves configuradas en el entorno.

## Principios de uso de IA

El análisis es de apoyo y debe basarse en información financiera relevante. No aprueba ni rechaza solicitudes automáticamente ni debe utilizar atributos protegidos o discriminatorios. La decisión final es humana.

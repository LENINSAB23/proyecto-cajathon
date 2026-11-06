# CAJA INTELIGENTE

Sistema web de demostración para evaluación de riesgo crediticio y prevención de morosidad en Cajas Municipales de Ahorro y Crédito del Perú. La IA brinda recomendaciones explicables; el dictamen final siempre corresponde a una persona autorizada.

## Funcionalidades

- Dashboard con indicadores de clientes, solicitudes, aprobaciones, riesgo y morosidad.
- Gestión y búsqueda de clientes, perfil financiero e historial crediticio.
- Registro y simulación de solicitudes de crédito: cuota francesa, capacidad de pago, DTI e ingreso disponible.
- Evaluación de riesgo con OpenAI y motor heurístico de respaldo (sin conexión externa).
- Gestión de pagos, cuotas atrasadas, alertas preventivas y clasificación SBS.
- Reportes de evaluaciones, solicitudes, clientes de riesgo alto y morosidad en PDF y Excel.
- Mapa agregado de cartera con Leaflet/OpenStreetMap; solo traza coordenadas ingresadas y agrega ubicaciones con un mínimo de cinco clientes.
- Auditoría append-only de evaluaciones, dictámenes, observaciones administrativas y desembolsos, con una instantánea JSON de las entradas financieras y resultados.
- Salud de cartera basada en desembolsos y abonos efectivamente registrados; exportación PDF/Excel.
- Seguimiento de promesas, abonos parciales asociados, responsables, vencimientos y alertas.
- Notificaciones opcionales de Telegram para concentración alta, decisiones de alto riesgo, salud crítica y promesas.
- Roles separados, validados en las rutas del servidor:
  - **Administrador:** acceso a todos los módulos, eliminación de clientes y reportes.
  - **Analista de créditos:** clientes, solicitudes y evaluaciones; no gestiona cobranzas ni elimina clientes.
  - **Personal de cobranza:** morosidad, registro de pagos, alertas y reporte de morosidad.

Los cuatro nuevos módulos respetan los permisos por rol: mapa agregado para los tres roles, historial para administrador/analista (el analista ve solo sus eventos), salud financiera para administrador, promesas para administrador/cobranzas.

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
2. En **SQL Editor**, ejecuta `database/schema.sql`. El esquema crea las tablas de aplicación e índices, claves foráneas, timestamps y políticas RLS; la tabla `usuarios` enlaza cada perfil con el UUID de `auth.users`.
   El esquema actualizado también agrega campos geográficos opcionales, desembolsos reales, historial de decisiones, promesas y transacciones de pago. Si ya tenías una instancia, vuelve a ejecutar el SQL actualizado para aplicar sus migraciones `ADD COLUMN IF NOT EXISTS` y tablas nuevas. Haz primero un respaldo de producción.
3. En **Authentication > Users**, crea una cuenta por persona. Para asignarle un rol, copia el UUID de Auth e inserta el perfil asociado en `public.usuarios`:

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
   - `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` son opcionales; sin ambos, las notificaciones externas quedan desactivadas.
   - `HEALTH_MORA_WARNING` y `HEALTH_MORA_CRITICAL` configuran los límites porcentuales de salud (por defecto 5% y 10%; se valida que advertencia < crítico).
   - `GEO_MORA_MEDIUM` y `GEO_MORA_HIGH` configuran los colores de concentración geográfica (por defecto 8% y 20%).
5. Inicia la aplicación. Al arrancar, verifica la conexión y que existan todas las tablas requeridas; si falta el esquema, muestra un error de configuración explícito.

El backend accede a PostgreSQL mediante una URI privada del servidor. Mantén `DATABASE_URL` y las claves fuera del repositorio. Los permisos de la aplicación también se comprueban en Flask; RLS no sustituye esas validaciones.

## Despliegue en Render

1. Crea un repositorio en GitHub. Desde la carpeta del proyecto, publica el código (sin incluir `.env`, contraseñas reales ni archivos de base local):

   ```powershell
   git init
   git add .
   git commit -m "Preparar CAJA INTELIGENTE"
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
python -m compileall -q app.py config.py routes database services scripts test_app.py
```

La suite usa la base de datos local ficticia e integra autenticación por rol, módulos, IA de respaldo y exportaciones. Las pruebas no requieren claves de Supabase, OpenAI ni Telegram.

## Módulos ampliados y fórmulas

### Concentración geográfica

Ruta `/concentracion/`. Registra departamento, provincia, distrito y, opcionalmente, latitud/longitud en el formulario de clientes. No se usa geocodificación: solo aparecen marcadores creados a partir de coordenadas ingresadas y al menos cinco clientes de la misma zona; los grupos menores se suprimen y el mapa no muestra ubicaciones individuales. OpenStreetMap proporciona las teselas, con atribución visible. Los límites de color de mora por zona son configurables con `GEO_MORA_MEDIUM` (8%) y `GEO_MORA_HIGH` (20%).

### Historial de decisiones

Ruta `/decisiones/`. Cada evaluación de IA, dictamen humano, observación administrativa y desembolso genera un evento nuevo con actor, fecha, score/riesgo, estado, observación e instantánea de entradas financieras/resultados. No se sobrescriben eventos. La tabla usa triggers que rechazan UPDATE/DELETE tanto en SQLite como en PostgreSQL. El analista solo ve eventos propios; el administrador puede consultar todo. Exports admiten PDF y Excel.

### Salud financiera

Ruta `/salud-financiera/` (administrador). Fórmulas:

- **Créditos otorgados** y **monto colocado**: conteo y suma de solicitudes aprobadas con `fecha_desembolso` y `monto_desembolsado` registrados por el administrador; una aprobación por sí sola no prueba un desembolso.
- **Cartera vigente**: saldo de las cuotas programadas no marcadas pagadas, menos abonos registrados (incluye cuotas vencidas; equivale al saldo de cronograma conocido, no al saldo contable de capital).
- **Cartera vencida**: saldo de cuota más penalidad, menos abonos registrados, con fecha de vencimiento anterior al día actual.
- **Morosidad**: cartera vencida / saldo de cuotas no pagadas × 100.
- **Recuperado**: suma de transacciones de pago efectivamente registradas; los pagos históricos que solo tienen estado `PAGADO` no se convierten en montos recuperados inventados.
- **Concentración HHI**: suma de los cuadrados de la participación porcentual de la exposición impaga por departamento.
- **Salud**: verde por debajo del umbral de advertencia; amarillo desde advertencia y por debajo de crítico; rojo desde crítico. Umbrales configurables por entorno.

El sistema muestra **No disponible** para pérdida esperada (falta LGD/exposición al incumplimiento calibrada), liquidez (no existe libro de caja/depósitos) y morosidad histórica mensual (no existen snapshots históricos). La gráfica mensual solo compara desembolsos y pagos registrados. No se presentan estimaciones como observaciones reales.

### Promesas de pago

Ruta `/promesas/`. Cobranzas registra monto, fecha y responsable. En el formulario de pago de cuota se captura el importe realmente recibido y se puede asociar expresamente a una promesa del mismo cliente. Las transacciones se conservan separadas de las cuotas programadas; abonos acumulados cubren promesas y cuotas parcialmente. El estado se recalcula al abrir promesas o morosidad: pendiente antes de la fecha, vencida el día comprometido, incumplida después de la fecha si falta saldo, cumplida cuando los abonos alcanzan el compromiso (incluso si el pago llega tarde). Se crean alertas locales y avisos opcionales para vencimientos próximos/incumplimientos. Para que las alertas se procesen aunque nadie abra la interfaz, programa `python -m scripts.check_promises` diariamente en Task Scheduler (Windows) o como Cron Job en Render, con las mismas variables de entorno de la aplicación.

### Telegram

Configura el token y chat en variables de entorno del servidor. Los avisos son opcionales, se envían con timeout y deduplicación, y un fallo de Telegram no bloquea la operación. Ningún token se envía al navegador ni se escribe en logs.

## Estructura principal

```text
app.py                  Aplicación Flask y configuración de contexto
config.py               Variables de entorno y validación de producción
database/db.py          Acceso a SQLite local o PostgreSQL de Supabase
database/schema.sql     Esquema PostgreSQL, índices y RLS
database/seed_data.py   Datos ficticios para SQLite local
routes/                 Autenticación y módulos de la plataforma
services/               Scoring, análisis IA, salud, snapshots y Telegram
templates/              Vistas HTML/Jinja
static/                 CSS, JavaScript e imágenes
scripts/                Tarea programable de revisión de promesas
render.yaml             Configuración de despliegue
```

## Principios de uso de IA

El análisis es de apoyo y debe basarse en información financiera relevante. No aprueba ni rechaza solicitudes automáticamente ni debe utilizar atributos protegidos o discriminatorios. La decisión final es humana.

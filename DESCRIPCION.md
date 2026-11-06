# CAJA INTELIGENTE &bull; Documentación Integral del Proyecto

## 1. Visión General del Sistema

**CAJA INTELIGENTE** es una plataforma SaaS de tecnología financiera (Fintech) de nivel empresarial diseñada específicamente para **prevenir, identificar y evaluar riesgos crediticios** en el ecosistema de las Cajas Municipales de Ahorro y Crédito (CMAC) del Perú y entidades microfinancieras reguladas por la **Superintendencia de Banca, Seguros y AFP (SBS)**.

El objetivo central del sistema es asistir a los analistas y comités de crédito en la toma de decisiones informadas, transparentes y éticas, sustentadas en el análisis cuantitativo del flujo de caja, capacidad de pago y endeudamiento sistémico, complementado con el poder explicativo de la Inteligencia Artificial.

---

## 2. Bank-ito: La Inteligencia Artificial del Proyecto

**Bank-ito** es el Oficial Senior de Inteligencia Financiera y Asesor Copiloto de Riesgo Crediticio integrado en la plataforma. Está potenciado por la API de **Google Gemini** con un motor de respaldo heurístico adaptado a la normativa SBS.

### Principales Capacidades de Bank-ito:
1. **Scoring Crediticio Explicable (0 a 100 Puntos):** 
   - No actúa como una "caja negra": desglosa de forma transparente por qué se asigna un puntaje y clasifica el riesgo en **Bajo**, **Medio** o **Alto**.
2. **Factores Positivos y Vulnerabilidades:**
   - Detecta fortalezas financieras (flujo libre holgado, puntualidad histórica, estabilidad laboral formal).
   - Identifica factores de riesgo (sobreendeudamiento, atrasos esporádicos, informalidad comercial).
3. **Señales de Alerta Preventiva (*Red Flags*):**
   - Dispara advertencias automáticas cuando el ratio DTI (*Debt-to-Income*) supera el umbral prudencial del 35% o alcanza niveles críticos (>50%).
4. **Proyección de Morosidad Anticipada:**
   - Estima la probabilidad porcentual de incurrir en atrasos a 30 días y de ingresar a cartera pesada a 90 días (Categorías Deficiente, Dudoso o Pérdida).
5. **Bank-ito Copilot Interactivo:**
   - Drawer lateral deslizable accesible desde cualquier pantalla del sistema para resolver consultas regulatorias, metodologías de cálculo financiero y recomendaciones de mitigación en tiempo real.
6. **Ética y Gobernanza SBS:**
   - La IA genera recomendaciones de apoyo técnico. El dictamen final de aprobación o denegación es siempre una **responsabilidad humana vinculante** registrada por el comité.

---

## 3. Módulos y Flujos de la Plataforma

### A. Dashboard Financiero y Gestión de Riesgos
- **Indicadores Clave (KPIs):** Monitoreo en vivo de clientes activos, solicitudes totales, tasa de colocación de créditos aprobados, solicitudes en revisión, clientes en riesgo alto y ratio de morosidad sistémico.
- **Gráficos Interactivos con Chart.js:**
  - *Evolución de Solicitudes vs Colocaciones:* Comparativa de montos aprobados y volúmenes solicitados.
  - *Distribución de Riesgos SBS:* Gráfico donut ponderado por clasificaciones de riesgo.
- **Actividad Reciente y Alertas:** Vista rápida de últimas solicitudes y alertas preventivas tempranas.

### B. Gestión de Clientes 360°
- Expediente financiero centralizado del cliente.
- Desglose de ingresos netos verificados, cargas fijas mensuales y pasivos preexistentes.
- Pestañas con historial de solicitudes, cronogramas de pago y registro histórico en centrales de riesgo SBS.
- Filtros por nivel de riesgo y buscador instantáneo por DNI o nombres.

### C. Admisión y Solicitudes de Crédito (con Simulador en Tiempo Real)
- Registro integral de solicitudes por tipo de producto (MYPE, Capital de Trabajo, Consumo, Hipotecario).
- **Simulador Financiero en Vivo:** Calcula automáticamente:
  - Cuota mensual estimada bajo el **método de amortización francés**.
  - Ratio de endeudamiento **DTI** (`Pasivos Mensuales / Ingreso Bruto * 100`).
  - Capacidad de pago admisible según umbrales prudenciales.
  - Excedente o flujo libre neto disponible post-cuota.
  - Pre-dictamen cuantitativo de viabilidad crediticia.

### D. Matriz de Riesgo y Evaluación Asistida por IA
- Vista detallada de dictámenes emitidos por Bank-ito IA.
- Indicador visual de score crediticio y barras de probabilidad de morosidad proyectada.
- Registro formal del **Dictamen Humano del Comité de Créditos** (`CONFORME`, `OBSERVADO / REQUIERE GARANTÍA` o `DENEGADO`) con fundamentación obligatoria para fines de auditoría.

### E. Gestión de Morosidad, Cobranzas y Alertas Preventivas
- Control de mora temprana (1 a 8 días) para evitar reclasificación a Categoría CPP (Con Problemas Potenciales).
- Cuadrícula de atención urgente para clientes críticos en mora con acceso directo a contacto telefónico.
- Cronograma de cuotas auditadas y emisión manual de alertas preventivas.

### F. Centro de Reportes Financieros y Auditoría
- Generación de expedientes oficiales conforme a requerimientos de auditoría:
  - **Exportación en PDF:** Membrete institucional, parámetros de riesgo y firmas del comité vía ReportLab.
  - **Exportación en Excel (.xlsx):** Hojas de cálculo detalladas con fórmulas de cartera procesadas vía OpenPyXL.

---

## 4. Arquitectura Tecnológica

| Capa | Tecnologías Utilizadas |
| :--- | :--- |
| **Backend** | Python 3.10+, Flask 3.0+, Gunicorn |
| **Base de Datos** | PostgreSQL (Supabase en Producción) / SQLite (Desarrollo Local) |
| **Autenticación** | Supabase Auth en Producción / Sesiones seguras HTTP-Only |
| **Inteligencia Artificial** | Google Gemini API (`gemini-flash-lite-latest` / `gemini-3.8-flash`) con fallback a motor heurístico SBS |
| **Frontend** | HTML5 semántico, Jinja2, Bootstrap 5.3 (grid/utilidades), FontAwesome 6 |
| **Estilos & Diseño** | CSS3 corporativo (Fintech Design System: Deep Navy `#0A192F`, Petrol Blue `#0284C7`) |
| **Visualización** | Chart.js 4 (gráficos donut y barras adaptadas con tipografía Inter) |
| **Exportación** | ReportLab (PDF bancario), OpenPyXL (Excel financiero) |
| **Despliegue** | Render Web Service / Blueprints (`render.yaml`) |

---

## 5. Roles y Permisos de Acceso

La plataforma implementa un control de acceso basado en roles (RBAC) validado tanto en las rutas del servidor como en la interfaz gráfica:

1. **Administrador (`admin@creditrisk.pe`):**
   - Acceso total a todos los módulos: dashboard, clientes, solicitudes, matriz de riesgo, morosidad y auditoría.
   - Capacidad de dar de baja clientes y emitir reportes ejecutivos.
2. **Analista de Créditos (`analista@creditrisk.pe`):**
   - Acceso enfocado a la prospección y admisión: padrón de clientes, creación y simulación de solicitudes, ejecución de evaluaciones con Bank-ito IA y emisión de dictámenes de comité.
   - Restringido de operaciones de cobranza y eliminación de registros.
3. **Personal de Cobranzas (`cobranzas@creditrisk.pe`):**
   - Acceso enfocado en recuperaciones y cartera vencida: centro de morosidad, actualización de estados de pago, emisión de alertas preventivas y descarga de cartera morosa.
   - Restringido de evaluación de solicitudes y gestión de analistas.

---

## 6. Guía de Conexión: Supabase & Render

### A. Configuración en Supabase
1. Crea un proyecto en [supabase.com](https://supabase.com).
2. Abre el **SQL Editor** y ejecuta el script [`database/schema.sql`](file:///c:/Users/LENIN/Documents/SENATI/CREDIT-RISK/database/schema.sql) para crear las tablas, relaciones, claves primarias UUID e índices de búsqueda.
3. En **Project Settings > API**, obtén tu `SUPABASE_URL` y tu clave pública `SUPABASE_KEY` (anon).
4. En **Project Settings > Database > Connection string > URI**, copia la cadena del **Pooler IPv4** (puerto `6543`) para asegurar compatibilidad total con los servidores de Render.

### B. Despliegue en Render
1. Conecta tu repositorio de GitHub en [render.com](https://render.com) como **Web Service**.
2. Parámetros de ejecución:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
3. Variables de entorno recomendadas:
   - `FLASK_ENV`: `production`
   - `FLASK_DEBUG`: `False`
   - `SECRET_KEY`: *(Generar clave criptográfica privada)*
   - `DEMO_MODE`: `False`
   - `DEMO_LOGIN_ENABLED`: `False`
   - `SUPABASE_URL`: `https://[TU-PROYECTO].supabase.co`
   - `SUPABASE_KEY`: `[TU-CLAVE-ANON]`
   - `DATABASE_URL`: `postgresql://postgres.[PROYECTO]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres`
   - `GEMINI_API_KEY`: `[TU-CLAVE-DE-GEMINI]`
   - `GEMINI_MODEL`: `gemini-flash-lite-latest`
4. Comprueba la disponibilidad en el endpoint de salud: `GET /health` &rarr; `{"status": "ok"}`.

---

## 7. Marco Regulatorio y Cumplimiento SBS

El sistema ha sido estructurado respetando los principios de la **Resolución SBS N° 11356-2008**:
- **Categoría 0 (Normal):** Créditos al día o con mora inferior a 8 días.
- **Categoría 1 (CPP - Con Problemas Potenciales):** Atrasos entre 9 y 30 días en cartera microempresa y consumo.
- **Categoría 2 (Deficiente):** Atrasos entre 31 y 60 días.
- **Categoría 3 (Dudoso):** Atrasos entre 61 y 120 días.
- **Categoría 4 (Pérdida):** Atrasos superiores a 120 días.
- **Prudencia Financiera:** Recomendación de mantener el ratio DTI inferior al 35% y exigir garantías o avales solidarios para ratios entre 35% y 50%.


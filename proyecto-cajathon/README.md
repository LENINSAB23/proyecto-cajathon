# 🏛️ CAJA INTELIGENTE
### Sistema de Evaluación de Riesgo Crediticio y Prevención de Morosidad con Inteligencia Artificial
> **Especialidad:** Riesgos Financieros y Microfinanzas para Cajas Municipales de Ahorro y Crédito (CMAC) del Perú  
> **Cumplimiento Regulatorio:** Superintendencia de Banca, Seguros y AFP (SBS Perú - Resolución N° 11356-2008)

---

## 📌 1. Visión General del Proyecto

**CAJA INTELIGENTE** es una plataforma web fintech de nivel empresarial diseñada específicamente para las Cajas Municipales del Perú (CMAC Arequipa, Huancayo, Piura, Cusco, etc.). 

Su propósito fundamental es modernizar el proceso de admisión crediticia y gestión de cobranzas mediante:
1. **Scoring Crediticio Cuantitativo:** Cálculo automático de ratios financieros clave (DTI, Capacidad de Pago ponderada, Cuota fija francesa).
2. **Evaluación Cualitativa con Inteligencia Artificial (OpenAI GPT-4o-mini & Motor Heurístico SBS):** Generación de dictámenes explicativos, factores positivos, debilidades, alertas tempranas (Red Flags) y probabilidades de morosidad a 30 y 90 días.
3. **Decisión Humana Vinculante:** Asistencia al analista financiero sin sustituir el criterio del comité humano.
4. **Gestión Proactiva de Morosidad:** Detección de cuotas vencidas, días de atraso, penalidades y categorización oficial SBS (Normal, CPP, Deficiente, Dudoso, Pérdida).
5. **Auditoría y Reportes:** Exportación ejecutiva a PDF con membrete institucional y hojas de cálculo Excel (.xlsx).

---

## 💻 2. Stack Tecnológico

- **Backend:** Python 3.10+ / Flask 3.x (Arquitectura modular con Blueprints).
- **Servidor de Producción:** Gunicorn.
- **Base de Datos de producción:** Supabase PostgreSQL mediante conexión segura del servidor.
- **Base de datos local:** SQLite 3 con esquema y datos de muestra para desarrollo sin conexión.
- **Inteligencia Artificial:** OpenAI API (`gpt-4o-mini`) + Motor de Inferencia Heurística Local para modo demostración sin conexión.
- **Frontend:** HTML5 semántico, CSS3 Fintech profesional (estética banking en azul noche, blanco y acentos cyan), JavaScript Vanilla, Bootstrap 5.3 y FontAwesome 6.
- **Visualización Gráfica:** Chart.js (Donut de distribución de riesgos y barras de colocaciones).
- **Generación de Reportes:** ReportLab (PDF) y OpenPyXL (Excel).
- **Despliegue:** Render (`Procfile`, `render.yaml`).

---

## 📂 3. Arquitectura del Proyecto

```text
cajathon/
├── app.py                      # Punto de entrada de la aplicación Flask
├── config.py                   # Configuración centralizada y variables de entorno
├── requirements.txt            # Dependencias oficiales de producción
├── Procfile                    # Comando de arranque para Render (Gunicorn)
├── render.yaml                 # Configuración de infraestructura como código (Render Blueprint)
├── .env.example                # Plantilla de variables de entorno seguras
├── .gitignore                  # Exclusión de credenciales y archivos temporales
├── README.md                   # Documentación técnica completa
├── test_app.py                 # Suite de pruebas de integración
│
├── database/
│   ├── schema.sql              # Esquema PostgreSQL aplicado a Supabase al iniciar la app
│   ├── db.py                   # Acceso Supabase PostgreSQL / SQLite local y semilla de muestra
│   └── seed_data.py            # Sembrado de 17 clientes, 20 solicitudes, pagos y alertas
│
├── routes/
│   ├── __init__.py
│   ├── auth.py                 # Inicio/cierre de sesión y control de acceso por roles
│   ├── dashboard.py            # KPIs ejecutivos y endpoints de gráficos
│   ├── clientes.py             # CRUD de clientes y expediente financiero 360°
│   ├── creditos.py             # Solicitudes y simulador financiero interactivo
│   ├── riesgos.py              # Matriz de riesgos y dictámenes con Inteligencia Artificial
│   ├── morosidad.py            # Monitoreo de cartera vencida, pagos y alertas
│   └── reportes.py             # Centro de descargas en PDF y Excel
│
├── services/
│   ├── __init__.py
│   ├── credit_scoring.py       # Fórmulas financieras SBS (DTI, Capacidad de pago, Cuota)
│   ├── ia_service.py           # Cliente OpenAI y Motor Heurístico de Inferencia SBS
│   └── report_service.py       # Generadores de documentos PDF (ReportLab) y Excel (OpenPyXL)
│
├── templates/
│   ├── base.html               # Layout maestro (Sidebar, Topbar, Notificaciones)
│   ├── login.html              # Login fintech con accesos rápidos de 1 clic para el jurado
│   ├── dashboard.html          # Dashboard principal con métricas y Chart.js
│   ├── clientes.html           # Padrón de clientes y modal de registro
│   ├── cliente_detalle.html    # Expediente 360° con central de riesgos SBS
│   ├── creditos.html           # Solicitudes y simulador en tiempo real
│   ├── evaluacion.html         # Resultados de IA, score 0-100 y dictamen humano
│   ├── riesgos_matriz.html     # Matriz general de cartera evaluada
│   ├── morosidad.html          # Centro de cobranzas, abonos y alertas tempranas
│   └── reportes.html           # Centro de descargas directas en PDF y Excel
│
└── static/
    ├── css/
    │   └── style.css           # Estilos fintech de alta gama inspirados en banca moderna
    ├── js/
    │   └── app.js              # Gráficos Chart.js, simulador reactivo y filtros de tabla
    └── img/
        └── logo.svg            # Isotipo institucional vectorizado
```

---

## 🧮 4. Modelos y Fórmulas Financieras (SBS / CMAC)

### A. Cálculo de Cuota Fija (Método Francés)
$$\text{Cuota} = \text{Monto} \times \frac{i \times (1+i)^n}{(1+i)^n - 1}$$
Donde $i$ es la Tasa Efectiva Mensual (TEM, aprox. 2.8% en microfinanzas) y $n$ es el número de meses.

### B. Ratio Deuda / Ingresos (Debt-to-Income - DTI)
$$\text{DTI} = \left( \frac{\text{Deudas Preexistentes} + \text{Cuota Mensual Proyectada}}{\text{Ingresos Mensuales Declarados}} \right) \times 100$$
- **DTI $\le$ 35%:** Nivel Óptimo (Riesgo Bajo).
- **35% $<$ DTI $\le$ 50%:** Nivel Moderado / Advertencia (Riesgo Medio).
- **DTI $>$ 50%:** Sobreendeudamiento Crítico (Riesgo Alto).

### C. Capacidad de Pago Ponderada
$$\text{Capacidad de Pago} = (\text{Ingresos} - \text{Gastos}) \times 0.85$$

### D. Clasificación Regulatoria de Morosidad (SBS Perú)
- **Normal (Categoría 0):** 0 a 8 días de atraso.
- **Con Problemas Potenciales CPP (Categoría 1):** 9 a 30 días de atraso.
- **Deficiente (Categoría 2):** 31 a 60 días de atraso.
- **Dudoso (Categoría 3):** 61 a 120 días de atraso.
- **Pérdida (Categoría 4):** Más de 120 días de atraso.

---

## 🤖 5. Inteligencia Artificial y Modo Demostración

El módulo de IA evalúa de manera holística:
- Solvencia económica y cobertura de cuota.
- Ratio de endeudamiento DTI y dispersión de gastos.
- Comportamiento en centrales de riesgo SBS.
- Estabilidad de la actividad comercial o empleo.

### Resiliencia de la Plataforma:
1. **Con Clave OpenAI (`OPENAI_API_KEY`):** Se comunica con el modelo `gpt-4o-mini` para redactar evaluaciones enriquecidas en formato estructurado JSON.
2. **Sin Clave / Modo Demostración:** El **Motor de Inferencia Heurística Local** analiza las mismas variables financieras conforme a la normativa SBS y genera dictámenes idénticos en profundidad, recomendaciones y probabilidades de mora, garantizando que el jurado o usuario pueda probar el 100% de la funcionalidad de inmediato sin incurrir en costos ni depender de conexión externa.

---

## 🚀 6. Guía de Ejecución Local

### Paso 1: Clonar el Repositorio
```bash
git clone https://github.com/TU-USUARIO/caja-inteligente.git
cd caja-inteligente
```

### Paso 2: Crear y Activar un Entorno Virtual
```bash
# En Windows:
python -m venv venv
venv\Scripts\activate

# En Linux / macOS:
python3 -m venv venv
source venv/bin/activate
```

### Paso 3: Instalar Dependencias
```bash
pip install -r requirements.txt
```

### Paso 4: Configurar Variables de Entorno (Opcional)
Copia el archivo `.env.example` a `.env`:
```bash
cp .env.example .env
```
*(En desarrollo, el sistema funciona con base de datos SQLite local y motor de IA heurístico sin claves externas).*

### Paso 5: Iniciar la Aplicación
```bash
python app.py
```
Abre en tu navegador: **http://127.0.0.1:5000**

---

## 👥 7. Credenciales de Demostración

En desarrollo (`DEMO_MODE=True`) hay 3 perfiles de demostración y botones de acceso rápido. No se exponen esos accesos en producción:

| Rol | Correo Electrónico | Contraseña | Alcance y Permisos |
| :--- | :--- | :--- | :--- |
| **Administrador** | `admin@cajainteligente.pe` | `admin123` | Control total, auditoría, eliminación y configuración |
| **Analista de Créditos** | `analista@cajainteligente.pe` | `analista123` | Creación de clientes, simulación y evaluación con IA |
| **Personal de Cobranzas** | `cobranzas@cajainteligente.pe` | `cobranza123` | Gestión de mora, registro de abonos y emisión de alertas |

Estas credenciales son únicamente para la base de datos de demostración local; no las uses en un despliegue público.

---

## 🗄️ 8. Base de datos

En producción, la aplicación se conecta directamente al PostgreSQL de Supabase usando `DATABASE_URL` (URI de conexión). El backend aplica `database/schema.sql` al iniciar y crea la primera cuenta administradora con `INITIAL_ADMIN_EMAIL` y `INITIAL_ADMIN_PASSWORD`. Las tablas tienen RLS habilitado sin políticas públicas; el navegador no usa claves de Supabase ni accede directamente a las tablas.

En Render configura `DATABASE_URL` con la URI **Session pooler** de Supabase y SSL (en Supabase: **Connect > Session pooler**). SQLite se utiliza solamente cuando no hay `DATABASE_URL` configurada fuera de producción. Si ya ejecutaste un esquema PostgreSQL anterior con IDs UUID, utiliza una base nueva/vacía o migra esos datos antes de aplicar el esquema actual, que usa IDs de texto compatibles con la aplicación.

---

## 🌐 9. Guía Paso a Paso para Despliegue en Render

### Paso 1: Subir el Código a GitHub
```bash
git init
git add .
git commit -m "feat: Lanzamiento de plataforma Caja Inteligente CMAC"
git branch -M main
git remote add origin https://github.com/TU-USUARIO/caja-inteligente.git
git push -u origin main
```

### Paso 2: Crear el servicio desde el Blueprint
1. Inicia sesión en [https://render.com/](https://render.com/).
2. Haz clic en **New + > Blueprint**.
3. Conecta el repositorio de GitHub que contiene `render.yaml` y aplica el Blueprint.
   Antes del primer arranque, crea un proyecto Supabase y copia en `DATABASE_URL` la URI PostgreSQL del **Session pooler**. Si la contraseña contiene caracteres especiales, conserva la codificación URL de la URI que entrega Supabase.
4. El Blueprint configura:
   - **Environment:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
5. En la configuración del servicio, define las variables secretas que solicita el Blueprint:
   - `FLASK_ENV` = `production`
   - `FLASK_DEBUG` = `False`
   - `SECRET_KEY` = *(Render la genera automáticamente)*
   - `DATABASE_URL` = *(URI de conexión PostgreSQL de Supabase; usa Session pooler y SSL)*
   - `INITIAL_ADMIN_EMAIL` y `INITIAL_ADMIN_PASSWORD` = *(credenciales seguras para crear el administrador inicial; contraseña de 12 caracteres como mínimo)*
   - `DEMO_MODE` = `False` para permitir el uso de OpenAI; sin `OPENAI_API_KEY`, el motor heurístico funciona como respaldo.
   - `OPENAI_API_KEY` = *(opcional; clave de OpenAI)*
   
   Los accesos rápidos de demostración quedan deshabilitados en producción. En desarrollo local siguen disponibles con `DEMO_MODE=True`.
6. Crea el servicio. Render instalará las dependencias, comprobará/creará el esquema Supabase y expondrá la aplicación por HTTPS.

---

## 🧪 10. Pruebas Automatizadas

El proyecto incluye una suite de pruebas unitarias y de integración que valida todos los módulos:
```bash
python test_app.py
```
La suite comprueba 20 flujos, incluyendo login, health check, permisos por rol, validación financiera, dashboard, simulador, evaluación IA, morosidad y exportaciones PDF/Excel.

---

## ⚖️ 11. Aviso Ético y Cumplimiento SBS

> **Nota de Cumplimiento Regulatorio:**  
> La inteligencia artificial integrada en esta plataforma opera bajo el principio de **IA explicable como soporte al analista financiero**. En estricto cumplimiento con la normativa de la SBS del Perú y principios de equidad algorítmica, el sistema no discrimina por variables protegidas (edad, sexo, etnia, religión) ni emite aprobaciones o rechazos automáticos vinculantes. Toda resolución final requiere la firma y fundamentación de un funcionario de crédito humano.

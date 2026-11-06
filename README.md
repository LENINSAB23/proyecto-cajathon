# 🏛️ Credit Risk
### Sistema de Evaluación de Riesgo Crediticio y Prevención de Morosidad con Inteligencia Artificial
> **Especialidad:** Gestión de Riesgos Financieros y Evaluación de Morosidad para Cajas Municipales de Ahorro y Crédito (CMAC) del Perú  
> **Marco Regulatorio:** Superintendencia de Banca, Seguros y AFP (SBS Perú - Resolución N° 11356-2008)

---

## 📌 1. Visión General del Proyecto

**Credit Risk** es una plataforma web orientada al sector financiero y de microfinanzas, diseñada para asistir a los analistas y comités de crédito de las Cajas Municipales en la toma de decisiones informadas, transparentes y seguras.

El sistema aborda dos de los principales desafíos en la gestión crediticia:
1. **Evaluación Rigurosa del Riesgo:** Análisis multifactorial de la solvencia del solicitante, combinando ratios financieros tradicionales con modelos avanzados de inteligencia artificial.
2. **Detección Temprana y Prevención de Morosidad:** Monitoreo constante del comportamiento de pago, alertas preventivas ante descalces de liquidez y clasificación de cartera conforme a la normativa SBS.

---

## 💻 2. Módulos del Sistema

### Módulo 1: Dashboard Financiero
- Indicadores clave de desempeño (KPIs): Total de colocaciones, clientes registrados, créditos aprobados, solicitudes en trámite, porcentaje de morosidad y clientes clasificados en riesgo alto.
- Gráficos interactivos de evolución mensual de colocaciones y distribución de cartera por niveles de riesgo.
- Notificaciones de actividad reciente y alertas financieras de atención inmediata.

### Módulo 2: Gestión de Clientes 360°
- Expediente digital completo del cliente: historial laboral, actividad económica, ingresos mensuales, gastos fijos y pasivos vigentes.
- Consulta centralizada y verificación de antecedentes en centrales de riesgo.
- Búsqueda y filtrado multicriterio por DNI, nombres o nivel de solvencia.

### Módulo 3: Admisión y Evaluación de Créditos
- Simulador financiero en tiempo real: cálculo inmediato de la cuota mensual mediante el método de amortización francés.
- Evaluación de indicadores clave: Capacidad de pago admisible, relación Deuda/Ingresos (DTI) y flujo neto disponible.
- Semáforo automático de viabilidad financiera.

### Módulo 4: Análisis con Inteligencia Artificial
- Evaluación explicativa cualitativa y cuantitativa que asigna un Score de Riesgo (0 a 100 puntos) y categoriza al cliente en:
  - **Riesgo Bajo:** Condiciones financieras óptimas y solvencia verificada.
  - **Riesgo Medio:** Requiere evaluación complementaria o garantías de respaldo.
  - **Riesgo Alto:** Señales de sobreendeudamiento o déficit de liquidez.
- Identificación estructurada de fortalezas financieras, vulnerabilidades operativas y alertas preventivas.
- Estimación de probabilidades de incumplimiento a 30 y 90 días.
- **Dictamen Humano Vinculante:** La IA actúa como soporte analítico para el oficial de créditos, garantizando que la decisión final sea siempre humana y conforme a políticas internas.

### Módulo 5: Gestión y Prevención de Morosidad
- Clasificación regulatoria de la cartera según directivas SBS:
  - Categoría 0: Normal (atraso de 0 a 8 días).
  - Categoría 1: Con Problemas Potenciales - CPP (atraso de 9 a 30 días).
  - Categoría 2: Deficiente (atraso de 31 a 60 días).
  - Categoría 3: Dudoso (atraso de 61 a 120 días).
  - Categoría 4: Pérdida (atraso superior a 120 días).
- Registro ágil de amortizaciones y cancelaciones de cuotas.
- Generación de alertas de cobranza preventiva ante indicios de mora temprana.

### Módulo 6: Centro de Reportes Financieros
- Generación de reportes ejecutivos en formato **PDF** con membrete institucional para comités de riesgo y auditoría.
- Exportación estructurada de cartera y vencimientos a **Excel (.xlsx)** para análisis contable y financiero.

---

## 🧮 3. Fundamentos y Fórmulas Financieras

### A. Cuota Fija Mensual (Sistema Francés)
$$\text{Cuota} = \text{Monto} \times \frac{i \times (1+i)^n}{(1+i)^n - 1}$$
Donde $i$ representa la Tasa Efectiva Mensual (TEM) y $n$ el plazo en meses.

### B. Ratio de Endeudamiento Total (Debt-to-Income - DTI)
$$\text{DTI} = \left( \frac{\text{Deudas Vigentes} + \text{Cuota Proyectada}}{\text{Ingresos Mensuales}} \right) \times 100$$
- $\text{DTI} \le 35\%$: Endeudamiento prudencial y sostenible.
- $35\% < \text{DTI} \le 50\%$: Endeudamiento moderado (alerta preventiva).
- $\text{DTI} > 50\%$: Sobreendeudamiento crítico.

### C. Capacidad de Pago Ponderada
$$\text{Capacidad de Pago} = (\text{Ingresos} - \text{Gastos}) \times 0.85$$

---

## 👥 4. Roles y Control de Acceso

La plataforma separa las tareas y los permisos de cada perfil:

- **Administrador:** Acceso a todos los módulos, supervisión de cartera, eliminación de clientes y reportes financieros para auditoría.
- **Analista de Créditos:** Registro y actualización de clientes, simulación y creación de solicitudes, evaluación de riesgo con IA y dictamen humano. No puede eliminar clientes ni gestionar cobranzas.
- **Personal de Cobranzas:** Seguimiento exclusivo de cuotas vencidas, registro de pagos, emisión de alertas preventivas y exportación del reporte de morosidad. No puede acceder a clientes, solicitudes de crédito, evaluaciones ni reportes generales.

Al iniciar sesión, cada perfil ingresa directamente a su espacio de trabajo: el administrador y el analista al dashboard, y cobranzas al centro de morosidad. Los permisos se validan también en el servidor, no solo en el menú.

---

## 🚀 5. Ejecución del Sistema

### 1. Instalación de Dependencias
```bash
pip install -r requirements.txt
```

### 2. Iniciar la Plataforma
```bash
python app.py
```
Acceder mediante el navegador web en: **http://127.0.0.1:5000**

---

## ⚖️ 6. Cumplimiento Normativo y Principios Éticos

> **Declaración de Conformidad SBS:**  
> La inteligencia artificial implementada en **Credit Risk** opera como una herramienta de apoyo analítico para los comités y funcionarios de crédito. En cumplimiento con la normativa peruana, el sistema no aprueba ni deniega solicitudes de forma automática, ni considera variables protegidas o discriminatorias. Toda decisión final sobre la concesión crediticia es emitida de forma humana por el personal autorizado.

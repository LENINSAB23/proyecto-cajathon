/**
 * CAJA INTELIGENTE - JavaScript de Interfaz & Gráficos
 * Control de Simulador en Tiempo Real, Integración Chart.js y Filtros Dinámicos
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Alternador de Sidebar Móvil
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('appSidebar');
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('show');
        });
    }

    // 2. Gráficos de Chart.js en Dashboard
    initDashboardCharts();

    // 3. Simulador de Crédito en Tiempo Real
    initCreditSimulator();

    // 4. Auto-llenado de datos de cliente en formulario de solicitud
    initCustomerSelector();

    // 5. Búsqueda y filtrado interactivo en tablas
    initTableSearch();
});

function initDashboardCharts() {
    // Gráfico de Distribución de Riesgos (Donut)
    const ctxRiesgo = document.getElementById('chartDistribucionRiesgo');
    if (ctxRiesgo) {
        const bajo = parseInt(ctxRiesgo.dataset.bajo || 0);
        const medio = parseInt(ctxRiesgo.dataset.medio || 0);
        const alto = parseInt(ctxRiesgo.dataset.alto || 0);

        new Chart(ctxRiesgo, {
            type: 'doughnut',
            data: {
                labels: ['Riesgo Bajo (Apto)', 'Riesgo Medio (En Observación)', 'Riesgo Alto (Crítico)'],
                datasets: [{
                    data: [bajo, medio, alto],
                    backgroundColor: ['#10B981', '#F59E0B', '#EF4444'],
                    hoverBackgroundColor: ['#059669', '#D97706', '#DC2626'],
                    borderWidth: 2,
                    borderColor: '#FFFFFF'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            font: { family: 'Inter', size: 12 },
                            usePointStyle: true,
                            padding: 18
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const val = context.raw || 0;
                                const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
                                return ` ${context.label}: ${val} (${pct}%)`;
                            }
                        }
                    }
                },
                cutout: '72%'
            }
        });
    }

    // Gráfico de Solicitudes y Colocaciones por Mes (Barras & Línea)
    const ctxMeses = document.getElementById('chartSolicitudesMes');
    if (ctxMeses) {
        new Chart(ctxMeses, {
            type: 'bar',
            data: {
                labels: ['Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre'],
                datasets: [
                    {
                        type: 'bar',
                        label: 'Colocaciones Aprobadas (S/.)',
                        data: [28000, 39000, 51000, 64000, 71000, 92000],
                        backgroundColor: '#0284C7',
                        borderRadius: 6,
                        order: 2
                    },
                    {
                        type: 'line',
                        label: 'Volumen Solicitado (S/.)',
                        data: [35000, 48000, 62000, 75000, 89000, 115000],
                        borderColor: '#F59E0B',
                        backgroundColor: 'rgba(245, 158, 11, 0.1)',
                        borderWidth: 3,
                        pointBackgroundColor: '#F59E0B',
                        tension: 0.3,
                        order: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            font: { family: 'Inter', size: 12 },
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return ` ${context.dataset.label}: S/. ${context.raw.toLocaleString('es-PE')}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: '#F1F5F9' },
                        ticks: {
                            callback: function(val) {
                                return 'S/. ' + (val / 1000) + 'k';
                            }
                        }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });
    }
}

function initCreditSimulator() {
    const montoInput = document.getElementById('sim_monto');
    const plazoInput = document.getElementById('sim_plazo');
    const ingresosInput = document.getElementById('sim_ingresos');
    const gastosInput = document.getElementById('sim_gastos');
    const deudasInput = document.getElementById('sim_deudas');
    const tasaInput = document.getElementById('sim_tasa');

    if (!montoInput || !plazoInput) return;

    const actualizarCalculo = () => {
        const monto = parseFloat(montoInput.value) || 0;
        const plazo = parseInt(plazoInput.value) || 12;
        const ingresos = parseFloat(ingresosInput ? ingresosInput.value : 0) || 0;
        const gastos = parseFloat(gastosInput ? gastosInput.value : 0) || 0;
        const deudas = parseFloat(deudasInput ? deudasInput.value : 0) || 0;
        const tasa = parseFloat(tasaInput ? tasaInput.value : 0.028) || 0.028;

        fetch('/creditos/simular', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ monto, plazo, ingresos, gastos, deudas, tasa })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                // Actualizar labels en UI
                const cuotaEl = document.getElementById('res_cuota');
                const dtiEl = document.getElementById('res_dti');
                const capacidadEl = document.getElementById('res_capacidad');
                const disponibleEl = document.getElementById('res_disponible');
                const semaforoEl = document.getElementById('res_semaforo');
                const diagEl = document.getElementById('res_diagnostico');

                if (cuotaEl) cuotaEl.textContent = `S/. ${data.cuota_mensual.toLocaleString('es-PE', { minimumFractionDigits: 2 })}`;
                if (dtiEl) dtiEl.textContent = `${data.ratio_dti}%`;
                if (capacidadEl) capacidadEl.textContent = `S/. ${data.capacidad_pago.toLocaleString('es-PE', { minimumFractionDigits: 2 })}`;
                if (disponibleEl) {
                    disponibleEl.textContent = `S/. ${data.ingreso_disponible.toLocaleString('es-PE', { minimumFractionDigits: 2 })}`;
                    disponibleEl.className = data.ingreso_disponible >= 0 ? 'text-success fw-bold' : 'text-danger fw-bold';
                }

                if (semaforoEl) {
                    if (data.semaforo === 'VERDE') {
                        semaforoEl.className = 'badge badge-risk badge-risk-low';
                        semaforoEl.textContent = '● Viabilidad Alta';
                    } else if (data.semaforo === 'AMARILLO') {
                        semaforoEl.className = 'badge badge-risk badge-risk-medium';
                        semaforoEl.textContent = '● Viabilidad Media';
                    } else {
                        semaforoEl.className = 'badge badge-risk badge-risk-high';
                        semaforoEl.textContent = '● Riesgo Alto';
                    }
                }

                if (diagEl) diagEl.textContent = data.diagnostico;
            }
        })
        .catch(err => console.error('Error al simular crédito:', err));
    };

    [montoInput, plazoInput, ingresosInput, gastosInput, deudasInput, tasaInput].forEach(input => {
        if (input) {
            input.addEventListener('input', actualizarCalculo);
        }
    });

    // Ejecutar primer cálculo inicial
    actualizarCalculo();
}

function initCustomerSelector() {
    const selectCliente = document.getElementById('selectClienteCredito');
    if (!selectCliente) return;

    selectCliente.addEventListener('change', function() {
        const option = this.options[this.selectedIndex];
        if (!option || !option.value) return;

        const ingresos = option.dataset.ingresos || 0;
        const gastos = option.dataset.gastos || 0;
        const deudas = option.dataset.deudas || 0;

        const ingresosInput = document.getElementById('sim_ingresos');
        const gastosInput = document.getElementById('sim_gastos');
        const deudasInput = document.getElementById('sim_deudas');

        if (ingresosInput) {
            ingresosInput.value = ingresos;
            ingresosInput.dispatchEvent(new Event('input'));
        }
        if (gastosInput) {
            gastosInput.value = gastos;
            gastosInput.dispatchEvent(new Event('input'));
        }
        if (deudasInput) {
            deudasInput.value = deudas;
            deudasInput.dispatchEvent(new Event('input'));
        }
    });
}

function initTableSearch() {
    const searchInputs = document.querySelectorAll('.table-search-input');
    searchInputs.forEach(input => {
        input.addEventListener('keyup', function() {
            const tableId = this.dataset.targetTable;
            const table = document.getElementById(tableId);
            if (!table) return;

            const filter = this.value.toLowerCase();
            const rows = table.querySelectorAll('tbody tr');

            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(filter) ? '' : 'none';
            });
        });
    });
}


/**
 * CAJA INTELIGENTE - JavaScript de Interfaz & Gráficos Fintech
 * - Bank-ito Copilot Asistente de IA (Google Gemini)
 * - Control de Simulador de Crédito en Tiempo Real
 * - Gráficos Financieros Chart.js
 * - Búsqueda y Filtros Dinámicos
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

    // 6. Bank-ito Copilot Drawer Interactivo
    initBankitoCopilot();
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
                    backgroundColor: ['#059669', '#D97706', '#DC2626'],
                    hoverBackgroundColor: ['#047857', '#B45309', '#B91C1C'],
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
                            font: { family: 'Inter', size: 12, weight: 500 },
                            usePointStyle: true,
                            padding: 16,
                            color: '#475569'
                        }
                    },
                    tooltip: {
                        backgroundColor: '#0F172A',
                        padding: 10,
                        titleFont: { family: 'Inter', size: 12, weight: 600 },
                        bodyFont: { family: 'Inter', size: 12 },
                        cornerRadius: 6,
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const val = context.raw || 0;
                                const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
                                return ` ${context.label}: ${val} expedientes (${pct}%)`;
                            }
                        }
                    }
                },
                cutout: '74%'
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
                        borderRadius: 4,
                        order: 2,
                        barPercentage: 0.6
                    },
                    {
                        type: 'line',
                        label: 'Volumen Solicitado (S/.)',
                        data: [35000, 48000, 62000, 75000, 89000, 115000],
                        borderColor: '#D97706',
                        backgroundColor: 'rgba(217, 119, 6, 0.08)',
                        borderWidth: 2.5,
                        pointBackgroundColor: '#D97706',
                        pointBorderColor: '#FFFFFF',
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        fill: true,
                        tension: 0.25,
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
                            font: { family: 'Inter', size: 12, weight: 500 },
                            usePointStyle: true,
                            padding: 14,
                            color: '#475569'
                        }
                    },
                    tooltip: {
                        backgroundColor: '#0F172A',
                        padding: 10,
                        titleFont: { family: 'Inter', size: 12, weight: 600 },
                        bodyFont: { family: 'Inter', size: 12 },
                        cornerRadius: 6,
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
                            font: { family: 'Inter', size: 11 },
                            color: '#64748B',
                            callback: function(val) {
                                return 'S/. ' + (val / 1000) + 'k';
                            }
                        }
                    },
                    x: {
                        grid: { display: false },
                        ticks: {
                            font: { family: 'Inter', size: 11 },
                            color: '#64748B'
                        }
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
                        semaforoEl.className = 'badge-risk badge-risk-low';
                        semaforoEl.textContent = '● Viabilidad Alta';
                    } else if (data.semaforo === 'AMARILLO') {
                        semaforoEl.className = 'badge-risk badge-risk-medium';
                        semaforoEl.textContent = '● Viabilidad Media';
                    } else {
                        semaforoEl.className = 'badge-risk badge-risk-high';
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

function initBankitoCopilot() {
    const openBtn = document.getElementById('openBankitoBtn');
    const closeBtn = document.getElementById('closeBankitoBtn');
    const drawer = document.getElementById('bankitoDrawer');
    const overlay = document.getElementById('bankitoOverlay');
    const form = document.getElementById('bankitoForm');
    const input = document.getElementById('bankitoInput');
    const body = document.getElementById('bankitoBody');
    const sendBtn = document.getElementById('bankitoSendBtn');

    if (!drawer) return;

    const openDrawer = () => {
        drawer.classList.add('open');
        if (overlay) overlay.classList.add('active');
        if (input) input.focus();
    };

    const closeDrawer = () => {
        drawer.classList.remove('open');
        if (overlay) overlay.classList.remove('active');
    };

    if (openBtn) openBtn.addEventListener('click', openDrawer);
    if (closeBtn) closeBtn.addEventListener('click', closeDrawer);
    if (overlay) overlay.addEventListener('click', closeDrawer);

    // Event delegation para chips de consulta rápida
    if (body) {
        body.addEventListener('click', (e) => {
            const chip = e.target.closest('.bankito-chip-btn');
            if (chip && chip.dataset.prompt) {
                enviarPregunta(chip.dataset.prompt);
            }
        });
    }

    if (form) {
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const texto = input.value.trim();
            if (texto) {
                enviarPregunta(texto);
                input.value = '';
            }
        });
    }

    function enviarPregunta(pregunta) {
        // Mensaje de usuario
        const userMsg = document.createElement('div');
        userMsg.className = 'bankito-msg bankito-msg-user';
        userMsg.textContent = pregunta;
        body.appendChild(userMsg);

        // Indicador de cargando
        const loadingMsg = document.createElement('div');
        loadingMsg.className = 'bankito-msg bankito-msg-ai';
        loadingMsg.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2 text-primary"></i>Bank-ito analizando consulta...';
        body.appendChild(loadingMsg);
        body.scrollTop = body.scrollHeight;

        if (sendBtn) sendBtn.disabled = true;

        fetch('/riesgos/bank-ito/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mensaje: pregunta })
        })
        .then(res => res.json())
        .then(data => {
            loadingMsg.remove();
            const aiMsg = document.createElement('div');
            aiMsg.className = 'bankito-msg bankito-msg-ai';
            
            // Formatear viñetas básicas o texto
            let formatted = data.respuesta || 'No se pudo obtener respuesta de Bank-ito.';
            formatted = formatted.replace(/\n/g, '<br>');
            formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            
            aiMsg.innerHTML = `<div class="fw-semibold text-primary mb-1"><i class="fa-solid fa-robot me-1"></i>Bank-ito Copilot</div>${formatted}`;
            body.appendChild(aiMsg);
            body.scrollTop = body.scrollHeight;
        })
        .catch(err => {
            loadingMsg.remove();
            const errEl = document.createElement('div');
            errEl.className = 'bankito-msg bankito-msg-ai text-danger';
            errEl.innerHTML = '<i class="fa-solid fa-circle-exclamation me-1"></i>Error al consultar Bank-ito.';
            body.appendChild(errEl);
        })
        .finally(() => {
            if (sendBtn) sendBtn.disabled = false;
        });
    }
}

/**
 * HealthBite Admin — Analytics Dashboard Logic
 *
 * STATE:
 *   let dateFrom = '', dateTo = '', activePreset = '30d'
 *   let salesChart = null, revenuePieChart = null
 *   let popularFoodsChart = null, diseaseChart = null
 *   let riskTrendChart = null, peakHoursChart = null
 */

let dateFrom = '', dateTo = '', activePreset = '30d';
let salesChart = null, revenuePieChart = null;
let popularFoodsChart = null, peakHoursChart = null;

// ═══════════════════════════════════════
// Chart.js Global Defaults
// ═══════════════════════════════════════
Chart.defaults.color = '#738A76';
Chart.defaults.font.family = 'Plus Jakarta Sans, sans-serif';
Chart.defaults.font.size = 11;
Chart.defaults.plugins.tooltip.backgroundColor = '#1B261D';
Chart.defaults.plugins.tooltip.borderColor = 'rgba(255,255,255,0.1)';
Chart.defaults.plugins.tooltip.borderWidth = 1;
Chart.defaults.plugins.tooltip.padding = 10;
Chart.defaults.plugins.tooltip.cornerRadius = 8;
Chart.defaults.plugins.legend.labels.padding = 16;
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.scale = Chart.defaults.scale || {};

// ═══════════════════════════════════════
// Center Text Doughnut Plugin
// ═══════════════════════════════════════
const centerTextPlugin = {
    id: 'centerText',
    afterDraw(chart) {
        if (!chart.config.options.plugins?.centerText) return;
        const { value, label } = chart.config.options.plugins.centerText;
        const { ctx, chartArea: { left, right, top, bottom } } = chart;
        const cx = (left + right) / 2;
        const cy = (top + bottom) / 2;
        const isDark = document.documentElement.classList.contains('dark');

        ctx.save();
        ctx.textAlign = 'center';
        ctx.fillStyle = isDark ? '#F3F4F6' : '#1B261D';
        ctx.font = 'bold 22px "Plus Jakarta Sans"';
        ctx.fillText(value, cx, cy - 4);
        ctx.font = '600 10px "Plus Jakarta Sans"';
        ctx.fillStyle = isDark ? '#9CA3AF' : '#738A76';
        ctx.fillText(label, cx, cy + 14);
        ctx.restore();
    }
};
Chart.register(centerTextPlugin);

document.addEventListener('DOMContentLoaded', () => { init(); });

async function init() {
    setPresetRange('30d');

    await Promise.all([
        loadKpiSummary(),
        loadSalesChart('30d'),
        loadRevenuePieChart(),
        loadPopularFoodsChart(),
        loadPeakHoursChart(),
        loadTopSpenders()
    ]);

    // Preset pill listeners
    document.querySelectorAll('#presetPills button').forEach(btn => {
        btn.addEventListener('click', () => {
            const preset = btn.dataset.preset;
            if (preset === 'custom') {
                document.getElementById('customDateInputs').classList.remove('hidden');
                document.getElementById('customDateInputs').classList.add('flex');
            } else {
                document.getElementById('customDateInputs').classList.add('hidden');
                setPresetRange(preset);
            }
            // Update active pill
            document.querySelectorAll('#presetPills button').forEach(b => { b.classList.remove('active'); b.classList.add('bg-white/50', 'text-text-muted'); });
            btn.classList.add('active'); btn.classList.remove('bg-white/50', 'text-text-muted');
            activePreset = preset;
        });
    });
}

// ═══════════════════════════════════════
// buildDateParams()
// ═══════════════════════════════════════
function buildDateParams() {
    return `?from=${dateFrom}&to=${dateTo}`;
}

// ═══════════════════════════════════════
// setPresetRange(preset)
// ═══════════════════════════════════════
function setPresetRange(preset) {
    const now = new Date();
    dateTo = now.toISOString().split('T')[0];
    if (preset === 'today') { dateFrom = dateTo; }
    else if (preset === '7d') { const d = new Date(now); d.setDate(d.getDate() - 7); dateFrom = d.toISOString().split('T')[0]; }
    else if (preset === '30d') { const d = new Date(now); d.setDate(d.getDate() - 30); dateFrom = d.toISOString().split('T')[0]; }
    else if (preset === '90d') { const d = new Date(now); d.setDate(d.getDate() - 90); dateFrom = d.toISOString().split('T')[0]; }
    const label = preset === 'today' ? 'today' : `last ${preset.replace('d', ' days')}`;
    document.getElementById('dateRangeLabel').textContent = `Showing data from ${label}`;
}

// ═══════════════════════════════════════
// applyFilters() — re-fetch all 10 sections
// ═══════════════════════════════════════
async function applyFilters() {
    if (activePreset === 'custom') {
        dateFrom = document.getElementById('dateFrom').value;
        dateTo = document.getElementById('dateTo').value;
        document.getElementById('dateRangeLabel').textContent = `Showing data from ${dateFrom} to ${dateTo}`;
    }
    await Promise.all([
        loadKpiSummary(), loadSalesChart('30d'), loadRevenuePieChart(),
        loadPopularFoodsChart(), loadPeakHoursChart(), loadTopSpenders()
    ]);
}

function destroyChart(instance) {
    if (instance) { instance.destroy(); return null; }
    return null;
}

// ═══════════════════════════════════════
// 1. loadKpiSummary()
// GET /api/admin/analytics/summary + buildDateParams()
// ═══════════════════════════════════════
async function loadKpiSummary() {
    let data = {
        revenue: { value: 0, change: 0 },
        orders: { value: 0, change: 0 },
        avg_order_value: { value: 0, change: 0 },
        new_users: { value: 0, change: 0 }
    };
    try {
        const response = await HealthBite.apiFetch(`/analytics/summary${buildDateParams()}`);
        data = response || data;
    } catch (e) {
        console.error('Failed to load KPI summary', e);
    }

    const set = (id, val, changeId, change) => {
        const el = document.getElementById(id);
        el.textContent = typeof val === 'number' && val > 999 ? '₹' + val.toLocaleString() : val;
        el.classList.remove('shimmer'); el.style.width = 'auto'; el.style.height = 'auto';
        document.getElementById(changeId).innerHTML = getChangeBadge(change);
    };

    set('kpiRevenue', data.revenue.value, 'kpiRevenueChange', data.revenue.change);
    set('kpiOrders', data.orders.value, 'kpiOrdersChange', data.orders.change);
    set('kpiAvg', '₹' + data.avg_order_value.value, 'kpiAvgChange', data.avg_order_value.change);
    const usersEl = document.getElementById('kpiUsers');
    usersEl.textContent = data.new_users.value; usersEl.classList.remove('shimmer'); usersEl.style.width = 'auto'; usersEl.style.height = 'auto';
    document.getElementById('kpiUsersChange').innerHTML = getChangeBadge(data.new_users.change);
}

function getChangeBadge(pct) {
    const isPositive = pct >= 0;
    return `<span class="inline-flex items-center gap-1 text-[11px] font-bold ${isPositive ? 'text-green-600' : 'text-red-600'}">
        <span class="material-symbols-outlined text-[14px]">${isPositive ? 'trending_up' : 'trending_down'}</span>
        ${isPositive ? '+' : ''}${pct.toFixed(1)}% vs prev period
    </span>`;
}

// ═══════════════════════════════════════
// 2. loadSalesChart(period)
// GET /api/admin/analytics/sales + params + &chart_period=
// ═══════════════════════════════════════
async function loadSalesChart(period) {
    salesChart = destroyChart(salesChart);

    let labels = [];
    let revenue = [];
    let orders = [];

    try {
        const urlParams = new URLSearchParams(buildDateParams().replace('?', ''));
        urlParams.set('period', period);
        const response = await HealthBite.apiFetch(`/analytics/sales?${urlParams.toString()}`);
        if (response && response.labels) {
            labels = response.labels;
            revenue = response.revenue;
            orders = response.orders;
        }
    } catch (e) {
        console.error('Failed to load sales chart', e);
    }

    const ctx = document.getElementById('salesChart').getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 0, 280);
    gradient.addColorStop(0, 'rgba(17, 212, 27, 0.15)');
    gradient.addColorStop(1, 'rgba(17, 212, 27, 0)');

    salesChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                { label: 'Revenue (₹)', data: revenue, borderColor: '#2E7D32', backgroundColor: gradient, fill: true, tension: 0.4, yAxisID: 'y', pointRadius: 3, pointHoverRadius: 6, borderWidth: 2 },
                { label: 'Orders', data: orders, borderColor: '#FB8C00', borderDash: [5, 3], fill: false, tension: 0.4, yAxisID: 'y1', pointRadius: 2, borderWidth: 2 }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { position: 'top' } },
            scales: {
                y: { position: 'left', beginAtZero: true, grid: { color: 'rgba(0,0,0,0.04)' }, ticks: { callback: v => '₹' + v.toLocaleString() } },
                y1: { position: 'right', beginAtZero: true, grid: { display: false }, ticks: { stepSize: 1, precision: 0 } },
                x: { grid: { display: false } }
            }
        }
    });
}

function switchSalesChartPeriod(btn, period) {
    document.querySelectorAll('#salesPeriodPills button').forEach(b => {
        b.classList.remove('bg-forest', 'text-white');
        b.classList.add('bg-white/50', 'text-text-muted');
    });
    btn.classList.add('bg-forest', 'text-white');
    btn.classList.remove('bg-white/50', 'text-text-muted');
    loadSalesChart(period);
}

// ═══════════════════════════════════════
// 3. loadRevenuePieChart()
// GET /api/admin/analytics/revenue-by-category + params
// ═══════════════════════════════════════
async function loadRevenuePieChart() {
    revenuePieChart = destroyChart(revenuePieChart);

    let categories = [];
    let values = [];

    try {
        const response = await HealthBite.apiFetch(`/analytics/revenue-by-category${buildDateParams()}`);
        if (response) {
            categories = response.labels;
            values = response.data;
        }
    } catch (e) {
        console.error('Failed to load revenue pie chart', e);
    }

    const total = values.reduce((a, b) => a + b, 0);
    // Expand colors if necessary
    const rawColors = ['#2E7D32', '#FB8C00', '#3B82F6', '#E53935', '#11d41b', '#8B5CF6', '#EC4899', '#F59E0B'];
    const colors = categories.map((_, i) => rawColors[i % rawColors.length]);

    const ctx = document.getElementById('revenuePieChart').getContext('2d');
    revenuePieChart = new Chart(ctx, {
        type: 'doughnut',
        data: { labels: categories, datasets: [{ data: values, backgroundColor: colors, borderWidth: 0, hoverOffset: 8 }] },
        options: {
            responsive: true, maintainAspectRatio: false, cutout: '65%',
            plugins: {
                legend: { display: false },
                centerText: { value: '₹' + (total / 1000).toFixed(1) + 'K', label: 'Total Revenue' }
            }
        }
    });

    // Custom legend
    document.getElementById('pieLegend').innerHTML = categories.map((c, i) =>
        `<div class="flex items-center justify-between text-xs">
            <div class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full" style="background:${colors[i]}"></span><span class="font-medium">${c}</span></div>
            <span class="font-bold">₹${(values[i] / 1000).toFixed(1)}K <span class="text-text-muted font-medium">(${((values[i] / total) * 100).toFixed(0)}%)</span></span>
        </div>`).join('');
}

// ═══════════════════════════════════════
// 4. loadPopularFoodsChart()
// GET /api/admin/analytics/popular-foods + params
// ═══════════════════════════════════════
async function loadPopularFoodsChart() {
    popularFoodsChart = destroyChart(popularFoodsChart);

    let foods = [];

    try {
        const response = await HealthBite.apiFetch(`/analytics/popular-foods${buildDateParams()}`);
        foods = response || [];
    } catch (e) {
        console.error('Failed to load popular foods chart', e);
    }

    const ctx = document.getElementById('popularFoodsChart').getContext('2d');
    popularFoodsChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: foods.map(f => f.name.length > 20 ? f.name.slice(0, 20) + '…' : f.name),
            datasets: [{ label: 'Orders', data: foods.map(f => f.orders), backgroundColor: 'rgba(46,125,50,0.7)', borderRadius: 4, barThickness: 22 }]
        },
        options: {
            indexAxis: 'y', responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { afterLabel: (ctx) => `Revenue: ₹${foods[ctx.dataIndex].revenue.toLocaleString()}` } }
            },
            scales: {
                x: { grid: { color: 'rgba(0,0,0,0.04)' } },
                y: { grid: { display: false } }
            }
        }
    });
}


// ═══════════════════════════════════════
// 8. loadPeakHoursChart()
// GET /api/admin/analytics/peak-hours + params
// ═══════════════════════════════════════
async function loadPeakHoursChart() {
    peakHoursChart = destroyChart(peakHoursChart);

    let counts = Array(24).fill(0);

    try {
        const response = await HealthBite.apiFetch(`/analytics/peak-hours${buildDateParams()}`);
        counts = response.data || Array(24).fill(0);
    } catch (e) {
        console.error('Failed to load peak hours map', e);
    }
    const peakIdx = detectPeakHour(counts);
    const colors = counts.map((_, i) => i === peakIdx ? '#FB8C00' : 'rgba(46,125,50,0.6)');

    const ctx = document.getElementById('peakHoursChart').getContext('2d');
    peakHoursChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: Array.from({ length: 24 }, (_, i) => `${i}:00`),
            datasets: [{ data: counts, backgroundColor: colors, borderRadius: 3, barPercentage: 0.85 }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { grid: { color: 'rgba(0,0,0,0.04)' }, beginAtZero: true },
                x: { grid: { display: false }, ticks: { maxRotation: 0, callback: (_, i) => i % 3 === 0 ? `${i}:00` : '' } }
            }
        }
    });

    const peakStart = peakIdx;
    const peakEnd = peakIdx + 1;
    document.getElementById('peakHourLabel').innerHTML = `🔥 Peak time: <span class="text-accent-orange">${peakStart}:00 – ${peakEnd}:00</span>`;
}

function detectPeakHour(counts) {
    return counts.indexOf(Math.max(...counts));
}

// ═══════════════════════════════════════
// 9. loadTopSpenders()
// GET /api/admin/analytics/top-spenders + params
// ═══════════════════════════════════════
async function loadTopSpenders() {
    let spenders = [];

    try {
        const response = await HealthBite.apiFetch(`/analytics/top-spenders${buildDateParams()}`);
        spenders = response || [];
    } catch (e) {
        console.error('Failed to load top spenders', e);
    }

    const gradients = ['from-green-400 to-emerald-600', 'from-blue-400 to-indigo-600', 'from-purple-400 to-fuchsia-600', 'from-amber-400 to-orange-600', 'from-rose-400 to-pink-600'];
    const rankColors = ['text-amber-500', 'text-gray-400', 'text-amber-700', 'text-text-muted', 'text-text-muted'];
    const rankIcons = ['🥇', '🥈', '🥉', '4', '5'];

    document.getElementById('topSpendersList').innerHTML = spenders.map((s, i) => {
        const grad = gradients[s.name.charCodeAt(0) % gradients.length];
        return `<div class="flex items-center gap-3 group">
            <span class="text-lg font-black ${rankColors[i]} w-6 text-center">${rankIcons[i]}</span>
            <div class="w-8 h-8 rounded-full bg-gradient-to-br ${grad} flex items-center justify-center text-white text-[10px] font-black">${s.name.split(' ').map(n => n[0]).join('')}</div>
            <div class="flex-1 min-w-0">
                <p class="text-sm font-bold text-text-main truncate">${s.name}</p>
                <p class="text-[10px] text-text-muted">${s.orders} orders</p>
            </div>
            <span class="text-sm font-bold text-forest">₹${(s.spent || s.total).toLocaleString()}</span>
            <a href="admin-users.html" class="opacity-0 group-hover:opacity-100 text-[10px] font-bold text-primary hover:underline transition-opacity">View →</a>
        </div>`;
    }).join('');
}


// ═══════════════════════════════════════
// exportAll()
// GET /api/admin/export/analytics + buildDateParams()
// ═══════════════════════════════════════
async function exportAll() {
    if (window.HealthBite) HealthBite.showToast('Generating PDF Report... please wait.', 'success');

    // Hide buttons temporarily during export
    const applyBtn = document.getElementById('applyBtn');
    let exportBtn = null;
    if (applyBtn) {
        exportBtn = applyBtn.nextElementSibling;
        applyBtn.style.display = 'none';
        if (exportBtn) exportBtn.style.display = 'none';
    }

    try {
        const element = document.getElementById('pdf-content');

        // html2pdf options for high quality landscape fit
        const opt = {
            margin: 10,
            filename: `Analytics_Export_${dateFrom}_to_${dateTo}.pdf`,
            image: { type: 'jpeg', quality: 0.98 },
            html2canvas: { scale: 2, useCORS: true, logging: false },
            jsPDF: { unit: 'mm', format: 'a4', orientation: 'landscape' }
        };

        // Generate and save
        await html2pdf().set(opt).from(element).save();

        if (window.HealthBite) HealthBite.showToast('PDF Exported Successfully!', 'success');
    } catch (e) {
        console.error('Export failed', e);
        if (window.HealthBite) HealthBite.showToast('Failed to export PDF', 'error');
    } finally {
        // Restore buttons
        if (applyBtn) applyBtn.style.display = '';
        if (exportBtn) exportBtn.style.display = '';
    }
}

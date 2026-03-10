let pollingInterval = null;
let currentFilters = {};
let currentPage = 1;
let featureChart = null;
let accuracyChart = null;

Chart.defaults.color = "#738A76";
Chart.defaults.font.family = "Plus Jakarta Sans, sans-serif";
Chart.defaults.font.size = 11;

document.addEventListener("DOMContentLoaded", () => {
    init().catch((e) => console.error("AI monitor init failed", e));
});

async function init() {
    await Promise.all([
        loadAiStatus(),
        loadFeatureImportanceChart(),
        loadAccuracyTrendChart(),
        loadRecommendationLogs(1, {}),
        loadTrainingHistory(),
    ]);

    document.getElementById("logSearch").addEventListener("input", filterLogs);
    document.getElementById("logRisk").addEventListener("change", filterLogs);
    document.getElementById("logAction").addEventListener("change", filterLogs);
    document.getElementById("logPeriod").addEventListener("change", filterLogs);

    document.getElementById("pageInput").addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            const next = parseInt(e.target.value, 10);
            if (!Number.isNaN(next) && next >= 1) goToPage(next);
        }
    });

    document.getElementById("retrainModal").addEventListener("click", (e) => {
        if (e.target === document.getElementById("retrainModal")) closeRetrainModal();
    });
}

async function loadAiStatus() {
    const fallback = {
        status: "Active",
        version: "1.0.0",
        last_trained: null,
        total_predictions: 0,
        metrics: { accuracy: 0, precision: 0, recall: 0, f1: 0 },
    };

    let data = fallback;
    try {
        const response = await HealthBite.apiFetch("/ai/status");
        data = response || fallback;
    } catch (e) {
        console.error("Failed to load AI status", e);
    }

    const metrics = data.metrics || {};
    const accuracy = Number(metrics.accuracy || 0);
    const precisionRaw = Number(metrics.precision || 0);
    const recallRaw = Number(metrics.recall || 0);
    const f1Raw = Number(metrics.f1 || 0);

    const precisionPct = precisionRaw <= 1 ? precisionRaw * 100 : precisionRaw;
    const recallPct = recallRaw <= 1 ? recallRaw * 100 : recallRaw;
    const f1Pct = f1Raw <= 1 ? f1Raw * 100 : f1Raw;

    updateStatusBar(
        data.status || "Active",
        data.version || "1.0.0",
        data.last_trained,
        Number(data.total_predictions || 0)
    );

    setMetric("metricAccuracy", `${accuracy.toFixed(2)}%`, "accBar", accuracy, getMetricColor(accuracy));
    setMetric("metricPrecision", precisionRaw.toFixed(4), "precBar", precisionPct, getMetricColor(precisionPct));
    setMetric("metricRecall", recallRaw.toFixed(4), "recBar", recallPct, getMetricColor(recallPct));
    setMetric("metricF1", f1Raw.toFixed(4), "f1Bar", f1Pct, getMetricColor(f1Pct));
}

function updateStatusBar(status, version, lastTrained, totalPred) {
    const normalized = String(status || "Active").toLowerCase();
    const dot = document.getElementById("statusDot");
    const label = document.getElementById("statusLabel");

    dot.className = "w-4 h-4 rounded-full";
    if (normalized === "retraining") {
        dot.classList.add("status-retraining");
        label.textContent = "Retraining...";
        label.className = "text-lg font-bold text-cyan-600";
    } else if (normalized === "degraded") {
        dot.classList.add("status-degraded");
        label.textContent = "Degraded";
        label.className = "text-lg font-bold text-accent-orange";
    } else {
        dot.classList.add("status-active");
        label.textContent = "Active";
        label.className = "text-lg font-bold text-forest";
    }

    document.getElementById("modelVersion").textContent = version;
    document.getElementById("versionPill").textContent = version;
    document.getElementById("lastTrained").textContent = lastTrained ? formatRelativeTime(lastTrained) : "Never";
    document.getElementById("totalPredictions").textContent = Number(totalPred || 0).toLocaleString();

    const btn = document.getElementById("retrainBtn");
    const busy = normalized === "retraining";
    btn.disabled = busy;
    btn.classList.toggle("opacity-50", busy);
    btn.classList.toggle("cursor-not-allowed", busy);
}

function setMetric(textId, text, barId, pct, color) {
    const textEl = document.getElementById(textId);
    textEl.textContent = text;
    textEl.classList.remove("shimmer");
    textEl.style.width = "auto";
    textEl.style.height = "auto";

    const bar = document.getElementById(barId);
    bar.style.background = color;
    bar.style.width = `${Math.max(0, Math.min(100, Number(pct || 0)))}%`;
}

function getMetricColor(pct) {
    const value = Number(pct || 0);
    if (value > 85) return "#2E7D32";
    if (value >= 60) return "#FB8C00";
    return "#E53935";
}

async function loadFeatureImportanceChart() {
    if (featureChart) {
        featureChart.destroy();
        featureChart = null;
    }

    let features = [];
    try {
        const response = await HealthBite.apiFetch("/ai/features");
        features = Array.isArray(response?.features) ? response.features : [];
    } catch (e) {
        console.error("Failed to load feature importance", e);
    }

    features = features
        .map((f) => ({
            name: f.name || "Unknown",
            importance: Number(f.importance || 0),
        }))
        .sort((a, b) => b.importance - a.importance);

    const ctx = document.getElementById("featureChart").getContext("2d");
    featureChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: features.map((f) => f.name),
            datasets: [
                {
                    data: features.map((f) => f.importance),
                    backgroundColor: features.map((_, i) => `rgba(46,125,50,${Math.max(0.2, 1 - i * 0.08)})`),
                    borderRadius: 4,
                    barThickness: 20,
                },
            ],
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { label: (ctx) => `Importance: ${ctx.raw}%` } },
            },
            scales: {
                x: { max: 100, ticks: { callback: (v) => `${v}%` } },
                y: { grid: { display: false } },
            },
        },
    });
}

async function loadAccuracyTrendChart() {
    if (accuracyChart) {
        accuracyChart.destroy();
        accuracyChart = null;
    }

    let dates = [];
    let accuracy = [];
    let notes = [];
    try {
        const response = await HealthBite.apiFetch("/ai/accuracy-history");
        dates = Array.isArray(response?.dates) ? response.dates : [];
        accuracy = Array.isArray(response?.accuracy) ? response.accuracy.map((x) => Number(x || 0)) : [];
        notes = Array.isArray(response?.notes) ? response.notes : [];
    } catch (e) {
        console.error("Failed to load accuracy history", e);
    }

    const ctx = document.getElementById("accuracyChart").getContext("2d");
    accuracyChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: dates,
            datasets: [
                {
                    label: "Accuracy",
                    data: accuracy,
                    borderColor: "#06b6d4",
                    backgroundColor: "rgba(6,182,212,0.1)",
                    fill: true,
                    tension: 0.4,
                    borderWidth: 2.5,
                    pointRadius: 4,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { afterLabel: (ctx) => `Notes: ${notes[ctx.dataIndex] || "-"}` } },
            },
            scales: {
                y: { min: 70, max: 100, ticks: { callback: (v) => `${v}%` } },
                x: { grid: { display: false } },
            },
        },
    });
}

async function loadRecommendationLogs(page, filters) {
    currentPage = page;
    currentFilters = filters;
    showLogSkeletons();

    let logs = [];
    let totalPages = 1;
    let totalRows = 0;
    try {
        const params = new URLSearchParams({ page: String(page), limit: "20" });
        if (filters.search) params.append("search", filters.search);
        if (filters.risk && filters.risk !== "all") params.append("risk", filters.risk);
        if (filters.action && filters.action !== "all") params.append("action", filters.action);
        if (filters.period && filters.period !== "all") params.append("period", filters.period);

        const response = await HealthBite.apiFetch(`/ai/logs?${params.toString()}`);
        logs = Array.isArray(response?.logs) ? response.logs : [];
        totalPages = Number(response?.pages || 1);
        totalRows = Number(response?.total || 0);
    } catch (e) {
        console.error("Failed to load recommendation logs", e);
    }

    renderLogRows(logs);
    updatePagination(page, totalPages, totalRows);
}

function showLogSkeletons() {
    const tbody = document.getElementById("logsTableBody");
    tbody.innerHTML = Array(4)
        .fill(0)
        .map(
            () => `
        <tr class="h-[52px] border-b border-black/5">
            <td class="px-4 py-2"><div class="shimmer h-4 w-28 rounded"></div></td>
            <td class="px-4 py-2"><div class="shimmer h-4 w-20 rounded"></div></td>
            <td class="px-4 py-2"><div class="shimmer h-5 w-16 rounded-full"></div></td>
            <td class="px-4 py-2"><div class="shimmer h-4 w-28 rounded"></div></td>
            <td class="px-4 py-2"><div class="shimmer h-4 w-36 rounded"></div></td>
            <td class="px-4 py-2"><div class="shimmer h-5 w-12 mx-auto rounded-full"></div></td>
            <td class="px-4 py-2"><div class="shimmer h-5 w-16 mx-auto rounded-full"></div></td>
            <td class="px-4 py-2"><div class="shimmer h-4 w-8 mx-auto rounded"></div></td>
        </tr>`
        )
        .join("");
}

function renderLogRows(logs) {
    const tbody = document.getElementById("logsTableBody");
    const empty = document.getElementById("logsEmptyState");

    if (!logs.length) {
        tbody.innerHTML = "";
        empty.classList.remove("hidden");
        empty.classList.add("flex");
        return;
    }
    empty.classList.add("hidden");
    empty.classList.remove("flex");

    tbody.innerHTML = logs
        .map((log) => {
            const riskBadge = getRiskBadge(log.user_risk || "Low");
            const confBadge = getConfidenceBadge(Number(log.confidence || 0));
            const actionBadge = getActionBadge(log.user_action || "No Response");
            const reason = String(log.reason || "");
            const trunc = reason.length > 48 ? `${reason.slice(0, 48)}...` : reason;

            return `<tr class="border-b border-black/5 hover:bg-white/40 transition-colors">
                <td class="px-4 py-2.5">
                    <p class="text-xs font-medium text-text-main">${formatDateTime(log.timestamp)}</p>
                    <p class="text-[10px] text-text-muted">${formatRelativeTime(log.timestamp)}</p>
                </td>
                <td class="px-4 py-2.5"><span class="text-sm font-medium text-text-main">${log.user_name || "-"}</span></td>
                <td class="px-4 py-2.5">${riskBadge}</td>
                <td class="px-4 py-2.5">
                    <span class="text-sm font-medium text-text-main">${log.food_name || "-"}</span>
                    <span class="ml-1 px-1.5 py-0.5 rounded text-[9px] font-bold bg-black/5 text-text-muted">${log.food_category || "-"}</span>
                </td>
                <td class="px-4 py-2.5"><span class="text-xs text-text-muted" title="${reason}">${trunc}</span></td>
                <td class="px-4 py-2.5 text-center">${confBadge}</td>
                <td class="px-4 py-2.5 text-center">${actionBadge}</td>
                <td class="px-4 py-2.5 text-center"><span class="text-sm font-bold text-text-main">${log.match_score || "-"}</span></td>
            </tr>`;
        })
        .join("");
}

function getRiskBadge(risk) {
    const map = {
        Low: "bg-green-100 text-green-700",
        Moderate: "bg-amber-100 text-amber-700",
        High: "bg-red-100 text-red-700",
    };
    const cls = map[risk] || map.Low;
    return `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${cls}">${risk}</span>`;
}

function getConfidenceBadge(pct) {
    let cls = "bg-green-100 text-green-700";
    if (pct < 60) cls = "bg-red-100 text-red-700";
    else if (pct < 85) cls = "bg-amber-100 text-amber-700";
    return `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${cls}">${pct.toFixed(1)}%</span>`;
}

function getActionBadge(action) {
    const map = {
        Accepted: "bg-green-100 text-green-700",
        Rejected: "bg-red-100 text-red-700",
        "No Response": "bg-black/5 text-text-muted",
    };
    const cls = map[action] || map["No Response"];
    return `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${cls}">${action}</span>`;
}

function updatePagination(page, totalPages, totalRows) {
    document.getElementById("pageInfo").textContent = `Page ${page} of ${totalPages} (${totalRows} logs)`;
    document.getElementById("pageInput").value = page;
    document.getElementById("prevPageBtn").disabled = page <= 1;
    document.getElementById("nextPageBtn").disabled = page >= totalPages;
}

async function loadTrainingHistory() {
    let history = [];
    try {
        const response = await HealthBite.apiFetch("/ai/training-history");
        history = Array.isArray(response?.history) ? response.history : [];
    } catch (e) {
        console.error("Failed to load training history", e);
    }

    const body = document.getElementById("historyTableBody");
    body.innerHTML = history
        .map((h) => {
            const statusBadge = getTrainStatusBadge(h.status || "In Progress");
            const before = Number(h.acc_before || 0);
            const after = Number(h.acc_after || 0);
            const diff = after - before;
            const color = diff > 0 ? "text-green-600" : diff < 0 ? "text-red-600" : "text-text-muted";
            return `<tr class="border-b border-black/5 hover:bg-white/40 transition-colors">
                <td class="px-4 py-3 text-sm text-text-muted">#${h.id}</td>
                <td class="px-4 py-3 text-sm font-medium text-text-main">${h.triggered_by || "-"}</td>
                <td class="px-4 py-3 text-sm text-text-muted">${h.date || "-"}</td>
                <td class="px-4 py-3 text-sm text-text-muted">${h.duration || "-"}</td>
                <td class="px-4 py-3 text-sm text-right">${before.toFixed(2)}%</td>
                <td class="px-4 py-3 text-sm text-right font-bold ${color}">${after.toFixed(2)}%</td>
                <td class="px-4 py-3 text-center">${statusBadge}</td>
                <td class="px-4 py-3 text-xs text-text-muted">${h.notes || ""}</td>
            </tr>`;
        })
        .join("");
}

function getTrainStatusBadge(status) {
    if (status === "Success") return `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-green-100 text-green-700">Success</span>`;
    if (status === "Failed") return `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-100 text-red-700">Failed</span>`;
    return `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-cyan-100 text-cyan-700 animate-pulse">In Progress</span>`;
}

function openRetrainModal() {
    const modal = document.getElementById("retrainModal");
    document.getElementById("retrainBtnText").textContent = "Start Retraining";
    document.getElementById("retrainSpinner").classList.add("hidden");
    document.getElementById("confirmRetrainBtn").disabled = false;
    modal.classList.remove("hidden");
    modal.classList.add("flex");
}

function closeRetrainModal() {
    const modal = document.getElementById("retrainModal");
    modal.classList.add("hidden");
    modal.classList.remove("flex");
}

async function confirmRetrain() {
    const btn = document.getElementById("confirmRetrainBtn");
    btn.disabled = true;
    document.getElementById("retrainBtnText").textContent = "Initiating...";
    document.getElementById("retrainSpinner").classList.remove("hidden");

    try {
        await HealthBite.apiFetch("/ai/retrain", { method: "POST" });
        closeRetrainModal();
        HealthBite.showToast("Model retraining initiated", "success");
        await loadAiStatus();
        startPolling();
    } catch (e) {
        HealthBite.showToast("Retraining failed. Please try again.", "error");
        btn.disabled = false;
        document.getElementById("retrainBtnText").textContent = "Start Retraining";
        document.getElementById("retrainSpinner").classList.add("hidden");
    }
}

function startPolling() {
    stopPolling();
    pollingInterval = setInterval(pollStatus, 10000);
}

async function pollStatus() {
    try {
        const response = await HealthBite.apiFetch("/ai/status");
        const status = String(response?.status || "").toLowerCase();
        await loadAiStatus();
        if (status !== "retraining") {
            stopPolling();
            await Promise.all([loadTrainingHistory(), loadAccuracyTrendChart()]);
            HealthBite.showToast("Retraining completed and metrics updated.", "success");
        }
    } catch (e) {
        console.error("Polling for AI status failed", e);
    }
}

function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

function filterLogs() {
    const filters = {
        search: document.getElementById("logSearch").value.trim(),
        risk: document.getElementById("logRisk").value,
        action: document.getElementById("logAction").value,
        period: document.getElementById("logPeriod").value,
    };
    loadRecommendationLogs(1, filters);
}

function goToPage(pageNum) {
    if (pageNum < 1) return;
    loadRecommendationLogs(pageNum, currentFilters);
}

function formatRelativeTime(isoString) {
    if (!isoString) return "-";
    const now = new Date();
    const past = new Date(isoString);
    const diffMin = Math.floor((now - past) / 60000);
    const diffHr = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHr / 24);
    if (diffMin < 1) return "Just now";
    if (diffMin < 60) return `${diffMin} min${diffMin > 1 ? "s" : ""} ago`;
    if (diffHr < 24) return `${diffHr} hr${diffHr > 1 ? "s" : ""} ago`;
    if (diffDay === 1) return "Yesterday";
    return `${diffDay} days ago`;
}

function formatDateTime(isoString) {
    if (!isoString) return "-";
    const d = new Date(isoString);
    return `${d.toLocaleDateString("en-IN", { day: "numeric", month: "short" })}, ${d.toLocaleTimeString("en-IN", {
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
    })}`;
}

window.openRetrainModal = openRetrainModal;
window.closeRetrainModal = closeRetrainModal;
window.confirmRetrain = confirmRetrain;
window.goToPage = goToPage;

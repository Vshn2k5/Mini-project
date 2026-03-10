/**
 * HealthBite Admin — Users Management Logic
 */

let usersData = [];
let currentAdminRole = '';

document.addEventListener('DOMContentLoaded', () => { init(); });

async function init() {
    await loadUsers();
    attachListeners();
}

function attachListeners() {
    const searchInput = document.getElementById('searchInput');
    const filterRole = document.getElementById('filterRole');
    const filterStatus = document.getElementById('filterStatus');

    console.log('DEBUG: Attaching listeners to:', { searchInput, filterRole, filterStatus });

    if (searchInput) searchInput.addEventListener('input', filterUsers);
    if (filterRole) filterRole.addEventListener('change', filterUsers);
    if (filterStatus) filterStatus.addEventListener('change', filterUsers);

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') { closeHealthModal(); closeRoleModal(); closeAllPopovers(); }
    });

    document.addEventListener('click', (e) => {
        if (!e.target.closest('.deactivate-popover') && !e.target.closest('.deactivate-trigger')) closeAllPopovers();
    });
}

async function loadUsers() {
    console.log('DEBUG: Starting loadUsers');
    showSkeletonRows();

    try {
        const response = await HealthBite.apiFetch('/users');
        console.log('DEBUG: loadUsers API response:', response);
        usersData = response.items || [];
        console.log('DEBUG: usersData loaded:', usersData.length, 'users');

        updateSummaryStrip();
        renderTable(usersData);
        updateResultsCount(usersData.length, usersData.length);
    } catch (e) {
        console.error('CRITICAL: Failed to load users:', e);
        const tbody = document.getElementById('usersTableBody');
        if (tbody) tbody.innerHTML = `<tr><td colspan="5" class="py-10 text-center text-red-500 font-bold">Failed to load users: ${e.message}</td></tr>`;
        if (window.HealthBite) HealthBite.showToast('Failed to load users: ' + e.message, 'error');
    }
}

function showSkeletonRows() {
    const tbody = document.getElementById('usersTableBody');
    if (!tbody) return;
    tbody.innerHTML = Array(6).fill(0).map(() => `
        <tr class="h-[60px] border-b border-black/5">
            <td class="px-4 py-3"><div class="shimmer w-10 h-10 rounded-full"></div></td>
            <td class="px-4 py-3"><div class="shimmer h-4 w-32 rounded mb-1"></div><div class="shimmer h-3 w-24 rounded"></div></td>
            <td class="px-4 py-3"><div class="shimmer h-5 w-16 rounded-full"></div></td>
            <td class="px-4 py-3"><div class="shimmer h-4 w-20 rounded"></div></td>
            <td class="px-4 py-3"><div class="shimmer h-6 w-24 mx-auto rounded"></div></td>
        </tr>`).join('');
}

function renderTable(users) {
    const tbody = document.getElementById('usersTableBody');
    const emptyState = document.getElementById('emptyState');
    if (!tbody || !emptyState) return;

    if (users.length === 0) {
        tbody.innerHTML = '';
        emptyState.classList.remove('hidden');
        emptyState.classList.add('flex');
        return;
    }

    emptyState.classList.add('hidden');
    emptyState.classList.remove('flex');
    tbody.innerHTML = users.map(u => buildUserRow(u)).join('');
}

function buildUserRow(user) {
    const isDeactivated = user.disabled === 1;
    const rowOpacity = isDeactivated ? 'opacity-[0.65]' : '';
    const nameStrike = isDeactivated ? 'line-through' : '';
    const grad = getAvatarGradient(user.name || 'User');

    return `
    <tr class="group hover:bg-white/40 transition-colors border-b border-black/5 ${rowOpacity}" id="user-row-${user.id}">
        <td class="px-4 py-3">
            <div class="w-10 h-10 rounded-full bg-gradient-to-br ${grad} flex items-center justify-center text-white text-xs font-black shrink-0">${(user.name || 'U').split(' ').map(n => n[0]).join('')}</div>
        </td>
        <td class="px-4 py-3">
            <p class="text-sm font-bold text-text-main ${nameStrike}">${user.name || 'Unnamed'}</p>
            <p class="text-[10px] text-text-muted">${user.email}</p>
        </td>
        <td class="px-4 py-3">${getRoleBadge(user.role)}</td>
        <td class="px-4 py-3 text-sm text-text-muted">${user.joined_at ? formatDate(user.joined_at) : 'N/A'}</td>
        <td class="px-4 py-3 text-center actions-col">
            <div class="flex items-center justify-center gap-1">
                <button onclick="openHealthModal(${user.id})" class="p-1.5 rounded-lg text-text-muted hover:text-blue-600 hover:bg-blue-50 transition-all" title="View Health Summary">
                    <span class="material-symbols-outlined text-[18px]">visibility</span>
                </button>
                <button onclick="openRoleModal(${user.id})" class="p-1.5 rounded-lg text-text-muted hover:text-purple-600 hover:bg-purple-50 transition-all" title="Change Role">
                    <span class="material-symbols-outlined text-[18px]">key</span>
                </button>
                <div class="relative">
                    <button class="deactivate-trigger p-1.5 rounded-lg text-text-muted hover:${isDeactivated ? 'text-green-600 hover:bg-green-50' : 'text-danger-red hover:bg-red-50'} transition-all" title="${isDeactivated ? 'Reactivate' : 'Deactivate'}" onclick="openDeactivatePopover(${user.id}, '${isDeactivated ? 'Deactivated' : 'Active'}', this)">
                        <span class="material-symbols-outlined text-[18px]">${isDeactivated ? 'check_circle' : 'block'}</span>
                    </button>
                </div>
            </div>
        </td>
    </tr>`;
}

function getAvatarGradient(name) {
    const gradients = ['from-green-400 to-emerald-600', 'from-blue-400 to-indigo-600', 'from-purple-400 to-fuchsia-600', 'from-amber-400 to-orange-600', 'from-rose-400 to-pink-600'];
    return gradients[name.charCodeAt(0) % gradients.length];
}

function getRoleBadge(role) {
    const map = {
        'ADMIN': 'bg-primary/10 text-primary border-primary/20',
        'USER': 'bg-black/5 text-text-muted border-black/10'
    };
    return `<span class="inline-flex px-2 py-0.5 rounded-full text-[10px] font-bold border ${map[role] || map['USER']}">${role}</span>`;
}

function getStatusBadge(status) {
    if (status === 'Active') return `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-green-100 text-green-700"><span class="w-1.5 h-1.5 rounded-full bg-green-600"></span>Active</span>`;
    return `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-100 text-red-700"><span class="w-1.5 h-1.5 rounded-full bg-red-600"></span>Deactivated</span>`;
}

function updateSummaryStrip() {
    const s = {
        total: usersData.length,
        active: usersData.filter(u => u.disabled === 0).length,
        deactivated: usersData.filter(u => u.disabled === 1).length
    };

    const pairs = [['summaryTotal', s.total], ['summaryActive', s.active], ['summaryDeactivated', s.deactivated]];
    pairs.forEach(([id, val]) => {
        const el = document.getElementById(id);
        if (el) {
            el.textContent = val;
            el.classList.remove('shimmer');
            el.style.width = 'auto';
            el.style.height = 'auto';
        }
    });
}

function openHealthModal(userId) {
    const user = usersData.find(u => u.id === userId);
    if (!user) return;

    const riskLevel = user.risk_level || 'Unknown';
    const riskScore = user.risk_score || 0;
    const riskColor = riskLevel === 'High' ? '#E53935' : riskLevel === 'Moderate' ? '#FB8C00' : '#2E7D32';
    const circumference = 2 * Math.PI * 54;
    const offset = circumference - (riskScore / 100) * circumference;
    const grad = getAvatarGradient(user.name || 'U');

    const modalBody = document.getElementById('healthModalBody');
    if (!modalBody) return;

    modalBody.innerHTML = `
        <div class="p-6 border-b border-black/5 flex items-center gap-4">
            <div class="w-14 h-14 rounded-full bg-gradient-to-br ${grad} flex items-center justify-center text-white text-lg font-black shrink-0">${(user.name || 'U').split(' ').map(n => n[0]).join('')}</div>
            <div class="flex-1">
                <h3 class="text-lg font-bold text-text-main">${user.name || 'Unnamed'}</h3>
                <p class="text-sm text-text-muted">${user.email}</p>
            </div>
            <div class="flex gap-2">${getRoleBadge(user.role)} ${getStatusBadge(user.disabled === 1 ? 'Deactivated' : 'Active')}</div>
        </div>

        <div class="p-6 space-y-6">
            <div class="text-center">
                <div class="relative inline-block">
                    <svg width="130" height="130" viewBox="0 0 130 130">
                        <circle cx="65" cy="65" r="54" fill="none" stroke="rgba(0,0,0,0.05)" stroke-width="8"/>
                        <circle class="risk-ring" cx="65" cy="65" r="54" fill="none" stroke="${riskColor}" stroke-width="8" stroke-linecap="round"
                            stroke-dasharray="${circumference}" stroke-dashoffset="${circumference}" transform="rotate(-90 65 65)"
                            style="transition: stroke-dashoffset 1s ease-out;"
                            id="riskRingCircle"/>
                    </svg>
                    <div class="absolute inset-0 flex flex-col items-center justify-center">
                        <span class="text-3xl font-black" style="color:${riskColor}">${riskScore}</span>
                        <span class="text-[9px] font-bold text-text-muted uppercase">Risk Score</span>
                    </div>
                </div>
                <p class="text-sm font-bold mt-2" style="color:${riskColor}">${riskLevel} Risk Profile</p>
            </div>

            <div>
                <h4 class="text-xs font-bold uppercase text-text-muted tracking-wider mb-2">Reported Conditions</h4>
                <div class="flex flex-wrap gap-2">
                    ${user.conditions && user.conditions.length > 0 && user.conditions[0] !== 'None' ? user.conditions.map(c => `<span class="px-3 py-1 rounded-full text-xs font-bold bg-red-50 text-red-700 border border-red-200">${c}</span>`).join('') : '<span class="text-sm text-text-muted">None reported</span>'}
                </div>
            </div>

            <div>
                <h4 class="text-xs font-bold uppercase text-text-muted tracking-wider mb-2">Dietary Preferences</h4>
                <div class="flex flex-wrap gap-2">
                    ${user.dietary_preferences && user.dietary_preferences.length > 0 ? user.dietary_preferences.map(d => `<span class="px-3 py-1 rounded-full text-xs font-bold bg-green-50 text-green-700 border border-green-200">${d}</span>`).join('') : '<span class="text-sm text-text-muted">No preferences set</span>'}
                </div>
            </div>

            <div>
                <h4 class="text-xs font-bold uppercase text-text-muted tracking-wider mb-3">Order Summary</h4>
                <div class="grid grid-cols-3 gap-4">
                    <div class="bg-white/50 p-3 rounded-xl text-center">
                        <p class="text-2xl font-bold text-text-main">${user.order_stats ? user.order_stats.total_orders : 0}</p>
                        <p class="text-[10px] text-text-muted font-bold">Total Orders</p>
                    </div>
                    <div class="bg-white/50 p-3 rounded-xl text-center">
                        <p class="text-2xl font-bold text-forest">₹${user.order_stats ? user.order_stats.total_spent.toLocaleString() : 0}</p>
                        <p class="text-[10px] text-text-muted font-bold">Total Spent</p>
                    </div>
                    <div class="bg-white/50 p-3 rounded-xl text-center">
                        <p class="text-2xl font-bold text-text-main">₹${user.order_stats ? user.order_stats.avg_order_value : 0}</p>
                        <p class="text-[10px] text-text-muted font-bold">Avg Value</p>
                    </div>
                </div>
            </div>

            <div>
                <h4 class="text-xs font-bold uppercase text-text-muted tracking-wider mb-3">AI Insights</h4>
                <div class="space-y-2.5">
                    <p class="text-sm"><span class="font-bold">Most recommended:</span> ${user.ai_insights ? user.ai_insights.top_category : 'N/A'}</p>
                    <p class="text-sm"><span class="font-bold">Flagged items:</span> ${user.ai_insights ? user.ai_insights.flagged_items : 'N/A'}</p>
                    <div class="flex items-center gap-3">
                        <span class="text-sm font-bold">Compliance:</span>
                        <div class="flex-1 h-2 bg-black/5 rounded-full overflow-hidden">
                            <div class="h-full bg-primary rounded-full" style="width:${user.ai_insights ? user.ai_insights.compliance_rate : 0}%"></div>
                        </div>
                        <span class="text-sm font-bold">${user.ai_insights ? user.ai_insights.compliance_rate : 0}%</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="p-6 border-t border-black/5 flex justify-between items-center">
            <button onclick="closeHealthModal()" class="px-5 py-2.5 text-sm font-bold text-text-muted rounded-xl hover:bg-black/5 transition-colors">Close</button>
            <a href="admin-orders.html?user_id=${user.id}" class="text-sm font-bold text-primary hover:underline">View Order History →</a>
        </div>`;

    const modal = document.getElementById('healthModal');
    if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
    }

    requestAnimationFrame(() => {
        const ring = document.getElementById('riskRingCircle');
        if (ring) ring.style.strokeDashoffset = offset;
    });
}

function closeHealthModal() {
    const modal = document.getElementById('healthModal');
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }
}

function openRoleModal(userId) {
    const user = usersData.find(u => u.id === userId);
    if (!user) return;

    selectedUserId = userId;

    const modalBody = document.getElementById('roleModalBody');
    if (!modalBody) return;

    modalBody.innerHTML = `
        <h3 class="text-lg font-bold text-text-main mb-1">Change Role</h3>
        <p class="text-sm text-text-muted mb-5">${user.name || 'User'} — Current: <span class="font-bold">${user.role}</span></p>

        <div class="space-y-2 mb-4">
            <button onclick="updateUserRole(${userId}, 'USER')" class="w-full text-left p-3.5 rounded-xl border-2 border-transparent hover:border-primary/20 hover:bg-white/50 transition-all">
                <span class="text-sm font-bold text-text-main">USER</span>
                <p class="text-xs text-text-muted mt-0.5">Standard user access</p>
            </button>
            <button onclick="updateUserRole(${userId}, 'ADMIN')" class="w-full text-left p-3.5 rounded-xl border-2 border-transparent hover:border-primary/20 hover:bg-white/50 transition-all">
                <span class="text-sm font-bold text-text-main">ADMIN</span>
                <p class="text-xs text-text-muted mt-0.5">Full system control</p>
            </button>
        </div>
        <div class="flex justify-end">
            <button onclick="closeRoleModal()" class="px-5 py-2.5 text-sm font-bold text-text-muted rounded-xl hover:bg-black/5 transition-colors">Cancel</button>
        </div>`;

    const modal = document.getElementById('roleModal');
    if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
    }
}

async function updateUserRole(userId, newRole) {
    try {
        await HealthBite.apiFetch(`/users/${userId}`, {
            method: 'PUT',
            body: JSON.stringify({ role: newRole })
        });

        const user = usersData.find(u => u.id === userId);
        if (user) user.role = newRole;

        closeRoleModal();
        renderTable(usersData);
        if (window.HealthBite) HealthBite.showToast(`Role updated to ${newRole}`, 'success');
    } catch (e) {
        if (window.HealthBite) HealthBite.showToast('Failed to update role', 'error');
    }
}

function closeRoleModal() {
    const modal = document.getElementById('roleModal');
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }
}

function openDeactivatePopover(userId, currentStatus, anchorEl) {
    closeAllPopovers();
    const isActive = currentStatus === 'Active';

    const popover = document.createElement('div');
    popover.className = 'deactivate-popover fixed bg-white rounded-xl shadow-2xl border border-black/10 p-4 w-60 z-[100] transform transition-all animate-in fade-in zoom-in duration-200';

    const rect = anchorEl.getBoundingClientRect();
    popover.style.top = `${rect.bottom + window.scrollY + 8}px`;
    popover.style.left = `${rect.right + window.scrollX - 240}px`;

    popover.innerHTML = `
        <h4 class="text-sm font-bold text-text-main mb-1">${isActive ? 'Deactivate User?' : 'Reactivate User?'}</h4>
        <p class="text-[11px] text-text-muted mb-4">${isActive ? 'Restrict system access.' : 'Restore system access.'}</p>
        <div class="flex items-center justify-between gap-3">
            <button onclick="confirmDeactivation(${userId}, ${!isActive})" class="flex-1 px-3 py-2 text-[11px] font-black text-white rounded-lg ${isActive ? 'bg-danger-red' : 'bg-forest'} transition-all active:scale-95">
                ${isActive ? 'Deactivate' : 'Reactivate'}
            </button>
            <button onclick="closeAllPopovers()" class="px-3 py-2 text-[11px] font-bold text-text-muted hover:bg-black/5 rounded-lg transition-colors">Cancel</button>
        </div>`;

    document.body.appendChild(popover);
}

async function confirmDeactivation(userId, makeActive) {
    closeAllPopovers();
    try {
        const newStatus = makeActive ? 'Active' : 'Deactivated';
        await HealthBite.apiFetch(`/users/${userId}`, {
            method: 'PUT',
            body: JSON.stringify({ status: newStatus })
        });

        const user = usersData.find(u => u.id === userId);
        if (user) {
            user.disabled = makeActive ? 0 : 1;
            filterUsers();
            updateSummaryStrip();
            if (window.HealthBite) HealthBite.showToast(`${user.name} is now ${newStatus}`, 'success');
        }
    } catch (e) {
        if (window.HealthBite) HealthBite.showToast('Failed to update status', 'error');
    }
}

function closeAllPopovers() {
    document.querySelectorAll('.deactivate-popover').forEach(p => p.remove());
}

function filterUsers() {
    const search = (document.getElementById('searchInput')?.value || '').toLowerCase().trim();
    const role = document.getElementById('filterRole')?.value || 'all';
    const status = document.getElementById('filterStatus')?.value || 'all';

    const filtered = usersData.filter(u => {
        const matchSearch = String(u.name || '').toLowerCase().includes(search) || String(u.email || '').toLowerCase().includes(search);
        const matchRole = role === 'all' || u.role === role;
        const matchStatus = status === 'all' || (status === 'Active' ? u.disabled === 0 : u.disabled === 1);
        return matchSearch && matchRole && matchStatus;
    });

    renderTable(filtered);
    updateResultsCount(filtered.length, usersData.length);
}

function updateResultsCount(showing, total) {
    const el = document.getElementById('resultsCount');
    if (el) el.textContent = `Showing ${showing} of ${total} users`;
}

function formatDate(dateStr) {
    try {
        return new Date(dateStr).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
    } catch (e) {
        return 'N/A';
    }
}

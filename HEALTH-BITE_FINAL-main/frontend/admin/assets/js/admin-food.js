/**
 * HealthBite Admin — Food Management Logic
 * 
 * STATE:
 *   foodsData[]  — full array from API
 *   editingId    — null for add mode, item.id for edit mode
 *   deletingId   — id of item being deleted
 *   isSubmitting — double-submit prevention flag
 */

let foodsData = [];
let editingId = null;
let deletingId = null;
let isSubmitting = false;

document.addEventListener('DOMContentLoaded', () => {
    init();
});

async function init() {
    // Base systems handled by layout.js

    await loadFoods();
    attachListeners();
}

function attachListeners() {
    // Search
    document.getElementById('searchInput').addEventListener('input', filterTable);

    // Dropdowns
    document.getElementById('filterDietType').addEventListener('change', filterTable);
    document.getElementById('filterCategory').addEventListener('change', filterTable);
    document.getElementById('filterStatus').addEventListener('change', filterTable);

    // Add button
    document.getElementById('addFoodBtn').addEventListener('click', openAddModal);

    // Image preview
    document.getElementById('fieldImageUrl').addEventListener('input', (e) => imagePreview(e.target.value));

    // Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeModal();
            closeDeleteModal();
        }
    });
}

// ═══════════════════════════════════════
// DATA LOADING
// ═══════════════════════════════════════

// GET /api/admin/foods
async function loadFoods() {
    showSkeletonRows();

    try {
        const response = await fetchAllFoods();
        foodsData = response.items || [];
        console.log('Foods loaded:', foodsData.length, 'items');
    } catch (e) {
        console.error('Failed to load foods:', e);
        foodsData = [];
        if (window.HealthBite) HealthBite.showToast('Failed to load foods: ' + e.message, 'error');
    }

    renderTable(foodsData);
    updateResultsCount(foodsData.length, foodsData.length);
}

async function fetchAllFoods() {
    const perPage = 100; // backend max
    const first = await HealthBite.apiFetch(`/foods/?page=1&per_page=${perPage}`);
    const base = first || { items: [], pages: 1, total: 0 };
    let allItems = [...(base.items || [])];
    const totalPages = Math.max(1, Number(base.pages || 1));

    for (let page = 2; page <= totalPages; page++) {
        const next = await HealthBite.apiFetch(`/foods/?page=${page}&per_page=${perPage}`);
        if (next?.items?.length) allItems = allItems.concat(next.items);
    }

    return { ...base, items: allItems, total: Number(base.total || allItems.length) };
}

function showSkeletonRows() {
    const tbody = document.getElementById('foodTableBody');
    let html = '';
    for (let i = 0; i < 6; i++) {
        html += `<tr class="h-[72px]">
            <td class="px-6 py-3"><div class="w-10 h-10 rounded-lg shimmer"></div></td>
            <td class="px-6 py-3"><div class="space-y-2"><div class="h-4 w-32 shimmer rounded-md"></div><div class="h-3 w-16 shimmer rounded-md"></div></div></td>
            <td class="px-6 py-3"><div class="h-6 w-20 shimmer rounded-full"></div></td>
            <td class="px-6 py-3"><div class="h-4 w-12 shimmer rounded-md"></div></td>
            <td class="px-6 py-3"><div class="h-4 w-12 shimmer rounded-md"></div></td>
            <td class="px-6 py-3"><div class="h-4 w-12 shimmer rounded-md"></div></td>
            <td class="px-6 py-3"><div class="h-6 w-24 shimmer rounded-full"></div></td>
            <td class="px-6 py-3"><div class="h-4 w-12 shimmer rounded-md"></div></td>
            <td class="px-6 py-3"><div class="h-6 w-20 shimmer rounded-full"></div></td>
            <td class="px-6 py-3"><div class="h-8 w-20 shimmer rounded-lg ml-auto"></div></td>
        </tr>`;
    }
    tbody.innerHTML = html;
}

// ═══════════════════════════════════════
// RENDERING
// ═══════════════════════════════════════

function renderTable(items) {
    const tbody = document.getElementById('foodTableBody');
    const emptyState = document.getElementById('emptyState');

    if (items.length === 0) {
        tbody.innerHTML = '';
        emptyState.classList.remove('hidden');
        emptyState.classList.add('flex');
        return;
    }

    emptyState.classList.add('hidden');
    emptyState.classList.remove('flex');
    tbody.innerHTML = items.map(item => buildRow(item)).join('');
}

function buildRow(item) {
    const category = item.category || 'General';
    const catClass = `cat-${category.toLowerCase()}`;

    // Stock color
    let stockColor = 'text-primary-dark'; // >= 10
    if (item.stock === 0) stockColor = 'text-danger-red';
    else if (item.stock < 10) stockColor = 'text-accent-orange';

    // Status badge
    const isAvailable = item.is_available ?? item.available;
    const statusBadge = isAvailable && item.stock > 0
        ? '<span class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-green-100 text-green-700">Available</span>'
        : '<span class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-red-100 text-red-600">Out of Stock</span>';
    const dietTypeRaw = item.dietary_type || 'Veg';
    const dietType = dietTypeRaw === 'Plant-Based' ? 'Plant-Based' : (dietTypeRaw === 'Non-Veg' ? 'Non-Veg' : 'Veg');
    let dietBadgeClass = 'bg-emerald-100 text-emerald-700';
    if (dietType === 'Non-Veg') dietBadgeClass = 'bg-rose-100 text-rose-700';
    if (dietType === 'Plant-Based') dietBadgeClass = 'bg-lime-100 text-lime-700';

    // Image
    let imageHtml;
    if (item.image_url) {
        imageHtml = `<div class="w-10 h-10 rounded-lg bg-cover bg-center shadow-sm border border-black/5" style="background-image: url('${item.image_url}')"></div>`;
    } else if (item.image_emoji) {
        imageHtml = `<div class="w-10 h-10 rounded-lg bg-black/5 flex items-center justify-center text-lg border border-black/5">${item.image_emoji}</div>`;
    } else {
        imageHtml = `<div class="w-10 h-10 rounded-lg bg-black/5 flex items-center justify-center text-lg border border-black/5">🍽️</div>`;
    }

    return `
    <tr class="group hover:bg-white/80 transition-colors h-[72px] border-b border-black/5" id="row-${item.id}">
        <td class="px-6 py-3">${imageHtml}</td>
        <td class="px-6 py-3">
            <p class="font-bold text-text-main text-sm">${item.name}</p>
            <p class="text-[10px] text-text-muted">ID: #${item.id}</p>
        </td>
        <td class="px-6 py-3">
            <span class="px-3 py-1 rounded-full text-[10px] font-bold ${catClass}">${category}</span>
        </td>
        <td class="px-6 py-3 text-right">
            <span class="text-sm font-medium text-text-main">${item.calories}</span>
            <span class="text-[10px] text-text-muted ml-0.5">kcal</span>
        </td>
        <td class="px-6 py-3 text-right">
            <span class="text-sm font-medium text-text-main">${item.sugar}</span>
            <span class="text-[10px] text-text-muted ml-0.5">g</span>
        </td>
        <td class="px-6 py-3 text-right">
            <span class="text-sm font-medium text-text-main">${item.protein}</span>
            <span class="text-[10px] text-text-muted ml-0.5">g</span>
        </td>
        <td class="px-6 py-3">
            <span class="px-2.5 py-1 rounded-full text-[10px] font-bold ${dietBadgeClass}">${dietType}</span>
        </td>
        <td class="px-6 py-3 text-right">
            <span class="text-sm font-bold ${stockColor}">${item.stock}</span>
        </td>
        <td class="px-6 py-3">${statusBadge}</td>
        <td class="px-6 py-3 text-right">
            <div class="flex items-center justify-end gap-1">
                <button onclick="openEditModal(${item.id})" class="px-3 py-1.5 rounded-lg text-xs font-bold text-blue-700 bg-blue-50 border border-blue-200 hover:bg-blue-100 transition-all" title="Edit">
                    Edit
                </button>
                <button onclick="openDeleteModal(${item.id}, '${item.name.replace(/'/g, "\\'")}')" class="px-3 py-1.5 rounded-lg text-xs font-bold text-red-700 bg-red-50 border border-red-200 hover:bg-red-100 transition-all" title="Delete">
                    Delete
                </button>
            </div>
        </td>
    </tr>`;
}

function updateResultsCount(showing, total) {
    document.getElementById('resultsCount').textContent = `Showing ${showing} of ${total} items`;
}

// ═══════════════════════════════════════
// FILTERING
// ═══════════════════════════════════════

function filterTable() {
    const search = document.getElementById('searchInput').value.toLowerCase().trim();
    const dietType = document.getElementById('filterDietType').value;
    const category = document.getElementById('filterCategory').value;
    const status = document.getElementById('filterStatus').value;

    const filtered = foodsData.filter(item => {
        if (!item || !item.name) return false;
        const matchName = item.name.toLowerCase().includes(search);
        const itemDiet = item.dietary_type || 'Veg';
        const matchDiet = dietType === 'all' || itemDiet === dietType;
        const matchCat = category === 'all' || item.category === category;
        const isAvailable = item.is_available ?? item.available;
        const matchStatus = status === 'all' ||
            (status === 'available' && isAvailable && item.stock > 0) ||
            (status === 'out' && (!isAvailable || item.stock === 0));
        return matchName && matchDiet && matchCat && matchStatus;
    });

    renderTable(filtered);
    updateResultsCount(filtered.length, foodsData.length);
}

// ═══════════════════════════════════════
// ADD / EDIT MODAL
// ═══════════════════════════════════════

function openAddModal() {
    editingId = null;
    document.getElementById('modalTitle').textContent = 'Add New Food Item';
    document.getElementById('submitBtnText').textContent = 'Save Food';
    resetForm();
    document.getElementById('fieldAvailable').checked = true; // Default ON
    document.getElementById('fieldDietaryType').value = 'Veg';
    document.getElementById('fieldIngredients').value = '';
    // clear additional fields
    ['food-sodium', 'food-carbs', 'food-price', 'food-emoji'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    document.getElementById('foodModal').classList.add('open');
}

function openEditModal(id) {
    const idNum = Number(id);
    const item = foodsData.find(f => Number(f.id) === idNum);
    if (!item) return;

    editingId = item.id;
    document.getElementById('modalTitle').textContent = 'Edit Food Item';
    document.getElementById('submitBtnText').textContent = 'Update Food';

    // Pre-fill
    document.getElementById('fieldName').value = item.name;
    document.getElementById('fieldCategory').value = item.category;
    document.getElementById('fieldCalories').value = item.calories;
    document.getElementById('fieldStock').value = item.stock;
    document.getElementById('fieldSugar').value = item.sugar;
    document.getElementById('fieldProtein').value = item.protein;
    document.getElementById('fieldFat').value = item.fat || '';
    document.getElementById('food-sodium').value = item.sodium || 0;
    document.getElementById('food-carbs').value = item.carbs || 0;
    document.getElementById('food-price').value = item.price || 0;
    document.getElementById('food-emoji').value = item.image_emoji || '';
    document.getElementById('fieldImageUrl').value = item.image_url || '';
    document.getElementById('fieldDescription').value = item.description || '';
    document.getElementById('fieldDietaryType').value = item.dietary_type || 'Veg';
    document.getElementById('fieldIngredients').value = item.ingredients || '';
    document.getElementById('fieldAvailable').checked = item.available || item.is_available;

    imagePreview(item.image_url || item.image_emoji);
    clearValidationErrors();
    document.getElementById('foodModal').classList.add('open');
}

function closeModal() {
    document.getElementById('foodModal').classList.remove('open');
    editingId = null;
    resetForm();
}

function resetForm() {
    document.getElementById('foodForm').reset();
    clearValidationErrors();
    imagePreview('');
}

function clearValidationErrors() {
    document.querySelectorAll('.field-error').forEach(el => el.classList.remove('field-error'));
}

// ═══════════════════════════════════════
// VALIDATION
// ═══════════════════════════════════════

function validateForm() {
    clearValidationErrors();
    let valid = true;
    const errors = [];

    const name = document.getElementById('fieldName');
    if (!name.value.trim() || name.value.trim().length < 2 || name.value.trim().length > 100) {
        name.classList.add('field-error');
        errors.push('name');
        valid = false;
    }

    const cat = document.getElementById('fieldCategory');
    if (!cat.value) {
        cat.classList.add('field-error');
        errors.push('category');
        valid = false;
    }
    const diet = document.getElementById('fieldDietaryType');
    if (!diet.value) {
        diet.classList.add('field-error');
        errors.push('dietary_type');
        valid = false;
    }

    // numeric fields that must be ≥0
    ['fieldCalories', 'fieldStock', 'fieldSugar', 'fieldProtein',
        'food-sodium', 'food-carbs', 'food-price'].forEach(id => {
            const el = document.getElementById(id);
            if (el && (el.value === '' || Number(el.value) < 0)) {
                el.classList.add('field-error');
                errors.push(id);
                valid = false;
            }
        });

    const imgUrl = document.getElementById('fieldImageUrl').value.trim();
    if (imgUrl && !imgUrl.match(/^https?:\/\//)) {
        document.getElementById('fieldImageUrl').classList.add('field-error');
        errors.push('imageUrl');
        valid = false;
    }

    // Scroll to first invalid
    if (!valid) {
        const first = document.querySelector('.field-error');
        if (first) first.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    return { valid, errors };
}

// ═══════════════════════════════════════
// SUBMIT
// ═══════════════════════════════════════

async function submitFood() {
    if (isSubmitting) return;

    const { valid } = validateForm();
    if (!valid) return;

    isSubmitting = true;
    const btn = document.getElementById('submitBtn');
    const spinner = document.getElementById('submitSpinner');
    btn.disabled = true;
    spinner.classList.remove('hidden');

    const payload = {
        name: document.getElementById('fieldName').value.trim(),
        category: document.getElementById('fieldCategory').value,
        dietary_type: document.getElementById('fieldDietaryType').value,
        calories: Number(document.getElementById('fieldCalories').value),
        stock: Number(document.getElementById('fieldStock').value),
        sugar: Number(document.getElementById('fieldSugar').value),
        protein: Number(document.getElementById('fieldProtein').value),
        fat: Number(document.getElementById('fieldFat').value) || 0,
        sodium: parseFloat(document.getElementById('food-sodium').value) || 0,
        carbs: parseFloat(document.getElementById('food-carbs').value) || 0,
        price: parseFloat(document.getElementById('food-price').value) || 0,
        image_emoji: document.getElementById('food-emoji').value.trim(),
        image_url: document.getElementById('fieldImageUrl').value.trim(),
        description: document.getElementById('fieldDescription').value.trim(),
        ingredients: document.getElementById('fieldIngredients').value.trim(),
        available: document.getElementById('fieldAvailable').checked
    };

    try {
        if (editingId === null) {
            // ADD MODE — POST /api/admin/foods/
            const response = await HealthBite.apiFetch('/foods/', {
                method: 'POST',
                body: JSON.stringify(payload)
            });
            const newItem = response;
            foodsData.unshift(newItem);
            closeModal();
            filterTable();
            if (window.HealthBite) HealthBite.showToast('Food item added successfully!', 'success');
        } else {
            // EDIT MODE — PUT /api/admin/foods/:id
            const response = await HealthBite.apiFetch(`/foods/${editingId}`, {
                method: 'PUT',
                body: JSON.stringify(payload)
            });
            const updatedItem = response;
            const idx = foodsData.findIndex(f => f.id === editingId);
            if (idx !== -1) {
                foodsData[idx] = { ...foodsData[idx], ...updatedItem };
                closeModal();
                filterTable();
                // Flash row
                const row = document.getElementById(`row-${editingId}`);
                if (row) { row.classList.add('row-flash'); setTimeout(() => row.classList.remove('row-flash'), 800); }
                if (window.HealthBite) HealthBite.showToast('Food item updated successfully!', 'success');
            }
        }
    } catch (e) {
        if (window.HealthBite) HealthBite.showToast('Operation failed: ' + e.message, 'error');
    } finally {
        isSubmitting = false;
        btn.disabled = false;
        spinner.classList.add('hidden');
    }
}

// ═══════════════════════════════════════
// DELETE
// ═══════════════════════════════════════

function openDeleteModal(id, name) {
    deletingId = Number(id);
    document.getElementById('deleteItemName').textContent = name;
    document.getElementById('deleteModal').classList.add('open');
}

function closeDeleteModal() {
    document.getElementById('deleteModal').classList.remove('open');
    deletingId = null;
}

async function confirmDelete() {
    if (isSubmitting || !deletingId) return;
    isSubmitting = true;

    const btn = document.getElementById('deleteConfirmBtn');
    const spinner = document.getElementById('deleteSpinner');
    const btnText = document.getElementById('deleteBtnText');
    btn.disabled = true;
    spinner.classList.remove('hidden');
    btnText.textContent = 'Deleting...';

    try {
        // DELETE /api/admin/foods/:deletingId
        await HealthBite.apiFetch(`/foods/${Number(deletingId)}`, {
            method: 'DELETE'
        });

        const row = document.getElementById(`row-${deletingId}`);
        if (row) {
            row.classList.add('row-deleting');
            setTimeout(() => row.remove(), 300);
        }

        foodsData = foodsData.filter(f => Number(f.id) !== Number(deletingId));
        closeDeleteModal();
        updateResultsCount(foodsData.length, foodsData.length);
        if (window.HealthBite) HealthBite.showToast('Deleted and removed from recommendations', 'success');
    } catch (e) {
        if (window.HealthBite) HealthBite.showToast('Delete failed: ' + e.message, 'error');
    } finally {
        isSubmitting = false;
        btn.disabled = false;
        spinner.classList.add('hidden');
        btnText.textContent = 'Yes, Delete';
    }
}

// ═══════════════════════════════════════
// AVAILABILITY TOGGLE
// ═══════════════════════════════════════

async function toggleAvailability(id, currentState, rowEl) {
    const idNum = Number(id);
    const toggleWrapper = document.getElementById(`toggle-${idNum}`);
    if (!toggleWrapper) return;
    toggleWrapper.classList.add('toggle-loading');

    try {
        // PATCH /api/admin/foods/:id/availability
        const response = await HealthBite.apiFetch(`/foods/${idNum}/availability`, {
            method: 'PATCH'
        });
        // Update local state
        const idx = foodsData.findIndex(f => Number(f.id) === idNum);
        if (idx !== -1) {
            foodsData[idx].is_available = response.is_available;
            foodsData[idx].available = response.is_available;
        }
    } catch (e) {
        // Revert toggle
        const checkbox = toggleWrapper.querySelector('input');
        checkbox.checked = currentState;
        if (window.HealthBite) HealthBite.showToast('Toggle failed', 'error');
    } finally {
        toggleWrapper.classList.remove('toggle-loading');
    }
}

// ═══════════════════════════════════════
// IMAGE PREVIEW
// ═══════════════════════════════════════

function imagePreview(urlOrEmoji) {
    const preview = document.getElementById('imagePreview');
    if (urlOrEmoji && urlOrEmoji.match(/^https?:\/\//)) {
        preview.innerHTML = `<img src="${urlOrEmoji}" class="w-full h-full object-cover rounded-lg" onerror="this.parentElement.innerHTML='🍽️'">`;
    } else if (urlOrEmoji) {
        // treat as emoji/text
        preview.innerHTML = urlOrEmoji;
    } else {
        preview.innerHTML = '🍽️';
    }
}

/* ═══════════════════════════════════════════════════════
   search.js – Search & Filter Page
   ═══════════════════════════════════════════════════════ */

let currentPage = 1;
let totalPages = 1;

// ── Get URL Params ────────────────────────────────────────────
function getParams() {
  const params = new URLSearchParams(window.location.search);
  return {
    q: params.get('q') || '',
    category: params.get('category') || '',
    condition: params.get('condition') || '',
    department: params.get('department') || '',
    min_price: params.get('min_price') || '',
    max_price: params.get('max_price') || '',
    sort: params.get('sort') || 'newest',
    page: parseInt(params.get('page')) || 1,
  };
}

// ── Update URL ─────────────────────────────────────────────────
function updateURL(params) {
  const url = new URL(window.location);
  Object.entries(params).forEach(([k, v]) => {
    if (v) url.searchParams.set(k, v);
    else url.searchParams.delete(k);
  });
  window.history.pushState({}, '', url);
}

// ── Load Results ───────────────────────────────────────────────
async function loadResults(params = {}) {
  const grid = document.getElementById('results-grid');
  const countEl = document.getElementById('result-count');
  const pageInfo = document.getElementById('page-info');

  // Skeletons
  grid.innerHTML = Array(8).fill(buildSkeletonCard()).join('');

  try {
    const data = await API.get('/api/products', { limit: 12, ...params });
    const products = data.products || [];
    totalPages = data.pages || 1;
    currentPage = data.page || 1;

    if (countEl) countEl.textContent = `${data.total} result${data.total !== 1 ? 's' : ''}`;
    if (pageInfo) pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;

    if (!products.length) {
      grid.innerHTML = `
        <div class="empty-state" style="grid-column:1/-1;">
          <div class="empty-state-icon">🔍</div>
          <h3>No products found</h3>
          <p>Try adjusting your filters or search terms</p>
          <button class="btn btn-outline" onclick="clearAllFilters()">Clear Filters</button>
        </div>`;
      return;
    }

    grid.innerHTML = products.map(p => buildProductCard(p)).join('');
    initWishlistState();
    renderPagination();

  } catch (e) {
    grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:40px;color:var(--text-muted);">Failed to load results. Please try again.</div>`;
  }
}

// ── Pagination ─────────────────────────────────────────────────
function renderPagination() {
  const container = document.getElementById('pagination');
  if (!container) return;

  if (totalPages <= 1) { container.innerHTML = ''; return; }

  let html = `<button class="page-btn" ${currentPage === 1 ? 'disabled' : ''} onclick="changePage(${currentPage - 1})">‹</button>`;

  for (let i = 1; i <= totalPages; i++) {
    if (i === 1 || i === totalPages || (i >= currentPage - 1 && i <= currentPage + 1)) {
      html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" onclick="changePage(${i})">${i}</button>`;
    } else if (i === currentPage - 2 || i === currentPage + 2) {
      html += `<span style="padding:0 4px;color:var(--text-muted)">…</span>`;
    }
  }

  html += `<button class="page-btn" ${currentPage === totalPages ? 'disabled' : ''} onclick="changePage(${currentPage + 1})">›</button>`;
  container.innerHTML = html;
}

function changePage(page) {
  currentPage = page;
  const params = collectFilters();
  params.page = page;
  updateURL(params);
  loadResults(params);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

window.changePage = changePage;

// ── Collect Filters ────────────────────────────────────────────
function collectFilters() {
  return {
    q: document.getElementById('search-input')?.value?.trim() || '',
    category: document.getElementById('filter-category')?.value || '',
    condition: document.getElementById('filter-condition')?.value || '',
    department: document.getElementById('filter-department')?.value?.trim() || '',
    min_price: document.getElementById('filter-min-price')?.value || '',
    max_price: document.getElementById('filter-max-price')?.value || '',
    sort: document.getElementById('sort-select')?.value || 'newest',
  };
}

// ── Apply Filters ──────────────────────────────────────────────
function applyFilters() {
  currentPage = 1;
  const params = collectFilters();
  updateURL({ ...params, page: 1 });
  loadResults({ ...params, page: 1 });
}

// ── Clear Filters ──────────────────────────────────────────────
function clearAllFilters() {
  ['filter-category', 'filter-condition', 'sort-select'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  ['filter-department', 'filter-min-price', 'filter-max-price', 'search-input'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  applyFilters();
}

window.applyFilters = applyFilters;
window.clearAllFilters = clearAllFilters;

// ── Debounced Search ───────────────────────────────────────────
let searchTimeout;
function onSearchInput() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(applyFilters, 400);
}

window.onSearchInput = onSearchInput;

// ── Toggle Mobile Filters ──────────────────────────────────────
function toggleFilters() {
  const sidebar = document.getElementById('filter-sidebar');
  sidebar?.classList.toggle('open');
}

window.toggleFilters = toggleFilters;

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const params = getParams();

  // Pre-fill fields
  const setVal = (id, val) => { const el = document.getElementById(id); if (el && val) el.value = val; };
  setVal('search-input', params.q);
  setVal('filter-category', params.category);
  setVal('filter-condition', params.condition);
  setVal('filter-department', params.department);
  setVal('filter-min-price', params.min_price);
  setVal('filter-max-price', params.max_price);
  setVal('sort-select', params.sort);

  // Update search page title
  if (params.q) {
    document.getElementById('search-page-title').textContent = `Results for "${params.q}"`;
    document.title = `"${params.q}" – NIT-Campus mart`;
  }

  // Populate categories
  const catSelect = document.getElementById('filter-category');
  if (catSelect && catSelect.options.length <= 1) {
    [
      'Engineering Books', 'Lab Coats', 'Scientific Calculators',
      'Drawing Instruments', 'Electronics', 'Hostel Items',
      'Stationery', 'Bags', 'Cycles',
    ].forEach(c => {
      const opt = new Option(c, c);
      catSelect.add(opt);
    });
    if (params.category) catSelect.value = params.category;
  }

  loadResults(params);
});

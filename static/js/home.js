/* ═══════════════════════════════════════════════════════
   home.js – Home page logic
   ═══════════════════════════════════════════════════════ */

const CATEGORIES = [
  'Engineering Books', 'Lab Coats', 'Scientific Calculators',
  'Drawing Instruments',
];

// ── Animated Counter ─────────────────────────────────────────
function animateCounter(el, target, duration = 1200) {
  const start = performance.now();
  const update = (time) => {
    const progress = Math.min((time - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.floor(eased * target).toLocaleString('en-IN');
    if (progress < 1) requestAnimationFrame(update);
    else el.textContent = target.toLocaleString('en-IN');
  };
  requestAnimationFrame(update);
}

// ── Hero Search ──────────────────────────────────────────────
function initHeroSearch() {
  const input = document.getElementById('hero-search');
  const btn = document.getElementById('hero-search-btn');
  const catSelect = document.getElementById('hero-search-cat');

  function doSearch() {
    const q = input?.value?.trim();
    const cat = catSelect?.value;
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    if (cat) params.set('category', cat);
    window.location.href = `/search?${params.toString()}`;
  }

  btn?.addEventListener('click', doSearch);
  input?.addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });
}

// ── Load Category Counts ─────────────────────────────────────
async function loadCategoryCounts() {
  try {
    const counts = await API.get('/api/products/categories-count');
    CATEGORIES.forEach(cat => {
      const el = document.querySelector(`[data-cat-count="${cat}"]`);
      if (el) {
        const n = counts[cat] || 0;
        el.textContent = `${n} item${n !== 1 ? 's' : ''}`;
      }
    });
  } catch (e) { /* non-critical */ }
}

// ── Load Products Section ────────────────────────────────────
async function loadProductSection(containerId, params = {}) {
  const container = document.getElementById(containerId);
  if (!container) return;

  // Show skeletons
  container.innerHTML = Array(4).fill(buildSkeletonCard()).join('');

  try {
    const data = await API.get('/api/products', { limit: 8, ...params });
    const products = data.products || [];

    if (!products.length) {
      container.innerHTML = `
        <div class="empty-state" style="padding:40px 0">
          <div class="empty-state-icon">📭</div>
          <p>No products yet</p>
        </div>`;
      return;
    }

    container.innerHTML = products.map(p => buildProductCard(p)).join('');
    initWishlistState(); // update heart states
  } catch (e) {
    container.innerHTML = `<p style="color:var(--text-muted);padding:20px">Failed to load products.</p>`;
  }
}

// ── Load Stats ────────────────────────────────────────────────
async function loadHomeStats() {
  try {
    const data = await API.get('/api/products', { limit: 1 });
    const totalEl = document.getElementById('stat-products');
    if (totalEl && data.total) {
      const observer = new IntersectionObserver(entries => {
        entries.forEach(e => {
          if (e.isIntersecting) {
            animateCounter(totalEl, data.total);
            observer.disconnect();
          }
        });
      });
      observer.observe(totalEl);
    }
  } catch (e) { /* non-critical */ }
}

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initHeroSearch();
  loadProductSection('popular-products', { sort: 'price_asc' });
  loadCategoryCounts();
  loadHomeStats();
});

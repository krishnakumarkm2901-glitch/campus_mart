/* ═══════════════════════════════════════════════════════
   home.js – Home page logic
   ═══════════════════════════════════════════════════════ */

const CATEGORIES = [
  'Engineering Books', 'Lab Coats', 'Scientific Calculators',
  'Written Notes',
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

// ── Load Home Summary ───────────────────────────────────────
async function loadHomeSummary() {
  const container = document.getElementById('popular-products');
  if (!container) return;
  container.innerHTML = Array(4).fill(buildSkeletonCard()).join('');

  try {
    const data = await API.get('/api/home-summary');
    const products = data.featured || [];
    const totalEl = document.getElementById('stat-products');

    CATEGORIES.forEach(cat => {
      const el = document.querySelector(`[data-cat-count="${cat}"]`);
      if (el) {
        const n = data.counts?.[cat] || 0;
        el.textContent = `${n} item${n !== 1 ? 's' : ''}`;
      }
    });

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

    if (!products.length) {
      container.innerHTML = `
        <div class="empty-state" style="padding:40px 0">
          <div class="empty-state-icon">📭</div>
          <p>No products yet</p>
        </div>`;
      return;
    }

    container.innerHTML = products.map(p => buildProductCard(p)).join('');
    initWishlistState();
  } catch (e) {
    container.innerHTML = `<p style="color:var(--text-muted);padding:20px">Failed to load products.</p>`;
  }
}

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initHeroSearch();
  loadHomeSummary();
});

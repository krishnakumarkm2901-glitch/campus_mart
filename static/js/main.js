/* ═══════════════════════════════════════════════════════
   main.js – Global utilities (navbar, toast, auth state)
   ═══════════════════════════════════════════════════════ */

// ── Toast Notification System ─────────────────────────────
const Toast = {
  container: null,

  init() {
    this.container = document.getElementById('toast-container');
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.id = 'toast-container';
      this.container.className = 'toast-container';
      document.body.appendChild(this.container);
    }
  },

  show(message, type = 'info', duration = 3500) {
    this.init();
    const icons = { success: '✓', error: '✕', info: 'ℹ', warning: '⚠' };
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span class="toast-icon">${icons[type] || icons.info}</span><span>${message}</span>`;
    this.container.appendChild(toast);
    setTimeout(() => {
      toast.classList.add('fade-out');
      setTimeout(() => toast.remove(), 350);
    }, duration);
    return toast;
  },

  success(msg, d) { return this.show(msg, 'success', d); },
  error(msg, d) { return this.show(msg, 'error', d); },
  info(msg, d) { return this.show(msg, 'info', d); },
  warning(msg, d) { return this.show(msg, 'warning', d); },
};

// ── API Helper ──────────────────────────────────────────────
const API = {
  async get(url, params = {}) {
    const qs = new URLSearchParams(params).toString();
    const res = await fetch(qs ? `${url}?${qs}` : url);
    return res.json();
  },

  async post(url, data = {}, isForm = false) {
    const opts = { method: 'POST' };
    if (isForm) {
      opts.body = data;
    } else {
      opts.headers = { 'Content-Type': 'application/json' };
      opts.body = JSON.stringify(data);
    }
    const res = await fetch(url, opts);
    return { ok: res.ok, status: res.status, data: await res.json() };
  },

  async put(url, data = {}, isForm = false) {
    const opts = { method: 'PUT' };
    if (isForm) {
      opts.body = data;
    } else {
      opts.headers = { 'Content-Type': 'application/json' };
      opts.body = JSON.stringify(data);
    }
    const res = await fetch(url, opts);
    return { ok: res.ok, status: res.status, data: await res.json() };
  },

  async patch(url, data = {}) {
    const res = await fetch(url, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return { ok: res.ok, status: res.status, data: await res.json() };
  },

  async del(url) {
    const res = await fetch(url, { method: 'DELETE' });
    return { ok: res.ok, status: res.status, data: await res.json() };
  },
};

// ── Navbar ──────────────────────────────────────────────────
function initNavbar() {
  const hamburger = document.getElementById('hamburger');
  const mobileMenu = document.getElementById('mobile-menu');
  const navSearch = document.getElementById('nav-search-input');
  const navSearchBtn = document.getElementById('nav-search-btn');

  if (hamburger && mobileMenu) {
    hamburger.addEventListener('click', () => {
      mobileMenu.classList.toggle('open');
      const spans = hamburger.querySelectorAll('span');
      if (mobileMenu.classList.contains('open')) {
        spans[0].style.transform = 'rotate(45deg) translate(5px, 5px)';
        spans[1].style.opacity = '0';
        spans[2].style.transform = 'rotate(-45deg) translate(5px, -5px)';
      } else {
        spans.forEach(s => { s.style.transform = ''; s.style.opacity = ''; });
      }
    });

    document.addEventListener('click', (e) => {
      if (!hamburger.contains(e.target) && !mobileMenu.contains(e.target)) {
        mobileMenu.classList.remove('open');
        hamburger.querySelectorAll('span').forEach(s => {
          s.style.transform = '';
          s.style.opacity = '';
        });
      }
    });
  }

  function doSearch() {
    const q = navSearch?.value?.trim();
    if (q) window.location.href = `/search?q=${encodeURIComponent(q)}`;
  }

  navSearch?.addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });
  navSearchBtn?.addEventListener('click', doSearch);
}

// ── Scroll Reveal ───────────────────────────────────────────
function initScrollReveal() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

  document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
}

// ── Number Formatter ────────────────────────────────────────
function formatPrice(n) {
  return '₹' + Number(n).toLocaleString('en-IN');
}

function formatDate(dateStr) {
  if (!dateStr) return 'Unknown';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

function timeAgo(dateStr) {
  if (!dateStr) return '';
  const diff = (Date.now() - new Date(dateStr)) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return formatDate(dateStr);
}

// ── Category Icons ──────────────────────────────────────────
const CATEGORY_ICONS = {
  'Engineering Books': { icon: '📚', cls: 'cat-books' },
  'Lab Coats': { icon: '🥼', cls: 'cat-lab' },
  'Scientific Calculators': { icon: '🧮', cls: 'cat-calc' },
  'Written Notes': { icon: '📝', cls: 'cat-drawing' },
};

// ── Product Card HTML ───────────────────────────────────────
function buildProductCard(p, showWishlist = true) {
  const img = p.images?.[0]?.url;
  const cat = CATEGORY_ICONS[p.category] || { icon: '📦', cls: 'cat-misc' };
  const isSold = p.status === 'sold';

  return `
    <div class="product-card" onclick="window.location='/product/${p._id}'">
      <div style="position:relative;overflow:hidden;">
        ${img
          ? `<img src="${img}" alt="${p.name}" class="product-card-image" loading="lazy">`
          : `<div class="product-card-image-placeholder">${cat.icon}</div>`
        }
        ${isSold ? `<div class="sold-overlay"><div class="sold-badge">SOLD</div></div>` : ''}
        ${showWishlist && !isSold ? `
          <button class="wishlist-btn" onclick="event.stopPropagation();toggleWishlist('${p._id}',this)"
            id="wb-${p._id}" title="Save to wishlist">🤍</button>
        ` : ''}
      </div>
      <div class="product-card-body">
        <div class="product-card-price">${formatPrice(p.price)}</div>
        <div class="product-card-name">${escHtml(p.name)}</div>
        <div class="product-card-meta">
          <span class="badge badge-primary">${escHtml(p.category)}</span>
          <span class="badge badge-muted">${escHtml(p.condition)}</span>
        </div>
      </div>
      <div class="product-card-footer">
        <span>📍 ${escHtml(p.department || 'N/A')}</span>
        <span>${timeAgo(p.created_at)}</span>
      </div>
    </div>
  `;
}

// ── Skeleton Product Card ────────────────────────────────────
function buildSkeletonCard() {
  return `
    <div class="skeleton-card">
      <div class="skeleton" style="height:180px;"></div>
      <div style="padding:14px;">
        <div class="skeleton" style="height:18px;width:60%;margin-bottom:8px;"></div>
        <div class="skeleton" style="height:14px;margin-bottom:6px;"></div>
        <div class="skeleton" style="height:14px;width:80%;"></div>
      </div>
    </div>
  `;
}

// ── Wishlist Toggle ─────────────────────────────────────────
const wishlistState = new Set();

async function initWishlistState() {
  try {
    const items = await API.get('/api/wishlist');
    if (Array.isArray(items)) {
      items.forEach(p => wishlistState.add(p._id));
      document.querySelectorAll('.wishlist-btn').forEach(btn => {
        const id = btn.id.replace('wb-', '');
        if (wishlistState.has(id)) {
          btn.textContent = '❤️';
          btn.classList.add('active');
        }
      });
    }
  } catch (e) { /* not logged in */ }
}

async function toggleWishlist(productId, btn) {
  if (wishlistState.has(productId)) {
    const r = await API.del(`/api/wishlist/${productId}`);
    if (r.ok) {
      wishlistState.delete(productId);
      btn.textContent = '🤍';
      btn.classList.remove('active');
      Toast.info('Removed from wishlist');
    }
  } else {
    const r = await API.post(`/api/wishlist/${productId}`);
    if (r.ok) {
      wishlistState.add(productId);
      btn.textContent = '❤️';
      btn.classList.add('active');
      Toast.success('Added to wishlist ❤️');
    } else if (r.status === 401) {
      Toast.warning('Please log in to save products');
      setTimeout(() => window.location.href = '/login', 1500);
    }
  }
}

// ── HTML Escape ──────────────────────────────────────────────
function escHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Modal Helpers ────────────────────────────────────────────
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.style.display = 'none';
    document.body.style.overflow = '';
  }
}

// Close modal on overlay click
document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.style.display = 'none';
    document.body.style.overflow = '';
  }
});

// ── Init ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initNavbar();
  initScrollReveal();
  initWishlistState();
});

window.Toast = Toast;
window.API = API;
window.formatPrice = formatPrice;
window.formatDate = formatDate;
window.timeAgo = timeAgo;
window.buildProductCard = buildProductCard;
window.buildSkeletonCard = buildSkeletonCard;
window.toggleWishlist = toggleWishlist;
window.escHtml = escHtml;
window.openModal = openModal;
window.closeModal = closeModal;
window.CATEGORY_ICONS = CATEGORY_ICONS;

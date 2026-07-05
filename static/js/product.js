/* ═══════════════════════════════════════════════════════
   product.js – Product Detail Page
   ═══════════════════════════════════════════════════════ */

let currentProduct = null;
let currentImageIndex = 0;
let images = [];

// ── Load Product ──────────────────────────────────────────────
async function loadProduct() {
  const productId = document.getElementById('product-data')?.dataset?.productId;
  if (!productId) return;

  showLoadingSkeleton();

  try {
    const p = await API.get(`/api/products/${productId}`);
    if (p.error) {
      document.getElementById('product-container').innerHTML =
        `<div class="empty-state"><div class="empty-state-icon">❌</div>
        <h3>Product not found</h3><p>${p.error}</p>
        <a href="/" class="btn btn-primary">Back to Home</a></div>`;
      return;
    }
    currentProduct = p;
    renderProduct(p);

    // Check wishlist
    try {
      const wl = await API.get(`/api/wishlist/check/${productId}`);
      const btn = document.getElementById('wishlist-action-btn');
      if (btn && wl.in_wishlist) {
        btn.textContent = '❤️ Saved';
        btn.dataset.saved = 'true';
      }
    } catch (e) { /* not logged in */ }

  } catch (e) {
    document.getElementById('product-container').innerHTML =
      `<div class="empty-state"><div class="empty-state-icon">⚠️</div>
      <h3>Failed to load product</h3><a href="/" class="btn btn-primary">Back to Home</a></div>`;
  }
}

function showLoadingSkeleton() {
  document.getElementById('product-container').innerHTML = `
    <div class="product-detail-grid">
      <div class="image-slider">
        <div class="skeleton" style="height:420px;border-radius:0;"></div>
      </div>
      <div class="product-info-panel" style="overflow:hidden;">
        <div style="padding:24px;">
          <div class="skeleton" style="height:32px;width:50%;margin-bottom:16px;"></div>
          <div class="skeleton" style="height:24px;margin-bottom:10px;"></div>
          <div class="skeleton" style="height:16px;width:70%;margin-bottom:24px;"></div>
          <div class="skeleton" style="height:60px;border-radius:12px;"></div>
        </div>
      </div>
    </div>`;
}

function renderProduct(p) {
  images = p.images || [];
  currentImageIndex = 0;

  const cat = CATEGORY_ICONS[p.category] || { icon: '📦', cls: 'cat-misc' };

  document.title = `${p.name} – CampusMart`;
  document.getElementById('breadcrumb-name').textContent = p.name;

  // Status badge
  const statusColors = {
    approved: 'badge-success', sold: 'badge-danger', pending: 'badge-warning'
  };

  document.getElementById('product-container').innerHTML = `
    <div class="product-detail-grid">
      <!-- Image Slider -->
      <div>
        <div class="image-slider">
          <div class="slider-main" id="slider-main">
            ${images.length
              ? `<img src="${images[0].url}" alt="${escHtml(p.name)}" id="slider-img">`
              : `<div class="no-image" style="height:420px;display:flex;align-items:center;justify-content:center;font-size:80px;opacity:0.3;">${cat.icon}</div>`
            }
            ${images.length > 1 ? `
              <button class="slider-nav-btn slider-prev" onclick="slideImage(-1)">‹</button>
              <button class="slider-nav-btn slider-next" onclick="slideImage(1)">›</button>
              <div class="slider-counter" id="slide-counter">1/${images.length}</div>
            ` : ''}
          </div>
          ${images.length > 1 ? `
            <div class="slider-thumbs" id="slider-thumbs">
              ${images.map((img, i) => `
                <img src="${img.url}" class="slider-thumb ${i === 0 ? 'active' : ''}"
                  onclick="goToSlide(${i})" alt="thumb ${i + 1}">
              `).join('')}
            </div>
          ` : ''}
        </div>

        <!-- Description -->
        <div class="description-card">
          <h3>📋 Description</h3>
          <div class="description-text">${escHtml(p.description || 'No description provided.')}</div>
        </div>
      </div>

      <!-- Info Panel -->
      <div class="product-info-panel">
        <div class="product-info-top">
          <div class="product-status-badge">
            <span class="badge ${statusColors[p.status] || 'badge-muted'}">
              ${p.status === 'approved' ? '✓ Available' : p.status === 'sold' ? '✗ Sold' : p.status}
            </span>
          </div>
          <div class="product-price"><span class="currency">₹</span>${Number(p.price).toLocaleString('en-IN')}</div>
          <h1 class="product-title">${escHtml(p.name)}</h1>
          <div class="product-tags">
            <span class="badge badge-primary">${escHtml(p.category)}</span>
            <span class="badge badge-accent condition-${p.condition?.replace(' ', '-')}">${escHtml(p.condition)}</span>
          </div>
        </div>

        <!-- Call Seller -->
        <div class="product-meta-section" style="padding-top:20px;border-bottom:1px solid var(--border);">
          ${p.status !== 'sold' ? `
            <button class="call-seller-btn" id="call-btn" onclick="handleCallSeller()">
              📞 Call Seller
            </button>
            <div id="phone-display" style="display:none;"></div>
          ` : `<div style="text-align:center;padding:16px;color:var(--danger);font-weight:700;font-size:16px;">❌ This item has been sold</div>`}
        </div>

        <!-- Action Row -->
        <div class="action-row">
          <button class="btn btn-outline btn-sm" style="flex:1" id="wishlist-action-btn"
            onclick="handleWishlist()" data-saved="false">
            🤍 Save
          </button>
          <button class="btn btn-ghost btn-sm" onclick="handleShare()">
            🔗 Share
          </button>
        </div>

        <!-- Seller Info -->
        <div class="seller-card">
          <div class="seller-card-title">👤 Seller Information</div>
          <div class="seller-info">
            ${p.seller_photo
              ? `<img src="${p.seller_photo}" class="seller-avatar" alt="Seller">`
              : `<div class="seller-avatar-placeholder">${(p.seller_name || 'S')[0].toUpperCase()}</div>`
            }
            <div class="seller-details">
              <h4>${escHtml(p.seller_name || 'Anonymous')}</h4>
              <p>📧 ${escHtml(p.seller_email || '')}</p>
            </div>
          </div>
        </div>

        <!-- Meta -->
        <div class="product-meta-section">
          <div class="meta-grid">
            <div class="meta-item">
              <div class="meta-item-label">Department</div>
              <div class="meta-item-value">🎓 ${escHtml(p.department || 'N/A')}</div>
            </div>
            <div class="meta-item">
              <div class="meta-item-label">Condition</div>
              <div class="meta-item-value">${escHtml(p.condition || 'N/A')}</div>
            </div>
            <div class="meta-item">
              <div class="meta-item-label">Pickup Location</div>
              <div class="meta-item-value">📍 ${escHtml(p.pickup_location || 'N/A')}</div>
            </div>
            <div class="meta-item">
              <div class="meta-item-label">Posted</div>
              <div class="meta-item-value">🗓 ${formatDate(p.created_at)}</div>
            </div>
          </div>
        </div>

        <!-- Report -->
        <div class="report-section">
          <span class="report-link" onclick="openReportModal()">
            🚩 Report this listing
          </span>
        </div>
      </div>
    </div>
  `;
}

// ── Image Slider ───────────────────────────────────────────────
function slideImage(dir) {
  if (!images.length) return;
  currentImageIndex = (currentImageIndex + dir + images.length) % images.length;
  goToSlide(currentImageIndex);
}

function goToSlide(idx) {
  currentImageIndex = idx;
  const img = document.getElementById('slider-img');
  const counter = document.getElementById('slide-counter');
  const thumbs = document.querySelectorAll('.slider-thumb');

  if (img) {
    img.style.opacity = '0';
    setTimeout(() => {
      img.src = images[idx].url;
      img.style.opacity = '1';
    }, 150);
  }
  if (counter) counter.textContent = `${idx + 1}/${images.length}`;
  thumbs.forEach((t, i) => t.classList.toggle('active', i === idx));
}

// ── Call Seller ────────────────────────────────────────────────
function handleCallSeller() {
  const phone = currentProduct?.phone;
  if (!phone) {
    Toast.error('Phone number not available');
    return;
  }

  const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);

  if (isMobile) {
    window.location.href = `tel:${phone}`;
  } else {
    const display = document.getElementById('phone-display');
    if (display) {
      display.style.display = 'block';
      display.innerHTML = `
        <div class="phone-display">${phone}</div>
        <div class="phone-display-label">Call this number on your phone</div>
      `;
    }
    const btn = document.getElementById('call-btn');
    if (btn) btn.textContent = '✓ Number Revealed';
  }
}

// ── Wishlist ───────────────────────────────────────────────────
async function handleWishlist() {
  const btn = document.getElementById('wishlist-action-btn');
  const productId = currentProduct?._id;
  if (!productId) return;

  const saved = btn?.dataset?.saved === 'true';

  if (saved) {
    const r = await API.del(`/api/wishlist/${productId}`);
    if (r.ok) {
      btn.textContent = '🤍 Save';
      btn.dataset.saved = 'false';
      Toast.info('Removed from wishlist');
    }
  } else {
    const r = await API.post(`/api/wishlist/${productId}`);
    if (r.ok) {
      btn.textContent = '❤️ Saved';
      btn.dataset.saved = 'true';
      Toast.success('Added to wishlist ❤️');
    } else if (r.status === 401) {
      Toast.warning('Please log in to save');
      setTimeout(() => window.location.href = '/login', 1500);
    }
  }
}

// ── Share ──────────────────────────────────────────────────────
function handleShare() {
  if (navigator.share) {
    navigator.share({ title: currentProduct?.name, url: window.location.href });
  } else {
    navigator.clipboard.writeText(window.location.href).then(() => {
      Toast.success('Link copied to clipboard!');
    });
  }
}

// ── Report Modal ───────────────────────────────────────────────
function openReportModal() {
  openModal('report-modal');
}

async function submitReport() {
  const reason = document.getElementById('report-reason')?.value;
  const details = document.getElementById('report-details')?.value;

  if (!reason) {
    Toast.error('Please select a reason');
    return;
  }

  const r = await API.post('/api/reports', {
    product_id: currentProduct?._id,
    reason,
    details,
  });

  if (r.ok) {
    Toast.success('Report submitted. Thank you!');
    closeModal('report-modal');
  } else {
    Toast.error(r.data?.error || 'Failed to submit report');
  }
}

// ── Keyboard Navigation ──────────────────────────────────────
document.addEventListener('keydown', e => {
  if (e.key === 'ArrowLeft') slideImage(-1);
  if (e.key === 'ArrowRight') slideImage(1);
});

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', loadProduct);

window.slideImage = slideImage;
window.goToSlide = goToSlide;
window.handleCallSeller = handleCallSeller;
window.handleWishlist = handleWishlist;
window.handleShare = handleShare;
window.openReportModal = openReportModal;
window.submitReport = submitReport;

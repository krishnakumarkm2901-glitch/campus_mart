/* ═══════════════════════════════════════════════════════
   wishlist.js – Wishlist Page
   ═══════════════════════════════════════════════════════ */

async function loadWishlist() {
  const grid = document.getElementById('wishlist-grid');

  grid.innerHTML = Array(4).fill(buildSkeletonCard()).join('');

  try {
    const products = await API.get('/api/wishlist');

    if (!Array.isArray(products) || !products.length) {
      grid.innerHTML = `
        <div class="empty-state" style="grid-column:1/-1;">
          <div class="empty-state-icon">🤍</div>
          <h3>Your wishlist is empty</h3>
          <p>Save products by clicking the heart icon on any listing</p>
          <a href="/" class="btn btn-primary btn-lg">Browse Products</a>
        </div>`;
      return;
    }

    grid.innerHTML = products.map(p => `
      <div class="product-card" id="wl-${p._id}">
        <div style="position:relative;overflow:hidden;" onclick="window.location='/product/${p._id}'">
          ${p.images?.[0]?.url
            ? `<img src="${p.images[0].url}" alt="${escHtml(p.name)}" class="product-card-image" loading="lazy">`
            : `<div class="product-card-image-placeholder">${CATEGORY_ICONS[p.category]?.icon || '📦'}</div>`
          }
        </div>
        <div class="product-card-body" onclick="window.location='/product/${p._id}'">
          <div class="product-card-price">${formatPrice(p.price)}</div>
          <div class="product-card-name">${escHtml(p.name)}</div>
          <div class="product-card-meta">
            <span class="badge badge-primary">${escHtml(p.category)}</span>
            <span class="badge badge-muted">${escHtml(p.condition)}</span>
          </div>
        </div>
        <div class="product-card-footer">
          <button class="btn btn-ghost btn-sm" style="color:var(--danger);font-size:13px;"
            onclick="removeFromWishlist('${p._id}')">
            🗑 Remove
          </button>
          <span>${timeAgo(p.created_at)}</span>
        </div>
      </div>
    `).join('');

    document.getElementById('wishlist-count').textContent = `${products.length} saved item${products.length !== 1 ? 's' : ''}`;

  } catch (e) {
    grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:40px;color:var(--text-muted);">Failed to load wishlist.</div>`;
  }
}

async function removeFromWishlist(productId) {
  const r = await API.del(`/api/wishlist/${productId}`);
  if (r.ok) {
    Toast.info('Removed from wishlist');
    document.getElementById(`wl-${productId}`)?.remove();
    // Check if empty
    const grid = document.getElementById('wishlist-grid');
    if (!grid.children.length) loadWishlist();
  }
}

window.removeFromWishlist = removeFromWishlist;

document.addEventListener('DOMContentLoaded', loadWishlist);

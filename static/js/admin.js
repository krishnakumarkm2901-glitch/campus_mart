/* ═══════════════════════════════════════════════════════
   admin.js – Admin Dashboard, Products, Students, Report
   ═══════════════════════════════════════════════════════ */

// ── Admin Login ───────────────────────────────────────────────
async function adminLogin(e) {
  e.preventDefault();
  const username = document.getElementById('admin-username')?.value;
  const password = document.getElementById('admin-password')?.value;
  const btn = document.getElementById('login-btn');

  btn.disabled = true;
  btn.innerHTML = '<div class="spinner spinner-sm"></div> Logging in...';

  const r = await API.post('/admin/login', { username, password });

  if (r.ok && r.data.success) {
    window.location.href = r.data.redirect;
  } else {
    Toast.error(r.data?.error || 'Invalid credentials');
    btn.disabled = false;
    btn.textContent = 'Login';

    // Shake animation
    document.getElementById('admin-login-form')?.classList.add('shake');
    setTimeout(() => document.getElementById('admin-login-form')?.classList.remove('shake'), 500);
  }
}

document.getElementById('admin-login-form')?.addEventListener('submit', adminLogin);

// ── Dashboard Stats ───────────────────────────────────────────
async function loadDashboardStats() {
  if (!document.getElementById('stat-students')) return;

  try {
    const data = await API.get('/api/admin/stats');

    setText('stat-students', data.total_students);
    setText('stat-total', data.total_products);
    setText('stat-active', data.active_products);
    setText('stat-sold', data.sold_products);
    setText('stat-pending', data.pending_products);

    // Update pending badge in sidebar
    const pendingBadge = document.getElementById('pending-badge');
    if (pendingBadge && data.pending_products > 0) {
      pendingBadge.textContent = data.pending_products;
      pendingBadge.style.display = 'inline';
    }

    renderCharts(data);
  } catch (e) {
    Toast.error('Failed to load stats');
  }
}

function renderCharts(data) {
  // Category chart
  const catCtx = document.getElementById('category-chart')?.getContext('2d');
  if (catCtx && data.category_data?.length) {
    const cats = data.category_data.slice(0, 8);
    new Chart(catCtx, {
      type: 'doughnut',
      data: {
        labels: cats.map(c => c.category),
        datasets: [{
          data: cats.map(c => c.count),
          backgroundColor: [
            '#000000', '#171717', '#d4af37', '#f3d675',
            '#a67c00', '#ead58e', '#5c5543', '#ffffff',
          ],
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right', labels: { font: { family: 'Inter', size: 12 }, padding: 12 } },
        },
      },
    });
  }

  // Monthly chart
  const monthCtx = document.getElementById('monthly-chart')?.getContext('2d');
  if (monthCtx && data.monthly_data?.length) {
    new Chart(monthCtx, {
      type: 'bar',
      data: {
        labels: data.monthly_data.map(m => m.month),
        datasets: [{
          label: 'New Listings',
          data: data.monthly_data.map(m => m.count),
          backgroundColor: 'rgba(212,175,55,0.85)',
          borderRadius: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { stepSize: 1 } },
        },
      },
    });
  }
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val ?? '—';
}

// ── Admin Products Table ──────────────────────────────────────
let productPage = 1;

async function loadAdminProducts() {
  if (!document.getElementById('products-tbody')) return;

  const tbody = document.getElementById('products-tbody');
  const q = document.getElementById('products-search')?.value?.trim() || '';
  const status = document.getElementById('products-status-filter')?.value || '';

  tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:32px;">
    <div class="spinner" style="margin:0 auto;"></div></td></tr>`;

  try {
    const data = await API.get('/api/admin/products', {
      q, status, page: productPage, limit: 20
    });

    const products = data.products || [];

    if (!products.length) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:32px;color:var(--text-muted);">No products found</td></tr>`;
      return;
    }

    tbody.innerHTML = products.map(p => {
      const img = p.images?.[0]?.url;
      const statusBadge = {
        approved: '<span class="badge badge-success">Approved</span>',
        pending: '<span class="badge badge-warning">Pending</span>',
        rejected: '<span class="badge badge-danger">Rejected</span>',
        sold: '<span class="badge badge-muted">Sold</span>',
      }[p.status] || `<span class="badge badge-muted">${p.status}</span>`;

      return `<tr class="${p.status === 'pending' ? 'pending' : ''}">
        <td>
          <div class="product-thumb-cell">
            ${img ? `<img src="${img}" class="product-thumb" alt="">` : `<div class="product-thumb-placeholder">📦</div>`}
            <div>
              <div class="product-name-cell" title="${escHtml(p.name)}">${escHtml(p.name)}</div>
              <div style="font-size:12px;color:var(--text-muted);">${escHtml(p.category)}</div>
            </div>
          </div>
        </td>
        <td>${formatPrice(p.price)}</td>
        <td>${escHtml(p.seller_name || '—')}</td>
        <td>${statusBadge}</td>
        <td>${escHtml(p.condition || '—')}</td>
        <td>${formatDate(p.created_at)}</td>
        <td>
          <div class="action-cell">
            ${p.status === 'pending' ? `
              <button class="btn btn-success btn-sm btn-icon" title="Approve"
                onclick="approveProduct('${p._id}')">✓</button>
              <button class="btn btn-danger btn-sm btn-icon" title="Reject"
                onclick="rejectProduct('${p._id}')">✕</button>
            ` : ''}
            ${p.status === 'approved' ? `
              <button class="btn btn-outline btn-sm btn-icon" title="Mark Sold"
                onclick="markSold('${p._id}')">💰</button>
            ` : ''}
            <a href="/product/${p._id}" target="_blank" class="btn btn-ghost btn-sm btn-icon" title="View">👁</a>
            <button class="btn btn-danger btn-sm btn-icon" title="Delete"
              onclick="deleteProduct('${p._id}')">🗑</button>
          </div>
        </td>
      </tr>`;
    }).join('');

  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:32px;color:var(--danger);">Failed to load products</td></tr>`;
  }
}

async function approveProduct(id) {
  const r = await API.patch(`/api/admin/products/${id}/approve`);
  if (r.ok) { Toast.success('Product approved!'); loadAdminProducts(); }
  else Toast.error('Failed to approve');
}

async function rejectProduct(id) {
  const reason = prompt('Reason for rejection (optional):') || '';
  const r = await API.patch(`/api/admin/products/${id}/reject`, { reason });
  if (r.ok) { Toast.info('Product rejected'); loadAdminProducts(); }
  else Toast.error('Failed to reject');
}

async function markSold(id) {
  if (!confirm('Mark this product as sold?')) return;
  const r = await API.patch(`/api/admin/products/${id}/sold`);
  if (r.ok) { Toast.success('Marked as sold'); loadAdminProducts(); }
}

async function deleteProduct(id) {
  if (!confirm('Delete this product permanently?')) return;
  const r = await API.del(`/api/admin/products/${id}`);
  if (r.ok) { Toast.success('Product deleted'); loadAdminProducts(); }
  else Toast.error(r.data?.error || 'Failed to delete');
}

window.approveProduct = approveProduct;
window.rejectProduct = rejectProduct;
window.markSold = markSold;
window.deleteProduct = deleteProduct;

// ── Admin Students Table ──────────────────────────────────────
async function loadAdminStudents() {
  if (!document.getElementById('students-tbody')) return;

  const tbody = document.getElementById('students-tbody');
  const q = document.getElementById('students-search')?.value?.trim() || '';

  tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:32px;">
    <div class="spinner" style="margin:0 auto;"></div></td></tr>`;

  try {
    const data = await API.get('/api/admin/students', { q, limit: 20 });
    const students = data.students || [];

    if (!students.length) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:32px;color:var(--text-muted);">No students found</td></tr>`;
      return;
    }

    tbody.innerHTML = students.map(s => `
      <tr>
        <td>
          <div class="student-cell">
            ${s.profile_photo
              ? `<img src="${s.profile_photo}" class="student-avatar-sm" alt="">`
              : `<div class="seller-avatar-placeholder" style="width:36px;height:36px;font-size:16px;">${(s.name || 'U')[0].toUpperCase()}</div>`
            }
            <div>
              <div style="font-weight:600;font-size:13.5px;">${escHtml(s.name || '—')}</div>
            </div>
          </div>
        </td>
        <td style="font-size:13px;">${escHtml(s.email || '—')}</td>
        <td>${escHtml(s.department || '—')}</td>
        <td>${escHtml(s.year || '—')}</td>
        <td>${formatDate(s.created_at)}</td>
        <td>
          <button class="btn btn-danger btn-sm btn-icon" title="Delete student"
            onclick="deleteStudent('${s._id}')">🗑</button>
        </td>
      </tr>
    `).join('');

  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:32px;color:var(--danger);">Failed to load students</td></tr>`;
  }
}

async function deleteStudent(id) {
  if (!confirm('Delete this student and all their listings? This cannot be undone.')) return;
  const r = await API.del(`/api/admin/students/${id}`);
  if (r.ok) { Toast.success('Student deleted'); loadAdminStudents(); }
  else Toast.error(r.data?.error || 'Failed to delete');
}

window.deleteStudent = deleteStudent;

// ── Daily Report ──────────────────────────────────────────────
async function loadDailyReport() {
  if (!document.getElementById('report-date')) return;

  const dateEl = document.getElementById('report-date');
  const today = new Date().toISOString().split('T')[0];
  if (!dateEl.value) dateEl.value = today;

  await fetchReport(dateEl.value);
}

async function fetchReport(date) {
  try {
    const data = await API.get('/api/admin/daily-report', { date });
    renderReport(data);
  } catch (e) {
    Toast.error('Failed to load report');
  }
}

function renderReport(data) {
  setText('rep-date', data.date);
  setText('rep-new-users', data.new_users);
  setText('rep-products-added', data.products_added);
  setText('rep-products-sold', data.products_sold);
  setText('rep-active-listings', data.active_listings);
  setText('rep-total-students', data.total_students);
  setText('rep-total-products', data.total_products);

  const catBody = document.getElementById('cat-breakdown-body');
  if (catBody) {
    catBody.innerHTML = data.category_breakdown?.map((c, i) => `
      <tr>
        <td>${i + 1}</td>
        <td>${escHtml(c.category)}</td>
        <td><strong>${c.count}</strong></td>
      </tr>
    `).join('') || '<tr><td colspan="3">No data</td></tr>';
  }
}

async function changeReportDate() {
  const date = document.getElementById('report-date')?.value;
  if (date) await fetchReport(date);
}

function printReport() {
  window.print();
}

window.changeReportDate = changeReportDate;
window.printReport = printReport;

// ── Debounce ──────────────────────────────────────────────────
let searchTimeout;
function debounce(fn, delay = 400) {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(fn, delay);
}

function onProductSearch() { debounce(loadAdminProducts); }
function onStudentSearch() { debounce(loadAdminStudents); }

window.onProductSearch = onProductSearch;
window.onStudentSearch = onStudentSearch;
window.loadAdminProducts = loadAdminProducts;
window.loadAdminStudents = loadAdminStudents;

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadDashboardStats();
  loadAdminProducts();
  loadAdminStudents();
  loadDailyReport();
});

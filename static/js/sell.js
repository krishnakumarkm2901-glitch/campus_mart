/* ═══════════════════════════════════════════════════════
   sell.js – Sell/Edit Product Page
   ═══════════════════════════════════════════════════════ */

let selectedFiles = [];
const MAX_IMAGES = 5;
const isEditing = document.getElementById('page-data')?.dataset?.editing === 'true';
const productId = document.getElementById('page-data')?.dataset?.productId;

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  initImageUpload();
  populateSelects();

  if (isEditing && productId) {
    await loadProductForEdit();
  }
});

// ── Populate Selects ─────────────────────────────────────────
async function populateSelects() {
  try {
    const [cats, conds] = await Promise.all([
      API.get('/api/categories'),
      API.get('/api/conditions'),
    ]);

    const catSelect = document.getElementById('category');
    cats.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c;
      opt.textContent = c;
      catSelect?.appendChild(opt);
    });
  } catch (e) { /* static fallback in HTML */ }
}

// ── Load Existing Product ─────────────────────────────────────
async function loadProductForEdit() {
  try {
    const p = await API.get(`/api/products/${productId}`);

    document.getElementById('sell-title').textContent = 'Edit Product';
    document.getElementById('sell-subtitle').textContent = 'Update your product details. It will go for re-approval.';
    document.getElementById('submit-btn').textContent = '💾 Save Changes';

    // Fill fields
    setField('name', p.name);
    setField('description', p.description);
    setField('price', p.price);
    setField('category', p.category);
    setField('condition', p.condition);
    setField('department', p.department);
    setField('pickup_location', p.pickup_location);
    setField('phone', p.phone);

    // Condition radio
    const condInput = document.querySelector(`input[name="condition"][value="${p.condition}"]`);
    if (condInput) condInput.checked = true;

    // Show existing images
    if (p.images?.length) {
      const previews = document.getElementById('image-previews');
      previews.innerHTML = p.images.map((img, i) => `
        <div class="image-preview-item" id="existing-${i}">
          <img src="${img.url}" alt="existing image">
          ${i === 0 ? `<div class="first-badge">Cover</div>` : ''}
        </div>
      `).join('');
    }
  } catch (e) {
    Toast.error('Failed to load product');
  }
}

function setField(id, value) {
  const el = document.getElementById(id);
  if (el) el.value = value ?? '';
}

// ── Image Upload ──────────────────────────────────────────────
function initImageUpload() {
  const zone = document.getElementById('drop-zone');
  const fileInput = document.getElementById('images-input');

  zone?.addEventListener('dragover', e => {
    e.preventDefault();
    zone.classList.add('dragover');
  });

  zone?.addEventListener('dragleave', () => zone.classList.remove('dragover'));

  zone?.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('dragover');
    handleFiles(Array.from(e.dataTransfer.files));
  });

  fileInput?.addEventListener('change', () => {
    handleFiles(Array.from(fileInput.files));
    fileInput.value = ''; // reset so same file can be re-added
  });
}

function handleFiles(files) {
  const imageFiles = files.filter(f => f.type.startsWith('image/'));

  if (selectedFiles.length + imageFiles.length > MAX_IMAGES) {
    Toast.warning(`Maximum ${MAX_IMAGES} images allowed`);
    imageFiles.splice(MAX_IMAGES - selectedFiles.length);
  }

  selectedFiles = [...selectedFiles, ...imageFiles];
  renderPreviews();
}

function renderPreviews() {
  const container = document.getElementById('image-previews');
  if (!container) return;

  // Clear new previews (keep existing)
  container.querySelectorAll('.new-preview').forEach(el => el.remove());

  selectedFiles.forEach((file, i) => {
    const url = URL.createObjectURL(file);
    const div = document.createElement('div');
    div.className = 'image-preview-item new-preview';
    div.innerHTML = `
      <img src="${url}" alt="preview">
      ${i === 0 && !isEditing ? `<div class="first-badge">Cover</div>` : ''}
      <button class="remove-image-btn" onclick="removeImage(${i})">✕</button>
    `;
    container.appendChild(div);
  });

  const hint = document.getElementById('upload-hint');
  if (hint) hint.textContent = selectedFiles.length
    ? `${selectedFiles.length} new image${selectedFiles.length > 1 ? 's' : ''} selected`
    : 'Drag & drop or click to upload';
}

function removeImage(idx) {
  URL.revokeObjectURL(URL.createObjectURL(selectedFiles[idx]));
  selectedFiles.splice(idx, 1);
  renderPreviews();
}

window.removeImage = removeImage;

// ── Form Submit ───────────────────────────────────────────────
async function handleSubmit(e) {
  e.preventDefault();

  // Validate condition
  const condEl = document.querySelector('input[name="condition"]:checked');

  const formData = new FormData();
  formData.append('name', document.getElementById('name')?.value?.trim());
  formData.append('description', document.getElementById('description')?.value?.trim());
  formData.append('price', document.getElementById('price')?.value);
  formData.append('category', document.getElementById('category')?.value);
  formData.append('condition', condEl?.value || document.getElementById('condition')?.value || '');
  formData.append('department', document.getElementById('department')?.value?.trim());
  formData.append('pickup_location', document.getElementById('pickup_location')?.value?.trim());
  formData.append('phone', document.getElementById('phone')?.value?.trim());

  selectedFiles.forEach(f => formData.append('images', f));

  // Validate
  const errors = validateForm(formData);
  if (errors.length) {
    Toast.error(errors[0]);
    return;
  }

  const submitBtn = document.getElementById('submit-btn');
  const originalText = submitBtn.textContent;
  submitBtn.disabled = true;
  submitBtn.innerHTML = '<div class="spinner spinner-sm"></div> Uploading...';

  try {
    let r;
    if (isEditing && productId) {
      r = await API.put(`/api/products/${productId}`, formData, true);
    } else {
      r = await API.post('/api/products', formData, true);
    }

    if (r.ok) {
      Toast.success(isEditing ? 'Product updated! Awaiting approval.' : 'Product submitted for approval! 🎉');
      setTimeout(() => window.location.href = '/my-listings', 2000);
    } else {
      const errs = r.data?.errors;
      if (errs) {
        const firstErr = Object.values(errs)[0];
        Toast.error(firstErr);
        showFieldErrors(errs);
      } else {
        Toast.error(r.data?.error || 'Failed to submit product');
      }
      submitBtn.disabled = false;
      submitBtn.textContent = originalText;
    }
  } catch (err) {
    Toast.error('Network error. Please try again.');
    submitBtn.disabled = false;
    submitBtn.textContent = originalText;
  }
}

function validateForm(fd) {
  const errors = [];
  if (!fd.get('name')) errors.push('Product name is required');
  if (!fd.get('category') || fd.get('category') === '') errors.push('Please select a category');
  if (!fd.get('condition') || fd.get('condition') === '') errors.push('Please select a condition');
  if (!fd.get('price') || isNaN(parseFloat(fd.get('price')))) errors.push('Valid price is required');
  if (!fd.get('department')) errors.push('Department is required');
  return errors;
}

function showFieldErrors(errors) {
  Object.entries(errors).forEach(([field, msg]) => {
    const el = document.getElementById(field);
    if (el) {
      el.classList.add('error');
      const errEl = document.getElementById(`${field}-error`);
      if (errEl) errEl.textContent = msg;
      el.addEventListener('input', () => el.classList.remove('error'), { once: true });
    }
  });
}

document.getElementById('sell-form')?.addEventListener('submit', handleSubmit);

window.handleSubmit = handleSubmit;

/* ═══════════════════════════════════════════════════════
   profile.js – User Profile Page
   ═══════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', async () => {
  await loadProfile();
});

async function loadProfile() {
  try {
    const user = await API.get('/api/profile');
    if (user.error) {
      window.location.href = '/login';
      return;
    }
    renderProfile(user);
  } catch (e) {
    Toast.error('Failed to load profile');
  }
}

function renderProfile(user) {
  const photoEl = document.getElementById('profile-photo');
  const avatarEl = document.getElementById('profile-avatar');

  if (user.profile_photo && photoEl) {
    photoEl.src = user.profile_photo;
    photoEl.style.display = 'block';
    if (avatarEl) avatarEl.style.display = 'none';
  } else if (avatarEl) {
    avatarEl.textContent = (user.name || 'U')[0].toUpperCase();
    if (photoEl) photoEl.style.display = 'none';
  }

  setText('profile-name', user.name);
  setText('profile-email', user.email);
  setVal('profile-phone', user.phone);
  setVal('profile-department', user.department);
  setVal('profile-year', user.year);

  // Display values
  setText('display-phone', user.phone || 'Not set');
  setText('display-department', user.department || 'Not set');
  setText('display-year', user.year || 'Not set');
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val || '';
}

function setVal(id, val) {
  const el = document.getElementById(id);
  if (el) el.value = val || '';
}

function toggleEdit() {
  const form = document.getElementById('edit-form');
  const displaySection = document.getElementById('display-section');
  const editBtn = document.getElementById('edit-btn');

  if (form.style.display === 'none' || !form.style.display) {
    form.style.display = 'block';
    if (displaySection) displaySection.style.display = 'none';
    if (editBtn) editBtn.textContent = '✕ Cancel';
  } else {
    form.style.display = 'none';
    if (displaySection) displaySection.style.display = 'block';
    if (editBtn) editBtn.textContent = '✏️ Edit Profile';
  }
}

async function saveProfile(e) {
  e.preventDefault();

  const phone = document.getElementById('profile-phone')?.value?.trim();
  const department = document.getElementById('profile-department')?.value?.trim();
  const year = document.getElementById('profile-year')?.value?.trim();

  const saveBtn = document.getElementById('save-btn');
  saveBtn.disabled = true;
  saveBtn.innerHTML = '<div class="spinner spinner-sm"></div> Saving...';

  const r = await API.put('/api/profile', { phone, department, year });

  if (r.ok) {
    Toast.success('Profile updated successfully!');
    setText('display-phone', phone || 'Not set');
    setText('display-department', department || 'Not set');
    setText('display-year', year || 'Not set');
    toggleEdit();
  } else {
    Toast.error(r.data?.error || 'Failed to update profile');
  }

  saveBtn.disabled = false;
  saveBtn.textContent = '💾 Save Changes';
}

document.querySelector('#edit-form form')?.addEventListener('submit', saveProfile);

window.toggleEdit = toggleEdit;
window.saveProfile = saveProfile;

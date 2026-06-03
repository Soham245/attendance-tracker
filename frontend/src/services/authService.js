import { api, unwrap } from './api.js';

export async function login(username, password) {
  const response = await api.post('/auth/login', { username, password });
  return unwrap(response); // { access_token, token_type, expires_in, must_change_password }
}

export async function fetchCurrentUser() {
  const response = await api.get('/auth/me');
  return unwrap(response); // { id, username, email, role, must_change_password, created_at }
}

export async function changePassword({ currentPassword, newPassword, confirmPassword }) {
  const response = await api.post('/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
    confirm_password: confirmPassword,
  });
  return unwrap(response);
}

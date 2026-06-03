import { api } from './api.js';

export async function fetchUsers({ role, skip = 0, limit = 50 } = {}) {
  const params = { skip, limit };
  if (role) params.role = role;
  const { data } = await api.get('/users', { params });
  return data.data;
}

export async function createFaculty({ username, email, password }) {
  const { data } = await api.post('/users/faculty', { username, email, password });
  return data.data;
}

export async function updateFaculty(userId, { username, email, password }) {
  const body = {};
  if (username !== undefined) body.username = username;
  if (email !== undefined) body.email = email;
  if (password !== undefined && password !== '') body.password = password;
  const { data } = await api.patch(`/users/${userId}`, body);
  return data.data;
}

export async function toggleUserActive(userId, active) {
  const { data } = await api.patch(`/users/${userId}/active`, { active });
  return data.data;
}

export async function deleteFaculty(userId) {
  const { data } = await api.delete(`/users/${userId}`);
  return data;
}

export async function resetFacultyPassword(userId, newPassword) {
  const { data } = await api.post(`/users/${userId}/reset-password`, {
    new_password: newPassword,
  });
  return data.data;
}

export async function fetchFacultyClasses(userId) {
  const { data } = await api.get(`/users/${userId}/classes`);
  return data.data;
}

export async function updateFacultyClasses(userId, classIds) {
  const { data } = await api.put(`/users/${userId}/classes`, { class_ids: classIds });
  return data.data;
}

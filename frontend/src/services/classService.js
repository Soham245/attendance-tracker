import { api, unwrap } from './api.js';

export async function fetchClasses({ activeOnly = false } = {}) {
  const params = {};
  if (activeOnly) params.active_only = true;
  const response = await api.get('/classes', { params });
  return unwrap(response);
}

export async function fetchClass(classId) {
  const response = await api.get(`/classes/${classId}`);
  return unwrap(response);
}

export async function createClass(data) {
  const response = await api.post('/classes', data);
  return unwrap(response);
}

export async function updateClass(classId, data) {
  const response = await api.patch(`/classes/${classId}`, data);
  return unwrap(response);
}

export async function deleteClass(classId) {
  const response = await api.delete(`/classes/${classId}`);
  return unwrap(response);
}

export async function fetchClassFaculty(classId) {
  const response = await api.get(`/classes/${classId}/faculty`);
  return unwrap(response);
}

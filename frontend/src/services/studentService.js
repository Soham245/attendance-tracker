import { api, unwrap } from './api.js';

export async function listStudents({ skip = 0, limit = 50, classId, status } = {}) {
  const params = { skip, limit };
  if (classId) params.class_id = classId;
  if (status) params.status = status;
  const response = await api.get('/students', { params });
  return unwrap(response); // { items, total }
}

export async function getStudent(id) {
  const response = await api.get(`/students/${id}`);
  return unwrap(response);
}

export async function createStudent(payload) {
  const response = await api.post('/students', payload);
  return unwrap(response);
}

export async function updateStudent(id, payload) {
  const response = await api.patch(`/students/${id}`, payload);
  return unwrap(response);
}

export async function deleteStudent(id) {
  const response = await api.delete(`/students/${id}`);
  return unwrap(response);
}

export async function bulkDeleteStudents(ids) {
  const response = await api.post('/students/bulk-delete', { ids });
  return unwrap(response);
}

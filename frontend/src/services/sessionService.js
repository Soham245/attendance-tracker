import { api, unwrap } from './api.js';

export async function fetchSessionStatus() {
  const response = await api.get('/session/status');
  return unwrap(response);
}

export async function startSession({ classId, sessionName } = {}) {
  const body = { class_id: classId };
  if (sessionName) body.session_name = sessionName;
  const response = await api.post('/session/start', body);
  return unwrap(response);
}

export async function stopSession() {
  const response = await api.post('/session/stop');
  return unwrap(response);
}

export async function fetchSessions({ classId, facultyId, dateFrom, dateTo, skip = 0, limit = 50 } = {}) {
  const params = { skip, limit };
  if (classId) params.class_id = classId;
  if (facultyId) params.faculty_id = facultyId;
  if (dateFrom) params.date_from = dateFrom;
  if (dateTo) params.date_to = dateTo;
  const response = await api.get('/sessions', { params });
  return unwrap(response);
}

export async function fetchSession(sessionId) {
  const response = await api.get(`/sessions/${sessionId}`);
  return unwrap(response);
}

export async function deleteSession(sessionId) {
  const response = await api.delete(`/sessions/${sessionId}`);
  return unwrap(response);
}

export async function bulkDeleteSessions(ids) {
  const response = await api.post('/sessions/bulk-delete', { ids });
  return unwrap(response);
}

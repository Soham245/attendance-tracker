import { api, unwrap } from './api.js';

/**
 * GET /attendance — paginated history, optionally filtered by student/date.
 * `on_date` should be a YYYY-MM-DD string; FastAPI parses it into a `date`.
 */
export async function listAttendance({
  studentId,
  classId,
  onDate,
  skip = 0,
  limit = 50,
} = {}) {
  const params = { skip, limit };
  if (studentId != null && studentId !== '') params.student_id = studentId;
  if (classId != null) params.class_id = classId;
  if (onDate) params.on_date = onDate;
  const response = await api.get('/attendance', { params });
  return unwrap(response); // { items, total }
}

export async function getAttendance(id) {
  const response = await api.get(`/attendance/${id}`);
  return unwrap(response);
}

export async function deleteAttendance(id) {
  const response = await api.delete(`/attendance/${id}`);
  return unwrap(response);
}

export async function bulkDeleteAttendance(ids) {
  const response = await api.post('/attendance/bulk-delete', { ids });
  return unwrap(response);
}

export async function listStudentAttendance(studentId, { onDate, skip = 0, limit = 50 } = {}) {
  const params = { skip, limit };
  if (onDate) params.on_date = onDate;
  const response = await api.get(`/attendance/students/${studentId}`, { params });
  return unwrap(response);
}

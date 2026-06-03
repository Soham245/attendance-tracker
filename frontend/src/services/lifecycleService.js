import { api, unwrap } from './api.js';

/**
 * POST /lifecycle/students/:id/graduate
 */
export async function graduateStudent(studentId) {
  const response = await api.post(`/lifecycle/students/${studentId}/graduate`);
  return unwrap(response);
}

/**
 * POST /lifecycle/students/:id/deactivate
 */
export async function deactivateStudent(studentId) {
  const response = await api.post(`/lifecycle/students/${studentId}/deactivate`);
  return unwrap(response);
}

/**
 * POST /lifecycle/students/:id/restore
 */
export async function restoreStudent(studentId, targetClassId) {
  const response = await api.post(`/lifecycle/students/${studentId}/restore`, {
    target_class_id: targetClassId,
  });
  return unwrap(response);
}

/**
 * POST /lifecycle/classes/:classId/promote
 * target_class_id is optional — omit for auto-resolution.
 */
export async function promoteClass(classId, targetClassId) {
  const body = {};
  if (targetClassId != null) body.target_class_id = targetClassId;
  const response = await api.post(`/lifecycle/classes/${classId}/promote`, body);
  return unwrap(response);
}

/**
 * POST /lifecycle/classes/:classId/graduate
 */
export async function graduateClass(classId) {
  const response = await api.post(`/lifecycle/classes/${classId}/graduate`);
  return unwrap(response);
}

/**
 * POST /lifecycle/batches/:batchId/restore
 */
export async function restoreBatch(batchId, targetClassId) {
  const response = await api.post(`/lifecycle/batches/${batchId}/restore`, {
    target_class_id: targetClassId,
  });
  return unwrap(response);
}

/**
 * GET /lifecycle/programs
 */
export async function fetchPrograms() {
  const response = await api.get('/lifecycle/programs');
  return unwrap(response);
}

/**
 * GET /lifecycle/promotion/preview
 */
export async function fetchPromotionPreview({ classId, major } = {}) {
  const params = {};
  if (classId != null) params.class_id = classId;
  if (major != null) params.major = major;
  const response = await api.get('/lifecycle/promotion/preview', { params });
  return unwrap(response);
}

/**
 * POST /lifecycle/promotion/execute
 */
export async function executePromotion(classIds) {
  const response = await api.post('/lifecycle/promotion/execute', {
    class_ids: classIds,
  });
  return unwrap(response);
}

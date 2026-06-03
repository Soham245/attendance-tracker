import { api, unwrap } from './api.js';

/**
 * Capture runtime API surface. Backend lives at /capture/* and returns the
 * standardized envelope. Status shape (CaptureStatus):
 *   { state, student_id, samples_collected, target_samples, camera_active,
 *     started_at, stopped_at, last_error, last_sample_filename,
 *     dataset_image_count }
 */

export async function startCapture({ studentId, replace = false } = {}) {
  const response = await api.post('/capture/start', {
    student_id: studentId,
    replace,
  });
  return unwrap(response);
}

export async function stopCapture() {
  const response = await api.post('/capture/stop');
  return unwrap(response);
}

export async function fetchCaptureStatus() {
  const response = await api.get('/capture/status');
  return unwrap(response);
}

export const CAPTURE_TERMINAL_STATES = new Set(['idle', 'completed', 'failed']);
export const CAPTURE_ACTIVE_STATES = new Set(['starting', 'capturing', 'stopping']);

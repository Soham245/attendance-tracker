import { api, unwrap } from './api.js';

export async function fetchTrainingStatus() {
  const response = await api.get('/training/status');
  return unwrap(response);
}

export async function runTraining() {
  const response = await api.post('/training/run');
  return unwrap(response);
}

export async function fetchActiveModel() {
  try {
    const response = await api.get('/training/model');
    return unwrap(response);
  } catch (err) {
    // 404 = no active model yet; treat as a normal empty state, not an error.
    if (err?.response?.status === 404) return null;
    throw err;
  }
}

export async function fetchModelVersions() {
  const response = await api.get('/training/versions');
  return unwrap(response);
}

export async function rollbackModel(versionId) {
  const response = await api.post(`/training/rollback/${versionId}`);
  return unwrap(response);
}

export async function deleteModelVersion(versionId) {
  const response = await api.delete(`/training/versions/${versionId}`);
  return unwrap(response);
}

export async function dropAllModels() {
  const response = await api.delete('/training/versions');
  return response.data;
}

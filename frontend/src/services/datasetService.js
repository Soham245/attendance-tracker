import { api, unwrap } from './api.js';

export async function listDatasetImages(studentId) {
  const response = await api.get(`/students/${studentId}/dataset/images`);
  return unwrap(response); // { student_id, image_count, images: [{filename, size_bytes}] }
}

export async function uploadDatasetImage(studentId, file, { onProgress } = {}) {
  const form = new FormData();
  form.append('file', file);
  const response = await api.post(
    `/students/${studentId}/dataset/images`,
    form,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (evt) => {
        if (!onProgress || !evt.total) return;
        onProgress(Math.round((evt.loaded * 100) / evt.total));
      },
      // Image uploads can take longer than the default JSON window.
      timeout: 60000,
    },
  );
  return unwrap(response);
}

export async function deleteDatasetImage(studentId, filename) {
  const response = await api.delete(
    `/students/${studentId}/dataset/images/${encodeURIComponent(filename)}`,
  );
  return unwrap(response);
}

export async function deleteAllDatasetImages(studentId) {
  const response = await api.delete(`/students/${studentId}/dataset/images`);
  return unwrap(response);
}

import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';
const TOKEN_KEY = 'attendai.token';

export const tokenStore = {
  get() {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set(token) {
    try {
      if (token) localStorage.setItem(TOKEN_KEY, token);
      else localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* storage unavailable (private mode etc.) — fall through */
    }
  },
  clear() {
    this.set(null);
  },
};

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// Attach bearer token on every request.
api.interceptors.request.use((config) => {
  const token = tokenStore.get();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Unwrap the standardized `{success, message, data}` envelope and surface
// auth failures through a single global listener (registered by AuthContext).
const unauthorizedListeners = new Set();
export function onUnauthorized(listener) {
  unauthorizedListeners.add(listener);
  return () => unauthorizedListeners.delete(listener);
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      tokenStore.clear();
      unauthorizedListeners.forEach((fn) => {
        try {
          fn();
        } catch {
          /* keep other listeners running */
        }
      });
    }
    return Promise.reject(error);
  },
);

/** Pull `data` out of the backend's APIResponse envelope. */
export function unwrap(response) {
  return response?.data?.data ?? null;
}

/** Normalize an axios error into a human-friendly message. */
export function errorMessage(error, fallback = 'Something went wrong') {
  const payload = error?.response?.data;
  if (payload?.message) return payload.message;
  if (payload?.errors?.[0]?.message) return payload.errors[0].message;
  if (error?.message) return error.message;
  return fallback;
}

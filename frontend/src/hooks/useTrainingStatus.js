import { useCallback } from 'react';
import { fetchTrainingStatus } from '../services/trainingService.js';
import { usePolling } from './usePolling.js';

/**
 * Polls /training/status. Defaults to 4s — fast enough that "running -> completed"
 * transitions feel responsive without hammering the backend during long idles.
 */
export function useTrainingStatus({ intervalMs = 4000, enabled = true } = {}) {
  const fetcher = useCallback(() => fetchTrainingStatus(), []);
  return usePolling(fetcher, { intervalMs, enabled });
}

import { useCallback, useMemo } from 'react';
import { fetchCaptureStatus, CAPTURE_ACTIVE_STATES } from '../services/captureService.js';
import { usePolling } from './usePolling.js';

/**
 * Capture-runtime poller. Cadence shifts with the runtime state:
 *   - capturing: tight (1s) so the progress bar feels responsive
 *   - starting/stopping: medium (1.5s) — transitional, brief
 *   - idle/completed/failed: slow (3s) — nothing meaningful changing
 *
 * `enabled` is typically wired to "modal is open" so polling stops as soon
 * as the operator dismisses the dialog. Visibility/pause-on-hidden is
 * handled by the underlying usePolling.
 */
export function useCaptureStatus({ enabled = true } = {}) {
  const fetcher = useCallback(() => fetchCaptureStatus(), []);

  // First-pass cadence: usePolling captures the interval on enable, so the
  // hook re-mounts the interval whenever this value changes — see how it
  // depends on `intervalMs` in usePolling's effect deps.
  const intervalMs = useMemo(() => 1000, []);

  const { data, error, loading, refresh } = usePolling(fetcher, {
    intervalMs,
    enabled,
  });

  return { data, error, loading, refresh };
}

/**
 * Helper so callers can ask "should I keep polling?" without re-deriving the
 * predicate everywhere.
 */
export function isCaptureActive(status) {
  if (!status) return false;
  return CAPTURE_ACTIVE_STATES.has(status.state);
}

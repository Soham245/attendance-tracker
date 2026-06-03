import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchSessionStatus } from '../services/sessionService.js';
import { usePolling } from './usePolling.js';

const ACTIVE_STATES = new Set(['running', 'starting', 'stopping']);

/**
 * Polls the session status endpoint with adaptive intervals.
 *
 * - Active session (running/starting/stopping): fast poll (default 2s)
 * - Idle session: slow poll (default 30s)
 * - Boost period (after start/stop action): fast poll for a brief window
 *   so the UI catches backend state transitions that happen asynchronously
 *   after the POST returns.
 *
 * The interval switches automatically when the session state changes.
 *
 * Returns the standard usePolling result plus a `boost()` function that
 * callers should invoke after triggering a session start or stop.
 */
export function useSessionStatus({
  activeIntervalMs = 2000,
  idleIntervalMs = 30000,
  boostDurationMs = 10000,
  enabled = true,
} = {}) {
  const fetcher = useCallback(() => fetchSessionStatus(), []);

  // Track whether the session is active to pick the right interval.
  // Start with idle rate — the first poll determines the real state.
  const [isActive, setIsActive] = useState(false);

  // Temporary fast-poll window after a user action so the UI doesn't
  // stall on the 30s idle interval while the backend transitions.
  const [boosted, setBoosted] = useState(false);
  const boostTimerRef = useRef(null);

  const intervalMs = (isActive || boosted) ? activeIntervalMs : idleIntervalMs;

  const result = usePolling(fetcher, { intervalMs, enabled });

  // Update the active flag whenever data changes.
  const prevStateRef = useRef(null);
  const currentState = result.data?.session_state;
  if (currentState !== prevStateRef.current) {
    prevStateRef.current = currentState;
    const nowActive = ACTIVE_STATES.has(currentState);
    if (nowActive !== isActive) {
      setIsActive(nowActive);
    }
  }

  // Cancel boost early once the adaptive flag takes over — no point
  // keeping the timer running when isActive already forces fast polling.
  useEffect(() => {
    if (isActive && boosted) {
      clearTimeout(boostTimerRef.current);
      setBoosted(false);
    }
  }, [isActive, boosted]);

  // Cleanup on unmount.
  useEffect(() => () => clearTimeout(boostTimerRef.current), []);

  /**
   * Temporarily switch to fast polling. Call this after triggering a
   * session start or stop so the UI picks up the backend transition
   * within 1-2 seconds instead of waiting for the next idle poll.
   */
  const boost = useCallback(() => {
    setBoosted(true);
    clearTimeout(boostTimerRef.current);
    boostTimerRef.current = setTimeout(() => setBoosted(false), boostDurationMs);
  }, [boostDurationMs]);

  return { ...result, boost };
}

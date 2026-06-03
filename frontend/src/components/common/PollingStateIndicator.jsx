import { RefreshCw } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { cn } from '../../utils/cn.js';

/**
 * Lightweight indicator that mirrors the state of a polling hook:
 *   - error: shows "Disconnected" (rose)
 *   - loading: shows "Refreshing" with spinning icon
 *   - otherwise: "Live"
 *
 * `loading` is gated by a short delay so sub-second polls don't flicker the
 * label between "Live" and "Refreshing" on every tick. Slow requests still
 * surface — the spinner only appears once the request crosses the threshold.
 */
const REFRESH_VISIBLE_AFTER_MS = 250;

export default function PollingStateIndicator({
  loading,
  error,
  label,
  className,
}) {
  const showLoading = useDelayedFlag(loading, REFRESH_VISIBLE_AFTER_MS);

  const tone = error
    ? 'text-rose-300'
    : showLoading
      ? 'text-zinc-200'
      : 'text-zinc-500';

  return (
    <div
      className={cn('flex items-center gap-1.5 text-xs', tone, className)}
      title={
        error
          ? 'Last poll failed'
          : showLoading
            ? 'Refreshing'
            : 'Polling active'
      }
    >
      <RefreshCw
        size={12}
        className={cn('opacity-70', showLoading && 'animate-spin opacity-100')}
      />
      {label ?? (error ? 'Disconnected' : showLoading ? 'Refreshing' : 'Live')}
    </div>
  );
}

/**
 * Returns true only when `flag` has been true continuously for at least
 * `delayMs`. Transitions to false immediately. Prevents fast-flickering
 * boolean state (polling loads) from causing visible UI chatter.
 */
function useDelayedFlag(flag, delayMs) {
  const [delayed, setDelayed] = useState(false);
  const timerRef = useRef(null);

  useEffect(() => {
    if (flag) {
      if (timerRef.current) return undefined;
      timerRef.current = window.setTimeout(() => {
        setDelayed(true);
        timerRef.current = null;
      }, delayMs);
      return () => {
        if (timerRef.current) {
          window.clearTimeout(timerRef.current);
          timerRef.current = null;
        }
      };
    }
    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    setDelayed(false);
    return undefined;
  }, [flag, delayMs]);

  return delayed;
}

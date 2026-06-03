import { AlertTriangle, WifiOff } from 'lucide-react';
import { useDebouncedValue } from '../../hooks/useDebouncedValue.js';
import { cn } from '../../utils/cn.js';

/**
 * Persistent connectivity banner that only fires after the poll has been
 * failing for a beat — prevents a single hiccup from flashing a scary banner.
 * Designed to sit at the top of a page or pinned just under the header.
 */
export default function ConnectionStatusBanner({
  error,
  hasData,
  retryDelayMs = 1500,
  className,
}) {
  // Treat "transient" errors during normal polling differently from "we've
  // never been able to reach the backend." Both surface, but with softer
  // wording so the operator can tell them apart at a glance.
  const stableError = useDebouncedValue(Boolean(error), retryDelayMs);
  if (!stableError) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        'flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200',
        className,
      )}
    >
      {hasData ? (
        <>
          <AlertTriangle size={14} className="shrink-0" />
          <span>
            Reconnecting to the runtime… displaying the last known state.
          </span>
        </>
      ) : (
        <>
          <WifiOff size={14} className="shrink-0" />
          <span>Offline — cannot reach the runtime.</span>
        </>
      )}
    </div>
  );
}

import { useEffect, useState } from 'react';
import { cn } from '../../utils/cn.js';

/**
 * Tiny "just refreshed" pulse for runtime panels. Mirrors a polling hook's
 * `loading` flag — flashes only on the *trailing edge* of a successful poll
 * so users perceive freshness without a perpetual spinner.
 */
export default function RefreshIndicator({ loading, error, className }) {
  const [pulse, setPulse] = useState(false);
  const [wasLoading, setWasLoading] = useState(false);

  useEffect(() => {
    if (loading) {
      setWasLoading(true);
      return undefined;
    }
    if (wasLoading) {
      setWasLoading(false);
      if (error) return undefined;
      setPulse(true);
      const t = window.setTimeout(() => setPulse(false), 700);
      return () => window.clearTimeout(t);
    }
    return undefined;
  }, [loading, wasLoading, error]);

  const tone = error
    ? 'bg-rose-400'
    : pulse
      ? 'bg-emerald-400'
      : 'bg-zinc-600';

  return (
    <span
      className={cn(
        'inline-block h-1.5 w-1.5 rounded-full transition-colors duration-300',
        tone,
        className,
      )}
      title={
        error
          ? 'Last refresh failed'
          : pulse
            ? 'Just refreshed'
            : 'Polling'
      }
    />
  );
}

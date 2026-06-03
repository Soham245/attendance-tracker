import { useEffect, useState } from 'react';

/**
 * Returns `value` after it has remained unchanged for `delay` ms. Useful for
 * gating UI transitions on flappy state (e.g. brief network blips) without
 * losing the ability to react to a sustained change.
 */
export function useDebouncedValue(value, delay = 300) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

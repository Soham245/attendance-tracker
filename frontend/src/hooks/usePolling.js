import { useEffect, useRef, useState } from 'react';

/**
 * Polls `fetcher` every `intervalMs` while the document is visible.
 *
 * Key behaviours:
 *   - `loading` is only true during the **initial** fetch. Subsequent polls
 *     update data silently so the UI never flashes a skeleton after mount.
 *   - Data is compared (shallow JSON equality) before calling `setData` so
 *     consumers don't re-render when the response hasn't changed.
 *   - Skips ticks when the tab is hidden; runs an immediate tick on focus.
 *   - Cleans up on unmount.
 *
 * Returns { data, error, loading, refresh }.
 */
export function usePolling(fetcher, { intervalMs = 3000, enabled = true } = {}) {
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true); // true until first response

  const tickIdRef = useRef(0);
  const hasFetchedRef = useRef(false);
  const lastJsonRef = useRef(null);

  useEffect(() => {
    if (!enabled) return undefined;

    let cancelled = false;
    let timer = null;
    hasFetchedRef.current = false;
    lastJsonRef.current = null;

    const tick = async () => {
      if (cancelled) return;
      if (typeof document !== 'undefined' && document.hidden) return;

      const id = ++tickIdRef.current;
      const isInitial = !hasFetchedRef.current;

      // Only show loading state for the very first fetch.
      if (isInitial) setLoading(true);

      try {
        const result = await fetcherRef.current();
        if (cancelled || id !== tickIdRef.current) return;

        hasFetchedRef.current = true;

        // Skip state update if data hasn't changed.
        const json = JSON.stringify(result);
        if (json !== lastJsonRef.current) {
          lastJsonRef.current = json;
          setData(result);
        }
        setError(null);
      } catch (err) {
        if (cancelled || id !== tickIdRef.current) return;
        hasFetchedRef.current = true;
        setError(err);
      } finally {
        if (!cancelled && id === tickIdRef.current) {
          setLoading(false);
        }
      }
    };

    tick();
    timer = window.setInterval(tick, intervalMs);

    const onVisibility = () => {
      if (!document.hidden) tick();
    };
    document.addEventListener('visibilitychange', onVisibility);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [intervalMs, enabled]);

  const refresh = () => {
    tickIdRef.current++;
    fetcherRef.current()
      .then((result) => {
        const json = JSON.stringify(result);
        if (json !== lastJsonRef.current) {
          lastJsonRef.current = json;
          setData(result);
        }
        setError(null);
      })
      .catch(setError);
  };

  return { data, error, loading, refresh };
}

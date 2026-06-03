import { useEffect } from 'react';

/**
 * Tiny keyboard shortcut helper. Matches a key + modifier set against the
 * browser KeyboardEvent. Skips when focus is inside an editable element so
 * Cmd+R inside an input doesn't hijack typing.
 *
 *   useHotkey('r', refresh, { meta: true })   // ⌘R / Ctrl+R
 *   useHotkey('Escape', closeModal)
 */
export function useHotkey(key, handler, { meta = false, alt = false, shift = false, enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return undefined;

    const onKey = (e) => {
      // `e.key` can be undefined for some synthetic browser events
      // (autofill, IME composition, certain media keys). Guard the read.
      if (typeof e.key !== 'string') return;
      if (e.key.toLowerCase() !== key.toLowerCase()) return;
      // Treat meta and ctrl interchangeably — desktop users press whichever
      // their OS conditions them to.
      if (meta && !(e.metaKey || e.ctrlKey)) return;
      if (!meta && (e.metaKey || e.ctrlKey)) return;
      if (alt !== e.altKey) return;
      if (shift !== e.shiftKey) return;

      const target = e.target;
      if (target instanceof HTMLElement) {
        const tag = target.tagName;
        if (
          tag === 'INPUT' ||
          tag === 'TEXTAREA' ||
          tag === 'SELECT' ||
          target.isContentEditable
        ) {
          return;
        }
      }

      handler(e);
    };

    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [key, handler, meta, alt, shift, enabled]);
}

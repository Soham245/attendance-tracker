import { useCallback, useMemo, useState } from 'react';

/**
 * Manages a set of selected row IDs for bulk operations.
 *
 * Usage:
 *   const sel = useSelection(rows, (r) => r.id);
 *   <input checked={sel.isSelected(id)} onChange={() => sel.toggle(id)} />
 *   <input checked={sel.allSelected} onChange={sel.toggleAll} />
 */
export function useSelection(rows, keyFn) {
  const [selected, setSelected] = useState(new Set());

  const ids = useMemo(() => rows.map(keyFn), [rows, keyFn]);

  const isSelected = useCallback((id) => selected.has(id), [selected]);

  const toggle = useCallback((id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const allSelected = ids.length > 0 && ids.every((id) => selected.has(id));
  const someSelected = ids.some((id) => selected.has(id));

  const toggleAll = useCallback(() => {
    if (allSelected) {
      setSelected(new Set());
    } else {
      setSelected(new Set(ids));
    }
  }, [allSelected, ids]);

  const clear = useCallback(() => setSelected(new Set()), []);

  /** IDs that are currently selected AND still present in `rows`. */
  const selectedIds = useMemo(
    () => ids.filter((id) => selected.has(id)),
    [ids, selected],
  );

  return {
    selected,
    selectedIds,
    count: selectedIds.length,
    isSelected,
    toggle,
    toggleAll,
    allSelected,
    someSelected,
    clear,
  };
}

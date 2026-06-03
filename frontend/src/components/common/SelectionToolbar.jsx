import { Trash2, X } from 'lucide-react';

/**
 * Floating toolbar that appears when rows are selected.
 * Shows selection count + bulk-delete button.
 */
export default function SelectionToolbar({ count, onDelete, onClear, loading }) {
  if (count === 0) return null;

  return (
    <div className="flex items-center gap-3 rounded-lg border border-surface-border bg-surface-panel px-4 py-2 mb-4 shadow-md">
      <span className="text-sm text-zinc-200 tabular-nums font-medium">
        {count} selected
      </span>

      <div className="ml-auto flex items-center gap-2">
        <button
          type="button"
          onClick={onDelete}
          disabled={loading}
          className="inline-flex items-center gap-1.5 rounded-md bg-rose-600 hover:bg-rose-500 disabled:opacity-50 px-3 py-1.5 text-xs font-medium text-white transition-colors"
        >
          <Trash2 size={13} />
          Delete
        </button>
        <button
          type="button"
          onClick={onClear}
          disabled={loading}
          className="p-1.5 rounded-md text-zinc-400 hover:text-zinc-100 hover:bg-surface-hover transition-colors"
          title="Clear selection"
        >
          <X size={14} />
        </button>
      </div>
    </div>
  );
}

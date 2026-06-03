import { cn } from '../../utils/cn.js';
import SkeletonTable from './SkeletonTable.jsx';

/**
 * Lightweight data table. Columns:
 *   { key, header, render?(row), className?, headerClassName?, width? }
 *
 * `rowKey` is required so rows are stable across re-renders. The table
 * intentionally stays unopinionated about pagination — callers compose that.
 *
 * Selection support (optional):
 *   Pass a `selection` object from `useSelection` to render a leading
 *   checkbox column with select-all in the header.
 */
export default function DataTable({
  columns,
  data = [],
  rowKey,
  loading = false,
  empty,
  onRowClick,
  className,
  bare = false,
  selection,
}) {
  const showCheckbox = Boolean(selection);
  const totalCols = columns.length + (showCheckbox ? 1 : 0);

  return (
    <div
      className={cn(
        bare ? 'overflow-hidden' : 'card overflow-hidden',
        className,
      )}
    >
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-surface-border bg-surface-raised/40">
              {showCheckbox ? (
                <th scope="col" style={{ width: '44px' }} className="px-3 py-3 text-center align-middle">
                  <div className="flex items-center justify-center">
                    <input
                      type="checkbox"
                      checked={selection.allSelected}
                      ref={(el) => {
                        if (el) el.indeterminate = selection.someSelected && !selection.allSelected;
                      }}
                      onChange={selection.toggleAll}
                      className="accent-accent h-3.5 w-3.5 cursor-pointer"
                    />
                  </div>
                </th>
              ) : null}
              {columns.map((col) => (
                <th
                  key={col.key}
                  scope="col"
                  style={col.width ? { width: col.width } : undefined}
                  className={cn(
                    'px-4 py-3 text-left text-[11px] font-medium uppercase tracking-wider text-zinc-500',
                    col.headerClassName,
                  )}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && data.length === 0 ? (
              <SkeletonTable rows={6} columns={totalCols} />
            ) : data.length === 0 ? (
              <tr>
                <td colSpan={totalCols}>{empty}</td>
              </tr>
            ) : (
              data.map((row, rowIdx) => {
                const key = rowKey(row);
                const isRowSelected = showCheckbox && selection.isSelected(key);
                return (
                  <tr
                    key={key}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                    className={cn(
                      'border-b border-surface-border/60 last:border-b-0',
                      'hover:bg-surface-hover/60 transition-colors',
                      onRowClick && 'cursor-pointer',
                      isRowSelected && 'bg-accent/5',
                    )}
                  >
                    {showCheckbox ? (
                      <td className="px-3 py-3 text-center align-middle">
                        <div className="flex items-center justify-center">
                          <input
                            type="checkbox"
                            checked={isRowSelected}
                            onChange={() => selection.toggle(key)}
                            onClick={(e) => e.stopPropagation()}
                            className="accent-accent h-3.5 w-3.5 cursor-pointer"
                          />
                        </div>
                      </td>
                    ) : null}
                    {columns.map((col) => (
                      <td
                        key={col.key}
                        className={cn(
                          'px-4 py-3 text-zinc-200 align-middle',
                          col.className,
                        )}
                      >
                        {col.render ? col.render(row, col, rowIdx) : row[col.key]}
                      </td>
                    ))}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

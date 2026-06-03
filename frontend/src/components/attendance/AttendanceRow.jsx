import { Eye } from 'lucide-react';

/**
 * Action cell for an attendance row. The row's data cells are composed in
 * AttendanceTable so DataTable retains layout control.
 */
export default function AttendanceRow({ record, onView }) {
  return (
    <div className="flex items-center justify-end gap-1">
      <button
        type="button"
        onClick={() => onView(record)}
        className="p-1.5 rounded-md text-zinc-400 hover:text-zinc-100 hover:bg-surface-hover transition-colors"
        title="View details"
      >
        <Eye size={15} />
      </button>
    </div>
  );
}

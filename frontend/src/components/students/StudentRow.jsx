import { Camera, GraduationCap, Pencil, RotateCcw, Users, UserMinus } from 'lucide-react';

/**
 * Action cell for a single student row. Rendered inside the DataTable's
 * trailing column. Visibility of mutating actions follows `canMutate`.
 *
 * Lifecycle actions (graduate, deactivate, restore) only appear for admin
 * and are contextual based on current student status.
 */
export default function StudentRow({
  student,
  onEdit,
  onManageDataset,
  onGraduate,
  onDeactivate,
  onRestore,
  onBatchRestore,
  canMutate,
}) {
  const isActive = !student.status || student.status === 'active';
  const isGraduated = student.status === 'graduated';
  const isInactive = student.status === 'inactive';

  return (
    <div className="flex items-center justify-end gap-1">
      <IconButton
        title="Manage dataset"
        onClick={() => onManageDataset(student)}
        icon={Camera}
      />
      {canMutate ? (
        <>
          <IconButton
            title="Edit student"
            onClick={() => onEdit(student)}
            icon={Pencil}
          />
          {isActive && onGraduate ? (
            <IconButton
              title="Graduate student"
              onClick={() => onGraduate(student)}
              icon={GraduationCap}
            />
          ) : null}
          {isActive && onDeactivate ? (
            <IconButton
              title="Deactivate student"
              onClick={() => onDeactivate(student)}
              icon={UserMinus}
              danger
            />
          ) : null}
          {(isGraduated || isInactive) && onRestore ? (
            <IconButton
              title="Restore student"
              onClick={() => onRestore(student)}
              icon={RotateCcw}
              accent
            />
          ) : null}
          {(isGraduated || isInactive) && student.lifecycle_batch_id && onBatchRestore ? (
            <IconButton
              title="Restore entire batch"
              onClick={() => onBatchRestore(student.lifecycle_batch_id)}
              icon={Users}
              accent
            />
          ) : null}
        </>
      ) : null}
    </div>
  );
}

function IconButton({ icon: Icon, danger, accent, ...props }) {
  let cls = 'text-zinc-400 hover:text-zinc-100 hover:bg-surface-hover';
  if (danger) cls = 'text-zinc-400 hover:text-rose-300 hover:bg-rose-500/10';
  if (accent) cls = 'text-zinc-400 hover:text-accent hover:bg-accent/10';
  return (
    <button
      type="button"
      className={'p-1.5 rounded-md transition-colors ' + cls}
      {...props}
    >
      <Icon size={15} />
    </button>
  );
}

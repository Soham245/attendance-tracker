import DataTable from '../common/DataTable.jsx';
import StudentRow from './StudentRow.jsx';
import StudentEmptyState from './StudentEmptyState.jsx';

export default function StudentsTable({
  students,
  loading,
  filtered,
  canMutate,
  onCreate,
  onEdit,
  onManageDataset,
  onGraduate,
  onDeactivate,
  onRestore,
  onBatchRestore,
  selection,
}) {
  const columns = [
    {
      key: 'name',
      header: 'Student',
      render: (s) => (
        <>
          <div className="text-sm font-medium text-zinc-100">{s.name}</div>
          {s.email ? (
            <div className="text-xs text-zinc-500">{s.email}</div>
          ) : null}
        </>
      ),
    },
    {
      key: 'roll',
      header: 'Roll',
      width: '140px',
      render: (s) => (
        <span className="font-mono text-xs text-zinc-300">{s.roll_number}</span>
      ),
    },
    {
      key: 'department',
      header: 'Department',
      render: (s) => (
        <span className="text-sm text-zinc-300">{s.department || '—'}</span>
      ),
    },
    {
      key: 'class',
      header: 'Class',
      width: '140px',
      render: (s) => {
        const code = s.class_code || s.last_class_code;
        return (
          <span className="font-mono text-xs text-zinc-300">
            {code || <span className="text-zinc-600">—</span>}
          </span>
        );
      },
    },
    {
      key: 'lifecycle',
      header: 'Status',
      width: '120px',
      render: (s) => <StudentStatusBadge status={s.status} />,
    },
    {
      key: 'dataset',
      header: 'Dataset',
      width: '160px',
      render: (s) =>
        s.training_required ? (
          <Pill tone="amber">Training required</Pill>
        ) : (
          <Pill tone="emerald">Trained</Pill>
        ),
    },
    {
      key: 'actions',
      header: '',
      width: '140px',
      headerClassName: 'text-right',
      className: 'text-right',
      render: (s) => (
        <StudentRow
          student={s}
          canMutate={canMutate}
          onEdit={onEdit}
          onManageDataset={onManageDataset}
          onGraduate={onGraduate}
          onDeactivate={onDeactivate}
          onRestore={onRestore}
          onBatchRestore={onBatchRestore}
        />
      ),
    },
  ];

  return (
    <DataTable
      columns={columns}
      data={students}
      rowKey={(s) => s.id}
      loading={loading}
      selection={selection}
      empty={
        <StudentEmptyState
          filtered={filtered}
          onCreate={onCreate}
          canCreate={canMutate}
        />
      }
    />
  );
}

const STATUS_STYLES = {
  active: 'bg-emerald-500/15 text-emerald-400',
  graduated: 'bg-sky-500/15 text-sky-400',
  inactive: 'bg-zinc-500/15 text-zinc-400',
};

function StudentStatusBadge({ status }) {
  const label = status ? status.charAt(0).toUpperCase() + status.slice(1) : 'Active';
  return (
    <span
      className={
        'inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ' +
        (STATUS_STYLES[status] ?? STATUS_STYLES.active)
      }
    >
      {label}
    </span>
  );
}

function Pill({ tone, children }) {
  const tones = {
    amber: 'bg-amber-500/10 text-amber-200 ring-amber-500/30 [&>span]:bg-amber-400',
    emerald: 'bg-emerald-500/10 text-emerald-200 ring-emerald-500/30 [&>span]:bg-emerald-400',
  };
  return (
    <span
      className={
        'inline-flex items-center gap-1.5 rounded-full ring-1 px-2 py-0.5 text-[11px] ' +
        (tones[tone] ?? tones.emerald)
      }
    >
      <span className="h-1.5 w-1.5 rounded-full" />
      {children}
    </span>
  );
}

// Exported for potential reuse
export { StudentStatusBadge };

import DataTable from '../common/DataTable.jsx';
import AttendanceRow from './AttendanceRow.jsx';
import AttendanceEmptyState from './AttendanceEmptyState.jsx';
import { formatDateTime } from '../../utils/format.js';

export default function AttendanceTable({
  records,
  loading,
  filtered,
  onView,
  selection,
}) {
  const columns = [
    {
      key: 'student',
      header: 'Student',
      render: (r) => <StudentCell record={r} />,
    },
    {
      key: 'recognized',
      header: 'Recognised at',
      render: (r) => (
        <span className="text-sm text-zinc-200">
          {formatDateTime(r.recognized_at)}
        </span>
      ),
    },
    {
      key: 'confidence',
      header: 'Confidence',
      width: '140px',
      render: (r) => (
        <span className="font-mono text-xs text-zinc-300 tabular-nums">
          {(Number(r.confidence) * 100).toFixed(0)}%
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      width: '120px',
      render: (r) => <StatusPill status={r.status} />,
    },
    {
      key: 'actions',
      header: '',
      width: '60px',
      headerClassName: 'text-right',
      className: 'text-right',
      render: (r) => (
        <AttendanceRow
          record={r}
          onView={onView}
        />
      ),
    },
  ];

  return (
    <DataTable
      columns={columns}
      data={records}
      rowKey={(r) => r.id}
      loading={loading}
      empty={<AttendanceEmptyState filtered={filtered} />}
      selection={selection}
    />
  );
}

function StudentCell({ record }) {
  const student = record?.student;
  const name = student?.name;
  const code = student?.student_code;
  if (!name && !code) {
    // Fallback for old records / pre-enrichment rows. Keeps the UI honest
    // about identity gaps rather than silently rendering nothing.
    return (
      <span className="text-xs text-zinc-500 italic">
        Student #{record.student_id}
      </span>
    );
  }
  return (
    <div className="min-w-0">
      <div className="text-sm text-zinc-100 truncate">{name ?? '—'}</div>
      {code ? (
        <div className="text-[11px] text-zinc-500 font-mono truncate">
          {code}
        </div>
      ) : null}
    </div>
  );
}

function StatusPill({ status }) {
  const tones = {
    present: 'bg-emerald-500/10 text-emerald-200 ring-emerald-500/30 [&>span]:bg-emerald-400',
    late: 'bg-amber-500/10 text-amber-200 ring-amber-500/30 [&>span]:bg-amber-400',
    absent: 'bg-rose-500/10 text-rose-200 ring-rose-500/30 [&>span]:bg-rose-400',
  };
  const tone = tones[status] ?? 'bg-zinc-500/10 text-zinc-300 ring-zinc-500/30 [&>span]:bg-zinc-400';
  return (
    <span
      className={
        'inline-flex items-center gap-1.5 rounded-full ring-1 px-2 py-0.5 text-[11px] capitalize ' +
        tone
      }
    >
      <span className="h-1.5 w-1.5 rounded-full" />
      {status ?? '—'}
    </span>
  );
}

import BaseModal from '../common/BaseModal.jsx';
import Button from '../common/Button.jsx';
import { formatDateTime } from '../../utils/format.js';

/**
 * Read-only detail view. Justified because the table strips long fields (IDs,
 * timestamps with seconds, raw confidence) to a compact display — the modal
 * shows the full record without sending the user to a separate page.
 */
export default function AttendanceDetailModal({ open, record, onClose }) {
  return (
    <BaseModal
      open={open}
      onClose={onClose}
      title={record?.student?.name ?? (record ? 'Attendance' : 'Attendance')}
      subtitle={
        record?.student?.student_code
          ? `Roll ${record.student.student_code}`
          : record
            ? `Student #${record.student_id}`
            : undefined
      }
      size="md"
      footer={
        <Button variant="ghost" onClick={onClose}>
          Close
        </Button>
      }
    >
      {record ? (
        <dl className="grid grid-cols-3 gap-x-4 gap-y-3 text-sm">
          <Row label="Student" value={record.student?.name ?? '—'} />
          <Row
            label="Roll number"
            value={record.student?.student_code ?? '—'}
          />
          <Row label="Status" value={record.status ?? '—'} capitalize />
          <Row
            label="Recognised at"
            value={formatDateTime(record.recognized_at)}
            span={2}
          />
          <Row
            label="Confidence"
            value={`${(Number(record.confidence) * 100).toFixed(1)}%`}
          />
          <Row
            label="Persisted at"
            value={formatDateTime(record.created_at)}
            span={3}
          />
        </dl>
      ) : null}
    </BaseModal>
  );
}

function Row({ label, value, capitalize, span = 1 }) {
  const colSpan =
    span === 3 ? 'col-span-3' : span === 2 ? 'col-span-2' : 'col-span-1';
  return (
    <div className={colSpan}>
      <dt className="text-[10px] uppercase tracking-wider text-zinc-500">
        {label}
      </dt>
      <dd
        className={
          'mt-0.5 text-sm text-zinc-100 tabular-nums ' +
          (capitalize ? 'capitalize' : '')
        }
      >
        {value}
      </dd>
    </div>
  );
}

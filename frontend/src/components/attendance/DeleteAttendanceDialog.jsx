import { useEffect, useState } from 'react';
import ConfirmDialog from '../common/ConfirmDialog.jsx';
import { errorMessage } from '../../services/api.js';
import { formatDateTime } from '../../utils/format.js';

export default function DeleteAttendanceDialog({ open, record, onClose, onConfirm }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (open) {
      setLoading(false);
      setError(null);
    }
  }, [open]);

  const handleConfirm = async () => {
    if (!record) return;
    setLoading(true);
    setError(null);
    try {
      await onConfirm(record);
      onClose();
    } catch (err) {
      setError(errorMessage(err, 'Could not delete the attendance record.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <ConfirmDialog
      open={open}
      onClose={onClose}
      onConfirm={handleConfirm}
      loading={loading}
      error={error}
      tone="danger"
      title="Delete attendance record"
      confirmLabel="Delete"
      description={
        record ? (
          <p>
            Remove attendance for{' '}
            <span className="font-medium text-zinc-100">
              {record.student?.name ?? `Student #${record.student_id}`}
            </span>
            {record.student?.student_code ? (
              <>
                {' '}
                (<span className="font-mono">{record.student.student_code}</span>)
              </>
            ) : null}{' '}
            recorded at{' '}
            <span className="font-medium text-zinc-100">
              {formatDateTime(record.recognized_at)}
            </span>
            ? This cannot be undone.
          </p>
        ) : null
      }
    />
  );
}

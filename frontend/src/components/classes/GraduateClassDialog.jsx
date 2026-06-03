import { useEffect, useState } from 'react';
import ConfirmDialog from '../common/ConfirmDialog.jsx';
import { errorMessage } from '../../services/api.js';
import { listStudents } from '../../services/studentService.js';

/**
 * Confirmation dialog for graduating all active students in a class.
 *
 * Loads a student count on open so the admin sees how many students
 * will be affected before confirming.
 */
export default function GraduateClassDialog({
  open,
  cls,
  onClose,
  onConfirm,
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [studentCount, setStudentCount] = useState(null);
  const [countLoading, setCountLoading] = useState(false);

  // Fetch the active student count when the dialog opens.
  useEffect(() => {
    if (!open || !cls) {
      setStudentCount(null);
      return;
    }

    let cancelled = false;
    setCountLoading(true);
    listStudents({ classId: cls.id, status: 'active', limit: 1 })
      .then((result) => {
        if (!cancelled) setStudentCount(result?.total ?? 0);
      })
      .catch(() => {
        if (!cancelled) setStudentCount(null);
      })
      .finally(() => {
        if (!cancelled) setCountLoading(false);
      });

    return () => { cancelled = true; };
  }, [open, cls?.id]);

  const handleConfirm = async () => {
    if (!cls) return;
    setLoading(true);
    setError(null);
    try {
      await onConfirm(cls);
      onClose();
    } catch (err) {
      setError(errorMessage(err, 'Graduation failed'));
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (!loading) {
      setError(null);
      onClose();
    }
  };

  const countText = countLoading
    ? 'Loading...'
    : studentCount != null
      ? `${studentCount} active student${studentCount !== 1 ? 's' : ''}`
      : 'unknown number of students';

  return (
    <ConfirmDialog
      open={open}
      onClose={handleClose}
      onConfirm={handleConfirm}
      title="Graduate entire class"
      confirmLabel="Graduate all"
      tone="warning"
      loading={loading}
      error={error}
      description={
        cls ? (
          <div className="space-y-2">
            <p>
              Graduate all active students in{' '}
              <span className="font-mono font-medium text-zinc-100">
                {cls.class_code}
              </span>
              ?
            </p>
            <p className="text-xs text-zinc-400">
              This will affect <span className="font-medium text-zinc-200">{countText}</span>.
              All students will be removed from the active roster and will no
              longer be recognized during attendance sessions.
            </p>
            <p className="text-xs text-zinc-500">
              Attendance history is preserved. A batch ID will be created so
              this operation can be undone via batch restore.
            </p>
          </div>
        ) : null
      }
    />
  );
}

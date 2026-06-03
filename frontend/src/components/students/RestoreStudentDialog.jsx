import { useState } from 'react';
import BaseModal from '../common/BaseModal.jsx';
import Button from '../common/Button.jsx';
import LoadingButton from '../common/LoadingButton.jsx';
import { errorMessage } from '../../services/api.js';
import { useClassContext } from '../../context/ClassContext.jsx';

/**
 * Restore dialog with target class selection.
 *
 * The admin must choose which class to re-enroll the student in.
 * Pre-selects the active class from context if available.
 */
export default function RestoreStudentDialog({
  open,
  student,
  onClose,
  onConfirm,
}) {
  const { classes, activeClass } = useClassContext();
  const [targetClassId, setTargetClassId] = useState(
    activeClass ? activeClass.class_id : '',
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleConfirm = async () => {
    if (!targetClassId) return;
    setLoading(true);
    setError(null);
    try {
      await onConfirm(student, Number(targetClassId));
      setError(null);
      onClose();
    } catch (err) {
      setError(errorMessage(err, 'Restore failed'));
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

  // Filter to active classes only.
  const activeClasses = (classes || []).filter((c) => c.is_active !== false);

  return (
    <BaseModal
      open={open}
      onClose={handleClose}
      title="Restore student"
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={handleClose} disabled={loading}>
            Cancel
          </Button>
          <LoadingButton
            loading={loading}
            disabled={!targetClassId}
            onClick={handleConfirm}
            className="bg-accent hover:bg-accent-hover text-white"
          >
            Restore
          </LoadingButton>
        </>
      }
    >
      <div className="space-y-4">
        <p className="text-sm text-zinc-300">
          Restore{' '}
          <span className="font-medium text-zinc-100">
            {student?.name}
          </span>{' '}
          to active status. Select a class to enroll them in.
        </p>

        {student?.last_class_code ? (
          <p className="text-xs text-zinc-500">
            Previously in: <span className="font-mono">{student.last_class_code}</span>
          </p>
        ) : null}

        <div>
          <label className="block text-xs font-medium text-zinc-400 mb-1">
            Target class
          </label>
          <select
            value={targetClassId}
            onChange={(e) => setTargetClassId(e.target.value)}
            className="w-full rounded-md border border-surface-border bg-surface-raised px-3 py-2 text-sm text-zinc-200 focus:border-accent focus:outline-none"
          >
            <option value="">Select a class...</option>
            {activeClasses.map((c) => (
              <option key={c.class_id} value={c.class_id}>
                {c.class_code}
              </option>
            ))}
          </select>
        </div>

        <p className="text-xs text-zinc-500">
          The student will be active immediately but will not be recognized
          until the model is retrained.
        </p>

        {error ? (
          <div className="text-xs text-rose-300">{error}</div>
        ) : null}
      </div>
    </BaseModal>
  );
}

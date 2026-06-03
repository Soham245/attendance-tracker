import { useEffect, useState } from 'react';
import ConfirmDialog from '../common/ConfirmDialog.jsx';
import { errorMessage } from '../../services/api.js';

export default function DeleteStudentDialog({ open, student, onClose, onConfirm }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (open) {
      setLoading(false);
      setError(null);
    }
  }, [open]);

  const handleConfirm = async () => {
    if (!student) return;
    setLoading(true);
    setError(null);
    try {
      await onConfirm(student);
      onClose();
    } catch (err) {
      setError(errorMessage(err, 'Could not delete the student.'));
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
      title="Delete student"
      confirmLabel="Delete"
      description={
        student ? (
          <>
            <p>
              This will permanently remove{' '}
              <span className="font-medium text-zinc-100">{student.name}</span>{' '}
              ({student.roll_number}), along with their dataset images. This action
              cannot be undone.
            </p>
            <p className="mt-2 text-xs text-zinc-500">
              You'll need to retrain the model afterward for the change to take effect.
            </p>
          </>
        ) : null
      }
    />
  );
}

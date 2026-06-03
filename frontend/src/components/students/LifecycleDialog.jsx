import { useState } from 'react';
import ConfirmDialog from '../common/ConfirmDialog.jsx';
import { errorMessage } from '../../services/api.js';

/**
 * Reusable confirmation dialog for student lifecycle operations.
 *
 * Handles loading state and error display. The caller provides the
 * async action and receives a callback on success.
 */
export default function LifecycleDialog({
  open,
  student,
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel,
  tone = 'warning',
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleConfirm = async () => {
    setLoading(true);
    setError(null);
    try {
      await onConfirm(student);
      onClose();
    } catch (err) {
      setError(errorMessage(err, 'Operation failed'));
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

  return (
    <ConfirmDialog
      open={open}
      onClose={handleClose}
      onConfirm={handleConfirm}
      title={title}
      description={description}
      confirmLabel={confirmLabel}
      tone={tone}
      loading={loading}
      error={error}
    />
  );
}

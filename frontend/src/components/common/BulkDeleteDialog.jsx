import { useEffect, useState } from 'react';
import ConfirmDialog from './ConfirmDialog.jsx';
import { errorMessage } from '../../services/api.js';

/**
 * Confirmation dialog for bulk-deleting selected rows.
 *
 * Props:
 *   open       – boolean
 *   count      – number of selected items
 *   noun       – singular label, e.g. "attendance record" or "session"
 *   onClose    – close handler
 *   onConfirm  – async () => void — performs the actual deletion
 */
export default function BulkDeleteDialog({ open, count, noun = 'item', onClose, onConfirm }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (open) {
      setLoading(false);
      setError(null);
    }
  }, [open]);

  const plural = count === 1 ? noun : `${noun}s`;

  const handleConfirm = async () => {
    setLoading(true);
    setError(null);
    try {
      await onConfirm();
      onClose();
    } catch (err) {
      setError(errorMessage(err, `Could not delete the selected ${plural}.`));
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
      title={`Delete ${count} ${plural}`}
      confirmLabel="Delete"
      description={
        <p>
          This will permanently remove{' '}
          <span className="font-medium text-zinc-100">
            {count} {plural}
          </span>
          . This action cannot be undone.
        </p>
      }
    />
  );
}

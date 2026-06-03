import { useEffect, useState } from 'react';
import BaseModal from '../common/BaseModal.jsx';
import Button from '../common/Button.jsx';
import LoadingButton from '../common/LoadingButton.jsx';
import { errorMessage } from '../../services/api.js';
import { useClassContext } from '../../context/ClassContext.jsx';

/**
 * Dialog to restore all students from a lifecycle batch.
 *
 * Used to undo a class-wide graduation or deactivation. The admin
 * selects the target class to re-enroll students into (the original
 * class may no longer be appropriate).
 */
export default function BatchRestoreDialog({
  open,
  batchId,
  batchInfo,
  onClose,
  onConfirm,
}) {
  const { classes, activeClass } = useClassContext();
  const [targetClassId, setTargetClassId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Reset form when dialog opens.
  useEffect(() => {
    if (open) {
      setTargetClassId(activeClass ? String(activeClass.class_id) : '');
      setError(null);
    }
  }, [open, batchId, activeClass]);

  const handleConfirm = async () => {
    if (!targetClassId || !batchId) return;
    setLoading(true);
    setError(null);
    try {
      await onConfirm(batchId, Number(targetClassId));
      onClose();
    } catch (err) {
      setError(errorMessage(err, 'Batch restore failed'));
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

  const activeClasses = (classes || []).filter((c) => c.is_active !== false);

  return (
    <BaseModal
      open={open}
      onClose={handleClose}
      title="Restore batch"
      subtitle={batchInfo?.classCode ? `From: ${batchInfo.classCode}` : undefined}
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
            Restore batch
          </LoadingButton>
        </>
      }
    >
      <div className="space-y-4">
        <p className="text-sm text-zinc-300">
          Restore all students from this lifecycle batch to active status.
          {batchInfo?.count ? (
            <span className="text-zinc-100 font-medium">
              {' '}{batchInfo.count} student{batchInfo.count !== 1 ? 's' : ''} will be restored.
            </span>
          ) : null}
        </p>

        {batchId ? (
          <div className="text-xs text-zinc-500 font-mono break-all">
            Batch: {batchId}
          </div>
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
          All restored students will be set to active but will require model
          retraining before they can be recognized.
        </p>

        {error ? (
          <div className="text-xs text-rose-300">{error}</div>
        ) : null}
      </div>
    </BaseModal>
  );
}

import { useEffect, useState } from 'react';
import { AlertTriangle, ArrowRight, Check } from 'lucide-react';
import BaseModal from '../common/BaseModal.jsx';
import Button from '../common/Button.jsx';
import LoadingButton from '../common/LoadingButton.jsx';
import { errorMessage } from '../../services/api.js';
import { fetchPromotionPreview } from '../../services/lifecycleService.js';

/**
 * Auto-resolved promotion dialog for a single class.
 *
 * On open, fetches a preview from the server to show the auto-resolved
 * target class and student count. No manual target selection.
 */
export default function PromoteClassDialog({
  open,
  sourceClass,
  onClose,
  onConfirm,
}) {
  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch preview when dialog opens.
  useEffect(() => {
    if (!open || !sourceClass) {
      setPreview(null);
      setPreviewError(null);
      setError(null);
      return;
    }

    let cancelled = false;
    setPreviewLoading(true);
    setPreviewError(null);

    fetchPromotionPreview({ classId: sourceClass.id })
      .then((result) => {
        if (!cancelled) {
          const item = result?.items?.[0] ?? null;
          setPreview(item);
        }
      })
      .catch((err) => {
        if (!cancelled) setPreviewError(errorMessage(err, 'Could not load preview'));
      })
      .finally(() => {
        if (!cancelled) setPreviewLoading(false);
      });

    return () => { cancelled = true; };
  }, [open, sourceClass?.id]);

  const handleConfirm = async () => {
    if (!sourceClass) return;
    setLoading(true);
    setError(null);
    try {
      await onConfirm(sourceClass);
      onClose();
    } catch (err) {
      setError(errorMessage(err, 'Promotion failed'));
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

  const canConfirm = preview && !preview.target_missing && preview.action === 'promote' && preview.student_count > 0;

  return (
    <BaseModal
      open={open}
      onClose={handleClose}
      title="Promote class"
      subtitle={sourceClass?.class_code}
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={handleClose} disabled={loading}>
            Cancel
          </Button>
          <LoadingButton
            loading={loading}
            disabled={!canConfirm || previewLoading}
            onClick={handleConfirm}
            className="bg-accent hover:bg-accent-hover text-white"
          >
            Promote
          </LoadingButton>
        </>
      }
    >
      <div className="space-y-4">
        {previewLoading ? (
          <div className="text-sm text-zinc-400 animate-pulse">
            Resolving target class...
          </div>
        ) : previewError ? (
          <div className="text-sm text-rose-300">{previewError}</div>
        ) : preview ? (
          <>
            {/* Promotion arrow */}
            <div className="flex items-center gap-3 rounded-lg bg-surface-raised p-3">
              <div className="text-center flex-1">
                <div className="text-[11px] text-zinc-500 mb-1">From</div>
                <div className="font-mono text-sm font-medium text-zinc-100">
                  {preview.source_class_code}
                </div>
                <div className="text-xs text-zinc-400 mt-0.5">
                  {preview.student_count} student{preview.student_count !== 1 ? 's' : ''}
                </div>
              </div>
              <ArrowRight size={16} className="text-zinc-500 shrink-0" />
              <div className="text-center flex-1">
                <div className="text-[11px] text-zinc-500 mb-1">To</div>
                {preview.target_missing ? (
                  <div className="font-mono text-sm font-medium text-amber-400">
                    Not found
                  </div>
                ) : (
                  <div className="font-mono text-sm font-medium text-zinc-100">
                    {preview.target_class_code}
                  </div>
                )}
                {preview.target_has_faculty ? (
                  <div className="flex items-center justify-center gap-1 text-xs text-emerald-400 mt-0.5">
                    <Check size={10} /> Faculty assigned
                  </div>
                ) : preview.target_class_code ? (
                  <div className="flex items-center justify-center gap-1 text-xs text-amber-400 mt-0.5">
                    <AlertTriangle size={10} /> No faculty
                  </div>
                ) : null}
              </div>
            </div>

            {preview.target_missing ? (
              <div className="rounded-md bg-amber-500/10 border border-amber-500/20 p-3 text-xs text-amber-300">
                The target class does not exist yet. Create it first, then try again.
              </div>
            ) : preview.action === 'graduate' ? (
              <div className="text-xs text-zinc-400">
                This is a final-year class. Use "Graduate" instead.
              </div>
            ) : (
              <p className="text-xs text-zinc-500">
                Students keep their datasets, embeddings, and attendance history.
                No retraining required.
              </p>
            )}
          </>
        ) : null}

        {error ? (
          <div className="text-xs text-rose-300">{error}</div>
        ) : null}
      </div>
    </BaseModal>
  );
}

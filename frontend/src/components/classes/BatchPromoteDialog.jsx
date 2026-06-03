import { useEffect, useState } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  Check,
  GraduationCap,
  SkipForward,
} from 'lucide-react';
import BaseModal from '../common/BaseModal.jsx';
import Button from '../common/Button.jsx';
import LoadingButton from '../common/LoadingButton.jsx';
import { errorMessage } from '../../services/api.js';
import { fetchPromotionPreview, executePromotion } from '../../services/lifecycleService.js';

const ACTION_ICONS = {
  promote: ArrowRight,
  graduate: GraduationCap,
  skip: SkipForward,
};

const ACTION_LABELS = {
  promote: 'Promote',
  graduate: 'Graduate',
  skip: 'Skip',
};

const ACTION_COLORS = {
  promote: 'text-sky-400',
  graduate: 'text-amber-400',
  skip: 'text-zinc-500',
};

/**
 * Batch promotion dialog for an entire major.
 *
 * Shows a preview table of all classes in the major with their
 * auto-resolved actions (promote / graduate / skip).
 */
export default function BatchPromoteDialog({
  open,
  major,
  onClose,
  onComplete,
}) {
  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // Fetch preview on open.
  useEffect(() => {
    if (!open || !major) {
      setPreview(null);
      setPreviewError(null);
      setError(null);
      setResult(null);
      return;
    }

    let cancelled = false;
    setPreviewLoading(true);
    setPreviewError(null);

    fetchPromotionPreview({ major })
      .then((data) => {
        if (!cancelled) setPreview(data);
      })
      .catch((err) => {
        if (!cancelled) setPreviewError(errorMessage(err, 'Could not load preview'));
      })
      .finally(() => {
        if (!cancelled) setPreviewLoading(false);
      });

    return () => { cancelled = true; };
  }, [open, major]);

  const items = preview?.items ?? [];
  const actionableItems = items.filter(
    (i) => i.action !== 'skip' && !(i.action === 'promote' && i.target_missing),
  );
  const hasAnyAction = actionableItems.length > 0;

  const handleExecute = async () => {
    if (!hasAnyAction) return;
    setLoading(true);
    setError(null);
    try {
      const ids = actionableItems.map((i) => i.source_class_id);
      const res = await executePromotion(ids);
      setResult(res);
      onComplete(res);
    } catch (err) {
      setError(errorMessage(err, 'Promotion failed'));
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (!loading) {
      onClose();
    }
  };

  const totalStudents = actionableItems.reduce((s, i) => s + i.student_count, 0);

  return (
    <BaseModal
      open={open}
      onClose={handleClose}
      title={result ? 'Promotion complete' : `Promote ${major}`}
      subtitle={preview ? `${preview.program_duration}-year program` : undefined}
      size="md"
      footer={
        result ? (
          <Button variant="ghost" onClick={handleClose}>
            Close
          </Button>
        ) : (
          <>
            <Button variant="ghost" onClick={handleClose} disabled={loading}>
              Cancel
            </Button>
            <LoadingButton
              loading={loading}
              disabled={!hasAnyAction || previewLoading}
              onClick={handleExecute}
              className="bg-accent hover:bg-accent-hover text-white"
            >
              Execute ({totalStudents} student{totalStudents !== 1 ? 's' : ''})
            </LoadingButton>
          </>
        )
      }
    >
      {/* Preview loading / error */}
      {previewLoading ? (
        <div className="text-sm text-zinc-400 animate-pulse py-4 text-center">
          Building promotion plan...
        </div>
      ) : previewError ? (
        <div className="text-sm text-rose-300">{previewError}</div>
      ) : result ? (
        /* Results summary */
        <div className="space-y-3">
          {result.promoted?.length ? (
            <div>
              <div className="text-xs text-zinc-500 mb-1">Promoted</div>
              {result.promoted.map((p, i) => (
                <div key={i} className="flex items-center gap-2 text-sm text-zinc-200 py-1">
                  <Check size={14} className="text-emerald-400 shrink-0" />
                  <span className="font-mono text-xs">{p.source}</span>
                  <ArrowRight size={12} className="text-zinc-500" />
                  <span className="font-mono text-xs">{p.target}</span>
                  <span className="text-zinc-500 text-xs ml-auto">{p.count} students</span>
                </div>
              ))}
            </div>
          ) : null}
          {result.graduated?.length ? (
            <div>
              <div className="text-xs text-zinc-500 mb-1">Graduated</div>
              {result.graduated.map((g, i) => (
                <div key={i} className="flex items-center gap-2 text-sm text-zinc-200 py-1">
                  <GraduationCap size={14} className="text-amber-400 shrink-0" />
                  <span className="font-mono text-xs">{g.source}</span>
                  <span className="text-zinc-500 text-xs ml-auto">{g.count} students</span>
                </div>
              ))}
            </div>
          ) : null}
          {result.skipped?.length ? (
            <div>
              <div className="text-xs text-zinc-500 mb-1">Skipped</div>
              {result.skipped.map((s, i) => (
                <div key={i} className="text-xs text-zinc-500 py-1">
                  {s.class_code ?? `Class #${s.class_id}`}: {s.reason}
                </div>
              ))}
            </div>
          ) : null}
          {result.model_stale ? (
            <div className="rounded-md bg-amber-500/10 border border-amber-500/20 p-2 text-xs text-amber-300">
              Recognition model is stale. Re-train to update it.
            </div>
          ) : null}
        </div>
      ) : items.length === 0 ? (
        <div className="text-sm text-zinc-500 py-4 text-center">
          No active classes found for {major}.
        </div>
      ) : (
        /* Preview table */
        <div className="space-y-3">
          <p className="text-xs text-zinc-400">
            Review the promotion plan below. Classes at final year will be graduated
            automatically.
          </p>

          <div className="divide-y divide-surface-border rounded-md border border-surface-border overflow-hidden">
            {/* Header */}
            <div className="grid grid-cols-[1fr_80px_auto_1fr_80px] gap-2 px-3 py-2 bg-surface-raised text-[11px] text-zinc-500 font-medium">
              <span>Source</span>
              <span>Students</span>
              <span></span>
              <span>Target</span>
              <span>Action</span>
            </div>
            {items.map((item) => {
              const Icon = ACTION_ICONS[item.action] ?? SkipForward;
              return (
                <div
                  key={item.source_class_id}
                  className="grid grid-cols-[1fr_80px_auto_1fr_80px] gap-2 px-3 py-2.5 items-center text-sm"
                >
                  <span className="font-mono text-xs text-zinc-200">
                    {item.source_class_code}
                  </span>
                  <span className="text-xs text-zinc-400 tabular-nums">
                    {item.student_count}
                  </span>
                  <ArrowRight size={12} className="text-zinc-600" />
                  <span className="font-mono text-xs">
                    {item.action === 'graduate' ? (
                      <span className="text-amber-400">Graduation</span>
                    ) : item.target_missing ? (
                      <span className="flex items-center gap-1 text-amber-400">
                        <AlertTriangle size={11} />
                        Missing
                      </span>
                    ) : (
                      <span className="text-zinc-200">
                        {item.target_class_code}
                        {!item.target_has_faculty ? (
                          <span className="text-amber-400 ml-1" title="No faculty assigned">
                            *
                          </span>
                        ) : null}
                      </span>
                    )}
                  </span>
                  <span className={`flex items-center gap-1 text-xs ${ACTION_COLORS[item.action]}`}>
                    <Icon size={12} />
                    {ACTION_LABELS[item.action]}
                  </span>
                </div>
              );
            })}
          </div>

          {items.some((i) => i.target_missing) ? (
            <div className="rounded-md bg-amber-500/10 border border-amber-500/20 p-2 text-xs text-amber-300">
              Some target classes are missing. They will be skipped. Create them first for a complete promotion.
            </div>
          ) : null}

          {error ? (
            <div className="text-xs text-rose-300">{error}</div>
          ) : null}
        </div>
      )}
    </BaseModal>
  );
}

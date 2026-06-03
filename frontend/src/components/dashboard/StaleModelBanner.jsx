import { AlertTriangle } from 'lucide-react';
import { formatRelative } from '../../utils/format.js';

export default function StaleModelBanner({ status }) {
  const health = status?.model_health;
  if (!health?.model_stale) return null;

  const since = health.model_stale_since;
  const seen = Number(health.stale_predictions_seen) || 0;

  return (
    <div
      role="alert"
      className="mb-4 flex items-start gap-3 rounded-md border border-red-900/60 bg-red-950/40 px-4 py-3 text-sm text-red-200"
    >
      <AlertTriangle size={18} className="mt-0.5 shrink-0 text-red-400" />
      <div className="min-w-0">
        <div className="font-medium text-red-100">Model retraining required</div>
        <p className="mt-0.5 text-xs text-red-300/90">
          The active model predicted a student that no longer exists in the
          database. Those recognitions are being suppressed and will not mark
          attendance. Retrain the model to clear this warning.
        </p>
        <div className="mt-1.5 text-[11px] text-red-400/80 tabular-nums">
          {since ? <>First seen {formatRelative(since)} · </> : null}
          {seen} stale prediction{seen === 1 ? '' : 's'} suppressed
        </div>
      </div>
    </div>
  );
}

import { CheckCircle2 } from 'lucide-react';

/**
 * Compact success summary shown beneath the preview after a successful
 * capture run. Doesn't replace the rest of the modal — just calls out what
 * just happened and points the operator at training.
 */
export default function CaptureCompletionView({ status }) {
  if (!status || status.state !== 'completed') return null;
  const collected = status.samples_collected ?? 0;
  return (
    <div className="flex items-start gap-2.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2.5 text-xs text-emerald-100">
      <CheckCircle2 size={14} className="mt-0.5 shrink-0 text-emerald-300" />
      <div className="leading-relaxed">
        <div className="font-medium">Capture complete</div>
        <div className="text-emerald-200/80">
          Saved {collected} sample{collected === 1 ? '' : 's'} to this
          student's dataset. <span className="text-emerald-100">Re-run training</span>{' '}
          to incorporate them.
        </div>
      </div>
    </div>
  );
}

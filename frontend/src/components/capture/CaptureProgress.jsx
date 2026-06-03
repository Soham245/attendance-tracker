/**
 * Sample counter + progress bar. Values come straight from the polled status —
 * no client-side smoothing or fake progress simulation. Layout stays the
 * same size in every state so polling re-renders never reflow the modal.
 */
export default function CaptureProgress({ status }) {
  const collected = status?.samples_collected ?? 0;
  const target = status?.target_samples ?? 0;
  const ratio = target > 0 ? Math.min(1, collected / target) : 0;
  const percent = Math.round(ratio * 100);

  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <div className="text-[10px] uppercase tracking-wider text-zinc-500">
          Samples collected
        </div>
        <div className="text-xs text-zinc-400 tabular-nums">{percent}%</div>
      </div>
      <div className="mt-1 flex items-baseline gap-2">
        <span className="text-2xl font-semibold text-zinc-100 tabular-nums">
          {collected}
        </span>
        <span className="text-xs text-zinc-500 tabular-nums">/ {target || '—'}</span>
      </div>
      <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-surface-border">
        <div
          className="h-full bg-accent transition-[width] duration-200 ease-out"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

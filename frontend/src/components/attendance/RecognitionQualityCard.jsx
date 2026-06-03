import { ShieldCheck, ShieldX, AlertTriangle, HelpCircle } from 'lucide-react';
import RuntimeCard from '../common/RuntimeCard.jsx';

/**
 * Recognition quality panel: accepted/rejected/stale counts, similarity
 * statistics, and threshold context. Fed by `status.runtime_metrics`.
 */
export default function RecognitionQualityCard({ status }) {
  const m = status?.runtime_metrics;
  if (!m) return null;

  const { counters, recognition } = m;
  const threshold = status?.diagnostics?.metric_stats?.threshold;

  return (
    <RuntimeCard
      title="Recognition quality"
      subtitle="Acceptance rates and similarity distribution."
      icon={ShieldCheck}
    >
      {/* Counter chips */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
        <Counter
          icon={ShieldCheck}
          label="Accepted"
          value={counters?.accepted ?? 0}
          color="text-emerald-300"
        />
        <Counter
          icon={ShieldX}
          label="Rejected"
          value={counters?.rejected ?? 0}
          color="text-rose-300"
        />
        <Counter
          icon={AlertTriangle}
          label="Stale"
          value={counters?.stale ?? 0}
          color="text-amber-300"
        />
        <Counter
          icon={HelpCircle}
          label="Unknown"
          value={counters?.unknown ?? 0}
          color="text-zinc-400"
        />
      </div>

      {/* Similarity stats */}
      {recognition ? (
        <div className="space-y-2">
          <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs tabular-nums">
            <SimStat label="Mean" value={recognition.mean} />
            <SimStat label="p50" value={recognition.p50} />
            <SimStat label="p95" value={recognition.p95} />
            <SimStat label="Min" value={recognition.min} warn />
            <SimStat label="Max" value={recognition.max} />
            {threshold != null ? (
              <SimStat label="Threshold" value={threshold} accent />
            ) : null}
          </div>

          {/* Visual threshold bar */}
          {threshold != null && recognition.mean != null ? (
            <ThresholdBar
              mean={recognition.mean}
              min={recognition.min}
              max={recognition.max}
              threshold={threshold}
            />
          ) : null}

          <p className="text-[10px] text-zinc-600">
            {recognition.count} similarity samples in rolling window.
          </p>
        </div>
      ) : (
        <p className="text-xs text-zinc-500">
          No recognition events yet. Similarity stats will appear once faces are recognized.
        </p>
      )}
    </RuntimeCard>
  );
}

function Counter({ icon: Icon, label, value, color }) {
  return (
    <div className="rounded-md border border-surface-border bg-surface-raised/50 px-2.5 py-2 text-center">
      <div className="flex items-center justify-center gap-1.5 text-[9px] uppercase tracking-wider text-zinc-500 mb-1">
        <Icon size={11} />
        {label}
      </div>
      <div className={`text-lg font-semibold tabular-nums ${color}`}>
        {value}
      </div>
    </div>
  );
}

function SimStat({ label, value, accent, warn }) {
  if (value == null) return null;
  const pct = `${(Number(value) * 100).toFixed(1)}%`;
  let color = 'text-zinc-200';
  if (accent) color = 'text-amber-300';
  if (warn) color = 'text-rose-300';
  return (
    <div>
      <span className="text-zinc-500">{label} </span>
      <span className={color}>{pct}</span>
    </div>
  );
}

function ThresholdBar({ mean, min, max, threshold }) {
  // Simple horizontal bar showing where mean sits relative to threshold.
  const clamp = (v) => Math.max(0, Math.min(1, v));
  const threshPct = clamp(threshold) * 100;
  const meanPct = clamp(mean) * 100;
  const minPct = clamp(min) * 100;
  const maxPct = clamp(max) * 100;

  return (
    <div className="relative h-4 rounded bg-surface-border/50 overflow-hidden">
      {/* Range bar (min to max) */}
      <div
        className="absolute top-0.5 bottom-0.5 rounded bg-emerald-500/30"
        style={{ left: `${minPct}%`, width: `${maxPct - minPct}%` }}
      />
      {/* Mean marker */}
      <div
        className="absolute top-0 bottom-0 w-0.5 bg-emerald-400"
        style={{ left: `${meanPct}%` }}
        title={`Mean: ${(mean * 100).toFixed(1)}%`}
      />
      {/* Threshold marker */}
      <div
        className="absolute top-0 bottom-0 w-0.5 bg-amber-400"
        style={{ left: `${threshPct}%` }}
        title={`Threshold: ${(threshold * 100).toFixed(0)}%`}
      />
      {/* Labels */}
      <span
        className="absolute text-[8px] text-amber-400 -top-0.5"
        style={{ left: `${threshPct}%`, transform: 'translateX(-50%) translateY(-100%)' }}
      >
        T
      </span>
    </div>
  );
}

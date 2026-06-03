import { useState } from 'react';
import { ChevronDown, ChevronRight, Activity } from 'lucide-react';

/**
 * Collapsible panel showing the recognition similarity distribution.
 *
 * All values are unified similarity [0, 1] — higher = better match,
 * regardless of which recognition backend is active.  The threshold is a
 * floor: matches below it are rejected.
 */
export default function DistanceDiagnosticsPanel({ status }) {
  const [open, setOpen] = useState(false);
  const stats = status?.diagnostics?.metric_stats;

  if (!stats || !stats.count) return null;

  return (
    <div className="rounded-lg border border-surface-border bg-surface-raised/40">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
      >
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <Activity size={14} />
        <span>Recognition diagnostics</span>
        <span className="ml-auto tabular-nums text-[11px] text-zinc-500">
          {stats.count} samples · threshold {fmtPct(stats.threshold)}
        </span>
      </button>

      {open ? (
        <div className="border-t border-surface-border px-4 py-3 space-y-3">
          {/* Stats row */}
          <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs tabular-nums">
            <Stat label="Min" value={stats.min} />
            <Stat label="Mean" value={stats.mean} />
            <Stat label="Median" value={stats.median} />
            <Stat label="Max" value={stats.max} />
            <Stat label="Threshold" value={stats.threshold} accent />
          </div>

          {/* Histogram */}
          {stats.histogram ? <Histogram data={stats.histogram} threshold={stats.threshold} /> : null}

          <p className="text-[10px] text-zinc-600">
            Higher similarity = stronger match. Recognitions below the threshold are rejected.
          </p>
        </div>
      ) : null}
    </div>
  );
}

function fmtPct(v) {
  return `${(Number(v) * 100).toFixed(0)}%`;
}

function Stat({ label, value, accent }) {
  return (
    <div>
      <span className="text-zinc-500">{label} </span>
      <span className={accent ? 'text-amber-300' : 'text-zinc-200'}>
        {fmtPct(value)}
      </span>
    </div>
  );
}

function Histogram({ data, threshold }) {
  const entries = Object.entries(data)
    .map(([bucket, count]) => {
      const lo = parseFloat(bucket.split('-')[0]);
      return { bucket, count: Number(count), lo };
    })
    .sort((a, b) => a.lo - b.lo);

  const maxCount = Math.max(...entries.map((e) => e.count), 1);

  return (
    <div className="space-y-0.5">
      {entries.map(({ bucket, count, lo }) => {
        const pct = (count / maxCount) * 100;
        // Below threshold = rejected (red), at or above = accepted (green)
        const belowThreshold = lo + 0.1 <= threshold;
        return (
          <div key={bucket} className="flex items-center gap-2 text-[11px]">
            <span className="w-14 text-right text-zinc-500 tabular-nums font-mono">
              {bucket}
            </span>
            <div className="flex-1 h-3 rounded-sm bg-surface-border/50 overflow-hidden">
              <div
                className={
                  'h-full rounded-sm transition-[width] ' +
                  (belowThreshold
                    ? 'bg-rose-500/60'
                    : 'bg-emerald-500/50')
                }
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="w-6 text-right text-zinc-500 tabular-nums">{count}</span>
          </div>
        );
      })}
    </div>
  );
}

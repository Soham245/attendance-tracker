import { Gauge, Cpu, Eye, Sparkles, Search } from 'lucide-react';
import RuntimeCard from '../common/RuntimeCard.jsx';

/**
 * Runtime performance panel showing latency breakdown, FPS, and backend info.
 * Fed by `status.runtime_metrics` from the polling status endpoint.
 */
export default function RuntimePerformanceCard({ status }) {
  const m = status?.runtime_metrics;
  if (!m) return null;

  const { backends, latency, detection, counters } = m;

  return (
    <RuntimeCard
      title="Runtime performance"
      subtitle="Latency breakdown and throughput."
      icon={Gauge}
    >
      {/* Backend info row */}
      <div className="flex flex-wrap gap-3 mb-4">
        <Badge label="Detector" value={backends?.detector ?? '—'} />
        <Badge label="Recognizer" value={backends?.recognizer ?? '—'} />
        <Badge label="Gallery" value={backends?.gallery_size ?? 0} suffix="embeddings" />
        <Badge label="FPS" value={detection?.fps ?? 0} />
        <Badge label="Frames" value={counters?.frames_processed ?? 0} />
      </div>

      {/* Latency table */}
      <div className="space-y-1">
        <LatencyRow label="Frame total" icon={Cpu} stats={latency?.frame} />
        <LatencyRow label="Detection" icon={Eye} stats={latency?.detection} />
        <LatencyRow label="Alignment" icon={Sparkles} stats={latency?.alignment} />
        <LatencyRow label="Embedding" icon={Sparkles} stats={latency?.embedding} />
        <LatencyRow label="Gallery search" icon={Search} stats={latency?.gallery} />
      </div>

      <div className="mt-3 flex items-center justify-between text-[10px] text-zinc-600">
        <span>Avg faces/frame: {detection?.avg_faces_per_frame ?? '—'}</span>
        <span>Uptime: {fmtUptime(m.uptime_seconds)}</span>
      </div>
    </RuntimeCard>
  );
}

function Badge({ label, value, suffix }) {
  return (
    <div className="rounded-md border border-surface-border bg-surface-raised/50 px-2.5 py-1.5">
      <div className="text-[9px] uppercase tracking-wider text-zinc-500">{label}</div>
      <div className="text-sm font-medium text-zinc-100 tabular-nums">
        {value}
        {suffix ? <span className="ml-1 text-[10px] text-zinc-500">{suffix}</span> : null}
      </div>
    </div>
  );
}

function LatencyRow({ label, icon: Icon, stats }) {
  if (!stats) return null;
  return (
    <div className="flex items-center gap-2 text-xs">
      <Icon size={12} className="text-zinc-500 shrink-0" />
      <span className="w-28 text-zinc-400 truncate">{label}</span>
      <span className="flex-1" />
      <Pill label="p50" value={stats.p50} />
      <Pill label="p95" value={stats.p95} accent />
      <Pill label="max" value={stats.max} />
      <span className="w-10 text-right text-[10px] text-zinc-600 tabular-nums">
        n={stats.samples}
      </span>
    </div>
  );
}

function Pill({ label, value, accent }) {
  const color = accent ? 'text-amber-300' : 'text-zinc-200';
  return (
    <span className="inline-flex items-baseline gap-1 min-w-[4.5rem]">
      <span className="text-[10px] text-zinc-500">{label}</span>
      <span className={`tabular-nums ${color}`}>{fmtMs(value)}</span>
    </span>
  );
}

function fmtMs(v) {
  if (v == null) return '—';
  return `${Number(v).toFixed(1)}ms`;
}

function fmtUptime(seconds) {
  if (!seconds) return '—';
  const s = Math.round(seconds);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  if (m < 60) return `${m}m ${rem}s`;
  const h = Math.floor(m / 60);
  return `${h}h ${m % 60}m`;
}

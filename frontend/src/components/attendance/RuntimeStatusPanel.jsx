import { Activity, Camera, Cpu, Clock } from 'lucide-react';
import RuntimeCard from '../common/RuntimeCard.jsx';
import RuntimeStatusBadge from '../common/RuntimeStatusBadge.jsx';
import { formatRelative } from '../../utils/format.js';

/**
 * Compact 2x2 panel summarising the recognition pipeline. Mirrors backend
 * RecognitionStatus fields — single source of truth, no derived state.
 */
export default function RuntimeStatusPanel({ status }) {
  const recognition = status?.recognition ?? {};
  const events = recognition.events_processed ?? 0;

  return (
    <RuntimeCard
      title="Recognition pipeline"
      subtitle="Camera, model, and event throughput."
      right={<RuntimeStatusBadge state={recognition.state ?? 'idle'} />}
    >
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat
          icon={Activity}
          label="State"
          value={recognition.state ?? '—'}
        />
        <Stat
          icon={Camera}
          label="Camera"
          value={recognition.camera_active ? 'Active' : 'Inactive'}
          tone={recognition.camera_active ? 'good' : 'muted'}
        />
        <Stat
          icon={Cpu}
          label="Model"
          value={recognition.model_loaded ? 'Loaded' : 'Not loaded'}
          tone={recognition.model_loaded ? 'good' : 'muted'}
        />
        <Stat
          icon={Clock}
          label="Last event"
          value={
            recognition.last_event?.recognized_at
              ? formatRelative(recognition.last_event.recognized_at)
              : '—'
          }
        />
      </div>

      <div className="mt-4 flex items-center justify-between text-xs text-zinc-500">
        <span>Events processed</span>
        <span className="text-zinc-200 tabular-nums">{events}</span>
      </div>
    </RuntimeCard>
  );
}

function Stat({ icon: Icon, label, value, tone }) {
  const valueColor =
    tone === 'good'
      ? 'text-emerald-200'
      : tone === 'muted'
        ? 'text-zinc-400'
        : 'text-zinc-100';

  return (
    <div className="rounded-lg border border-surface-border bg-surface-raised/50 px-3 py-2.5">
      <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-zinc-500">
        <Icon size={12} />
        {label}
      </div>
      <div className={`mt-1 text-sm font-medium truncate ${valueColor}`}>
        {value || '—'}
      </div>
    </div>
  );
}

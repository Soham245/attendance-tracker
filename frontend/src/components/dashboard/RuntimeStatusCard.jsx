import { Activity, AlertTriangle, Camera, Cpu } from 'lucide-react';
import Card, { CardBody, CardHeader } from '../common/Card.jsx';
import StatusBadge from '../common/StatusBadge.jsx';
import { formatRelative } from '../../utils/format.js';

export default function RuntimeStatusCard({ status, error }) {
  const recognition = status?.recognition ?? {};
  const sessionState = status?.session_state ?? (error ? 'error' : 'idle');

  return (
    <Card className="p-5">
      <CardHeader
        title="Session runtime"
        subtitle="Recognition + ingestion pipeline"
        right={<StatusBadge state={sessionState} />}
      />

      <CardBody className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat
          icon={Activity}
          label="Recognition"
          value={recognition.state ?? '—'}
        />
        <Stat
          icon={Camera}
          label="Camera"
          value={recognition.camera_active ? 'Active' : 'Inactive'}
        />
        <Stat
          icon={Cpu}
          label="Model"
          value={recognition.model_loaded ? 'Loaded' : 'Not loaded'}
        />
        <Stat
          icon={AlertTriangle}
          label="Last event"
          value={
            recognition.last_event?.recognized_at
              ? formatRelative(recognition.last_event.recognized_at)
              : '—'
          }
        />
      </CardBody>

      {status?.last_error ? (
        <div className="mt-4 flex items-start gap-2 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
          <AlertTriangle size={15} className="mt-0.5 shrink-0" />
          <span>{status.last_error}</span>
        </div>
      ) : null}
    </Card>
  );
}

function Stat({ icon: Icon, label, value }) {
  return (
    <div className="rounded-lg border border-surface-border bg-surface-raised/50 px-3 py-2.5">
      <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-zinc-500">
        <Icon size={12} />
        {label}
      </div>
      <div className="mt-1 text-sm font-medium text-zinc-100 truncate">
        {value || '—'}
      </div>
    </div>
  );
}

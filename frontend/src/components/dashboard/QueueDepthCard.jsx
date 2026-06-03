import { CircleDot, Database } from 'lucide-react';
import Card, { CardBody, CardHeader } from '../common/Card.jsx';

export default function QueueDepthCard({ status }) {
  const ingestion = status?.ingestion ?? {};
  const queueSize = ingestion.queue_size ?? 0;
  const alive = Boolean(ingestion.alive);

  return (
    <Card className="p-5">
      <CardHeader
        title="Ingestion queue"
        subtitle="Recognition events awaiting persistence"
        right={
          <span
            className={[
              'inline-flex items-center gap-1.5 text-xs',
              alive ? 'text-emerald-300' : 'text-zinc-500',
            ].join(' ')}
          >
            <CircleDot size={12} />
            {alive ? 'Worker online' : 'Worker offline'}
          </span>
        }
      />
      <CardBody className="flex items-end justify-between">
        <div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-semibold text-zinc-100 tabular-nums">
              {queueSize}
            </span>
            <span className="text-xs text-zinc-500">pending</span>
          </div>
          <p className="mt-1 text-xs text-zinc-500">
            Drained continuously by the attendance worker.
          </p>
        </div>
        <Database size={28} className="text-zinc-700" />
      </CardBody>
    </Card>
  );
}

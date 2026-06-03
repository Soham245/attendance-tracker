import { Database } from 'lucide-react';
import RuntimeCard from '../common/RuntimeCard.jsx';

/**
 * Queue depth gives operators a heuristic for whether the ingestion worker
 * is keeping up. Thresholds are conservative — recognition events trickle
 * in, so anything >50 pending is unusual.
 */
function depthTone(size) {
  if (size > 50) return 'danger';
  if (size > 10) return 'warning';
  return 'neutral';
}

export default function QueueHealthCard({ status }) {
  const queueSize = status?.ingestion?.queue_size ?? 0;
  const tone = depthTone(queueSize);

  return (
    <RuntimeCard
      title="Ingestion queue"
      subtitle="Events awaiting persistence."
      icon={Database}
      tone={tone}
    >
      <div className="flex items-end justify-between">
        <div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-semibold text-zinc-100 tabular-nums">
              {queueSize}
            </span>
            <span className="text-xs text-zinc-500">pending</span>
          </div>
          <p className="mt-1 text-xs text-zinc-500">
            {tone === 'danger'
              ? 'Queue is backing up — worker may be unhealthy.'
              : tone === 'warning'
                ? 'Slight backlog; should drain soon.'
                : 'Drained continuously by the attendance worker.'}
          </p>
        </div>
      </div>
    </RuntimeCard>
  );
}

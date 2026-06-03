import { CircleDot, Workflow } from 'lucide-react';
import RuntimeCard from '../common/RuntimeCard.jsx';

export default function WorkerHealthCard({ status }) {
  const alive = Boolean(status?.ingestion?.alive);
  const tone = alive ? 'success' : 'danger';

  return (
    <RuntimeCard
      title="Ingestion worker"
      subtitle="Persists recognition events to the database."
      icon={Workflow}
      tone={tone}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="text-sm text-zinc-300">
          {alive ? (
            <>
              Worker is{' '}
              <span className="text-emerald-200 font-medium">online</span>.
            </>
          ) : (
            <>
              Worker is{' '}
              <span className="text-rose-200 font-medium">offline</span>.
              Events will not persist.
            </>
          )}
        </div>
        <span
          className={[
            'inline-flex items-center gap-1.5 text-xs',
            alive ? 'text-emerald-300' : 'text-rose-300',
          ].join(' ')}
        >
          <CircleDot size={12} className={alive ? '' : 'animate-pulse'} />
          {alive ? 'Online' : 'Offline'}
        </span>
      </div>
    </RuntimeCard>
  );
}

import StatusBadge from '../common/StatusBadge.jsx';
import PollingStateIndicator from '../common/PollingStateIndicator.jsx';

export default function SessionOverview({ status, loading, error }) {
  const sessionState = status?.session_state ?? (error ? 'error' : 'idle');

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
      <div>
        <h1 className="text-xl font-semibold text-zinc-100">Dashboard</h1>
        <p className="text-sm text-zinc-500">
          Live attendance runtime overview
        </p>
      </div>

      <div className="flex items-center gap-3">
        <StatusBadge state={sessionState} />
        <PollingStateIndicator loading={loading} error={error} />
      </div>
    </div>
  );
}

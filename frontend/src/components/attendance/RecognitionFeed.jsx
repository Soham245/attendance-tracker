import { Inbox } from 'lucide-react';
import RuntimeCard from '../common/RuntimeCard.jsx';
import RecognitionEventCard from './RecognitionEventCard.jsx';
import SkeletonFeed from '../common/SkeletonFeed.jsx';

const VISIBLE_LIMIT = 20;

/**
 * Newest-first feed of recent recognitions. Backend returns oldest-first under
 * `recent_events`; we reverse + slice client-side so the cap can change without
 * a backend tweak. Polling-driven — the list re-renders with each tick.
 */
export default function RecognitionFeed({ status, loading }) {
  const raw = Array.isArray(status?.recent_events) ? status.recent_events : [];
  const events = [...raw].reverse().slice(0, VISIBLE_LIMIT);

  return (
    <RuntimeCard
      title="Recent recognitions"
      subtitle="Newest first · capped at the most recent events."
      right={
        <span className="text-xs text-zinc-500">
          {events.length} {events.length === 1 ? 'event' : 'events'}
        </span>
      }
    >
      {events.length === 0 && loading ? (
        <SkeletonFeed rows={4} />
      ) : events.length === 0 ? (
        <Empty />
      ) : (
        <ul className="divide-y divide-surface-border">
          {events.map((evt, idx) => (
            <RecognitionEventCard
              key={`${evt.recognized_at}-${evt.student_id}-${idx}`}
              event={evt}
            />
          ))}
        </ul>
      )}
    </RuntimeCard>
  );
}

function Empty() {
  return (
    <div className="flex flex-col items-center justify-center py-10 text-center">
      <Inbox size={26} className="text-zinc-700" />
      <p className="mt-2 text-sm text-zinc-400">No recent activity</p>
      <p className="text-xs text-zinc-600">
        Recognitions will appear here while a session is running.
      </p>
    </div>
  );
}

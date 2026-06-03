import { Inbox } from 'lucide-react';
import Card, { CardBody, CardHeader } from '../common/Card.jsx';
import { formatRelative } from '../../utils/format.js';

export default function RecentActivity({ status }) {
  const events = Array.isArray(status?.recent_events) ? status.recent_events : [];

  return (
    <Card className="p-5">
      <CardHeader
        title="Recent recognitions"
        subtitle="Latest events emitted by the runtime"
        right={
          <span className="text-xs text-zinc-500">
            {events.length} {events.length === 1 ? 'event' : 'events'}
          </span>
        }
      />
      <CardBody>
        {events.length === 0 ? (
          <Empty />
        ) : (
          <ul className="divide-y divide-surface-border">
            {[...events].reverse().map((evt, idx) => {
              const name = evt.student_name;
              const code = evt.student_code;
              const initial = (name || `#${evt.student_id}`)
                .trim()
                .charAt(0)
                .toUpperCase();
              return (
                <li
                  key={`${evt.recognized_at}-${idx}`}
                  className="flex items-center justify-between py-2.5 text-sm"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="grid place-items-center h-7 w-7 rounded-md bg-surface-raised text-xs text-zinc-300">
                      {initial}
                    </span>
                    <div className="min-w-0">
                      <div className="text-zinc-100 truncate">
                        {name ?? `Student #${evt.student_id}`}
                      </div>
                      <div className="text-[11px] text-zinc-500 truncate">
                        {code ? (
                          <span className="font-mono">{code} · </span>
                        ) : null}
                        {formatRelative(evt.recognized_at)}
                      </div>
                    </div>
                  </div>
                  <div className="text-xs text-zinc-400 tabular-nums">
                    {(Number(evt.confidence) * 100).toFixed(0)}%
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </CardBody>
    </Card>
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

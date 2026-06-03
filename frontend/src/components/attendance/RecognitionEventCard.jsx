import { formatRelative } from '../../utils/format.js';

/**
 * Compact event row. Confidence is shown as a similarity percentage (higher
 * is better). Identity comes from the active model's labels block — already
 * gated by the DB-authoritative validator so deleted students never reach
 * this list.
 */
export default function RecognitionEventCard({ event }) {
  const name = event.student_name;
  const code = event.student_code;
  const initial = (name || `#${event.student_id}`).trim().charAt(0).toUpperCase();
  const simPct = `${(Number(event.confidence) * 100).toFixed(0)}%`;

  return (
    <li className="flex items-center justify-between gap-3 py-2.5 text-sm">
      <div className="flex items-center gap-3 min-w-0">
        <span className="grid place-items-center h-7 w-7 rounded-md bg-surface-raised text-xs text-zinc-300 tabular-nums shrink-0">
          {initial}
        </span>
        <div className="min-w-0">
          <div className="text-zinc-100 truncate">
            {name ?? `Student #${event.student_id}`}
          </div>
          <div className="text-[11px] text-zinc-500 truncate">
            {code ? <span className="font-mono">{code} · </span> : null}
            {formatRelative(event.recognized_at)}
          </div>
        </div>
      </div>
      <div className="text-xs text-zinc-400 tabular-nums shrink-0">
        {simPct}
      </div>
    </li>
  );
}

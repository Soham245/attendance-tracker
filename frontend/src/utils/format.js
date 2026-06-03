/**
 * Parse a datetime value into a local `Date`.
 *
 * The backend stores all timestamps in UTC but SQLite strips timezone
 * info on round-trip, so Pydantic often serialises naive ISO strings
 * (e.g. `"2026-05-25T11:14:13"` with no trailing `Z` or `+00:00`).
 * Without correction `new Date()` would interpret that as *local* time,
 * shifting the displayed value by the user's UTC offset.
 *
 * Rule: if a string has no timezone indicator we assume UTC and append `Z`.
 */
function toDate(value) {
  if (!value) return null;
  if (value instanceof Date) return value;
  // Append 'Z' when no timezone indicator is present.
  if (typeof value === 'string' && !/Z|[+-]\d{2}:\d{2}$/.test(value)) {
    value = value + 'Z';
  }
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function formatDateTime(value) {
  const d = toDate(value);
  if (!d) return '—';
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export function formatRelative(value) {
  const d = toDate(value);
  if (!d) return '—';
  const diff = Date.now() - d.getTime();
  const sec = Math.round(diff / 1000);
  if (sec < 5) return 'just now';
  if (sec < 60) return `${sec}s ago`;
  const min = Math.round(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr}h ago`;
  return formatDateTime(d);
}

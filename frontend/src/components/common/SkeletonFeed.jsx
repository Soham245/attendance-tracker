import Skeleton from './Skeleton.jsx';

/**
 * List-style placeholder used by feeds (recognition stream, activity lists).
 * Renders rows that match the divider styling of those feeds.
 */
export default function SkeletonFeed({ rows = 4 }) {
  return (
    <ul className="divide-y divide-surface-border">
      {Array.from({ length: rows }).map((_, i) => (
        <li
          key={i}
          className="flex items-center justify-between gap-3 py-2.5"
        >
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <Skeleton className="h-7 w-7 rounded-md shrink-0" />
            <div className="min-w-0 flex-1 space-y-1.5">
              <Skeleton className="h-3 w-1/3" />
              <Skeleton className="h-2.5 w-1/4" />
            </div>
          </div>
          <Skeleton className="h-3 w-10 shrink-0" />
        </li>
      ))}
    </ul>
  );
}

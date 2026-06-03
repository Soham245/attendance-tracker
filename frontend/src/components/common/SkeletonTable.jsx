import Skeleton from './Skeleton.jsx';

/**
 * Skeleton inside an existing table body — caller passes column count so the
 * placeholder retains real table geometry and avoids layout shift on swap.
 */
export default function SkeletonTable({ rows = 6, columns = 4 }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, r) => (
        <tr
          key={r}
          className="border-b border-surface-border/60 last:border-b-0"
        >
          {Array.from({ length: columns }).map((__, c) => (
            <td key={c} className="px-4 py-3 align-middle">
              <Skeleton
                className={
                  'h-3 ' + (c === 0 ? 'w-2/3' : c === columns - 1 ? 'w-12 ml-auto' : 'w-1/2')
                }
              />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

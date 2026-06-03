import Skeleton from './Skeleton.jsx';
import { cn } from '../../utils/cn.js';

/**
 * Card-shaped placeholder that mirrors the spacing of `card-padded` so the
 * layout doesn't shift when real content arrives.
 */
export default function SkeletonCard({ lines = 3, className }) {
  return (
    <div className={cn('card-padded', className)}>
      <Skeleton className="h-4 w-1/3" />
      <Skeleton className="mt-2 h-3 w-1/2" />
      <div className="mt-5 space-y-2">
        {Array.from({ length: lines }).map((_, i) => (
          <Skeleton
            key={i}
            className={cn('h-3', i === lines - 1 ? 'w-2/3' : 'w-full')}
          />
        ))}
      </div>
    </div>
  );
}

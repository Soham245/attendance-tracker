import { cn } from '../../utils/cn.js';

/**
 * Base shimmer block. All skeleton primitives compose this so the visual
 * treatment stays consistent — change the animation here once.
 */
export default function Skeleton({ className, ...props }) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        'animate-pulse rounded-md bg-surface-raised/80',
        className,
      )}
      {...props}
    />
  );
}

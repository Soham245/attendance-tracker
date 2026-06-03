import { Loader2 } from 'lucide-react';
import { cn } from '../../utils/cn.js';

/**
 * Translucent overlay anchored to its nearest positioned ancestor. Use for
 * in-place "blocking" states (e.g. while a mutation is settling) without
 * unmounting the underlying content — preserves layout and scroll position.
 */
export default function LoadingOverlay({
  active = false,
  label = 'Working…',
  className,
}) {
  if (!active) return null;
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        'absolute inset-0 z-10 flex items-center justify-center',
        'rounded-[inherit] bg-surface/60 backdrop-blur-[1px]',
        'transition-opacity duration-150',
        className,
      )}
    >
      <div className="flex items-center gap-2 rounded-full bg-surface-raised/90 border border-surface-border px-3 py-1.5 text-xs text-zinc-200 shadow-card">
        <Loader2 size={14} className="animate-spin text-accent" />
        {label}
      </div>
    </div>
  );
}

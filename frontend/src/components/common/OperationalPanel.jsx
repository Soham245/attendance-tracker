import { cn } from '../../utils/cn.js';
import LoadingOverlay from './LoadingOverlay.jsx';

/**
 * Positioned wrapper for clusters of cards that share a header and may need
 * a single in-place loading state (e.g. while refetching after a mutation).
 * Defers visual hierarchy to its children — it adds no chrome of its own,
 * just spacing + overlay anchoring.
 */
export default function OperationalPanel({
  header,
  busy = false,
  busyLabel,
  className,
  children,
}) {
  return (
    <section className={cn('relative', className)}>
      {header}
      <div className={cn(header ? 'mt-0' : '')}>{children}</div>
      <LoadingOverlay active={busy} label={busyLabel} />
    </section>
  );
}

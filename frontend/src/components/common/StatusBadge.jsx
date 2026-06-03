import { cn } from '../../utils/cn.js';

// Maps the backend's session/recognition state strings to a visual treatment.
// Anything unknown falls back to the neutral "idle" style.
const STATE_STYLES = {
  idle: {
    label: 'Idle',
    dot: 'bg-zinc-500',
    text: 'text-zinc-300',
    ring: 'ring-zinc-700/60',
  },
  starting: {
    label: 'Starting',
    dot: 'bg-amber-400 animate-pulse',
    text: 'text-amber-200',
    ring: 'ring-amber-500/30',
  },
  running: {
    label: 'Running',
    dot: 'bg-emerald-400',
    text: 'text-emerald-200',
    ring: 'ring-emerald-500/30',
  },
  stopping: {
    label: 'Stopping',
    dot: 'bg-amber-400 animate-pulse',
    text: 'text-amber-200',
    ring: 'ring-amber-500/30',
  },
  stopped: {
    label: 'Stopped',
    dot: 'bg-zinc-500',
    text: 'text-zinc-300',
    ring: 'ring-zinc-700/60',
  },
  failed: {
    label: 'Failed',
    dot: 'bg-rose-500',
    text: 'text-rose-200',
    ring: 'ring-rose-500/30',
  },
  error: {
    label: 'Error',
    dot: 'bg-rose-500',
    text: 'text-rose-200',
    ring: 'ring-rose-500/30',
  },
};

export default function StatusBadge({ state, label, className }) {
  const style = STATE_STYLES[state] ?? STATE_STYLES.idle;
  return (
    <span
      className={cn(
        'inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs ring-1',
        'bg-surface-raised',
        style.text,
        style.ring,
        className,
      )}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', style.dot)} />
      {label ?? style.label}
    </span>
  );
}

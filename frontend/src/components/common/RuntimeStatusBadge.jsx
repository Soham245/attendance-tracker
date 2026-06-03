import { cn } from '../../utils/cn.js';

/**
 * Unified status badge for runtime-style states (sessions, recognition, workers).
 * Slightly more granular than StatusBadge — exposes a `size` knob and accepts
 * any state string. Unknown states render as neutral grey so the UI keeps
 * rendering even if the backend introduces a new state we haven't catalogued.
 */
const STATES = {
  idle:     { label: 'Idle',     dot: 'bg-zinc-500',                text: 'text-zinc-300',    ring: 'ring-zinc-700/60' },
  starting: { label: 'Starting', dot: 'bg-amber-400 animate-pulse', text: 'text-amber-200',   ring: 'ring-amber-500/30' },
  running:  { label: 'Running',  dot: 'bg-emerald-400',             text: 'text-emerald-200', ring: 'ring-emerald-500/30' },
  stopping: { label: 'Stopping', dot: 'bg-amber-400 animate-pulse', text: 'text-amber-200',   ring: 'ring-amber-500/30' },
  stopped:  { label: 'Stopped',  dot: 'bg-zinc-500',                text: 'text-zinc-300',    ring: 'ring-zinc-700/60' },
  failed:   { label: 'Failed',   dot: 'bg-rose-500',                text: 'text-rose-200',    ring: 'ring-rose-500/30' },
  error:    { label: 'Error',    dot: 'bg-rose-500',                text: 'text-rose-200',    ring: 'ring-rose-500/30' },
  offline:  { label: 'Offline',  dot: 'bg-zinc-500',                text: 'text-zinc-400',    ring: 'ring-zinc-700/60' },
};

const SIZES = {
  sm: 'text-[10px] px-2 py-0.5',
  md: 'text-xs px-2.5 py-1',
};

export default function RuntimeStatusBadge({ state, label, size = 'md', className }) {
  const style = STATES[state] ?? STATES.idle;
  return (
    <span
      className={cn(
        'inline-flex items-center gap-2 rounded-full ring-1 bg-surface-raised',
        SIZES[size] ?? SIZES.md,
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

import { cn } from '../../utils/cn.js';

const STATES = {
  idle: { label: 'Idle', dot: 'bg-zinc-500', text: 'text-zinc-300', ring: 'ring-zinc-700/60' },
  running: {
    label: 'Running',
    dot: 'bg-amber-400 animate-pulse',
    text: 'text-amber-200',
    ring: 'ring-amber-500/30',
  },
  completed: {
    label: 'Completed',
    dot: 'bg-emerald-400',
    text: 'text-emerald-200',
    ring: 'ring-emerald-500/30',
  },
  failed: {
    label: 'Failed',
    dot: 'bg-rose-500',
    text: 'text-rose-200',
    ring: 'ring-rose-500/30',
  },
};

export default function TrainingStateBadge({ state, className }) {
  const style = STATES[state] ?? STATES.idle;
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
      {style.label}
    </span>
  );
}

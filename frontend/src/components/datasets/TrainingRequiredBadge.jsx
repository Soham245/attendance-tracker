import { AlertCircle, CheckCircle2 } from 'lucide-react';
import { cn } from '../../utils/cn.js';

export default function TrainingRequiredBadge({ required, className }) {
  if (required) {
    return (
      <span
        className={cn(
          'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs',
          'bg-amber-500/10 text-amber-200 ring-1 ring-amber-500/30',
          className,
        )}
      >
        <AlertCircle size={12} />
        Training required
      </span>
    );
  }
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs',
        'bg-emerald-500/10 text-emerald-200 ring-1 ring-emerald-500/30',
        className,
      )}
    >
      <CheckCircle2 size={12} />
      Up to date
    </span>
  );
}

import { AlertTriangle, X } from 'lucide-react';
import { cn } from '../../utils/cn.js';

const TONES = {
  danger: 'border-rose-500/30 bg-rose-500/10 text-rose-200',
  warning: 'border-amber-500/30 bg-amber-500/10 text-amber-200',
};

const SECONDARY = {
  danger: 'text-rose-300/80',
  warning: 'text-amber-300/80',
};

export default function ErrorStateBanner({
  title,
  message,
  tone = 'danger',
  onDismiss,
  className,
}) {
  if (!title && !message) return null;
  return (
    <div
      className={cn(
        'flex items-start gap-2 rounded-lg border px-4 py-3 text-sm',
        TONES[tone] ?? TONES.danger,
        className,
      )}
    >
      <AlertTriangle size={16} className="mt-0.5 shrink-0" />
      <div className="flex-1 min-w-0">
        {title ? <div className="font-medium">{title}</div> : null}
        {message ? (
          <div className={cn(SECONDARY[tone] ?? SECONDARY.danger, 'break-words')}>
            {message}
          </div>
        ) : null}
      </div>
      {onDismiss ? (
        <button
          type="button"
          onClick={onDismiss}
          className="text-current/70 hover:text-current transition-colors"
          aria-label="Dismiss"
        >
          <X size={14} />
        </button>
      ) : null}
    </div>
  );
}

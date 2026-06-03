import { useEffect } from 'react';
import { X } from 'lucide-react';
import { cn } from '../../utils/cn.js';

const SIZES = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
};

export default function BaseModal({
  open,
  onClose,
  title,
  subtitle,
  size = 'md',
  children,
  footer,
  closeOnBackdrop = true,
}) {
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => {
      if (e.key === 'Escape') onClose?.();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={closeOnBackdrop ? onClose : undefined}
      />
      <div
        role="dialog"
        aria-modal="true"
        className={cn(
          'relative w-full card shadow-2xl',
          'animate-[fadeIn_120ms_ease-out]',
          SIZES[size] ?? SIZES.md,
        )}
      >
        <div className="flex items-start justify-between gap-4 px-5 py-4 border-b border-surface-border">
          <div>
            {title ? (
              <h2 className="text-sm font-semibold text-zinc-100">{title}</h2>
            ) : null}
            {subtitle ? (
              <p className="mt-0.5 text-xs text-zinc-500">{subtitle}</p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-zinc-500 hover:text-zinc-200 transition-colors"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        <div className="px-5 py-4 max-h-[calc(100vh-12rem)] overflow-y-auto scrollbar-hide">{children}</div>

        {footer ? (
          <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-surface-border bg-surface-raised/40 rounded-b-xl">
            {footer}
          </div>
        ) : null}
      </div>
    </div>
  );
}

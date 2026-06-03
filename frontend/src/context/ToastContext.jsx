import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { AlertTriangle, CheckCircle2, Info, X } from 'lucide-react';
import { cn } from '../utils/cn.js';

const ToastContext = createContext(null);

const DEFAULT_DURATION = 4000;
const MAX_VISIBLE = 4;

const VARIANTS = {
  success: {
    icon: CheckCircle2,
    classes: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-100',
    iconClass: 'text-emerald-400',
  },
  error: {
    icon: AlertTriangle,
    classes: 'border-rose-500/30 bg-rose-500/10 text-rose-100',
    iconClass: 'text-rose-400',
  },
  warning: {
    icon: AlertTriangle,
    classes: 'border-amber-500/30 bg-amber-500/10 text-amber-100',
    iconClass: 'text-amber-400',
  },
  info: {
    icon: Info,
    classes: 'border-surface-border bg-surface-panel text-zinc-100',
    iconClass: 'text-accent',
  },
};

/**
 * Minimal operational toaster. Capped queue, fixed bottom-right placement,
 * subtle motion. Designed for one-line confirmations and brief failures —
 * not a generic notification framework.
 */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const timersRef = useRef(new Map());

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
    const timer = timersRef.current.get(id);
    if (timer) {
      window.clearTimeout(timer);
      timersRef.current.delete(id);
    }
  }, []);

  const push = useCallback(
    (input) => {
      const id =
        typeof crypto !== 'undefined' && crypto.randomUUID
          ? crypto.randomUUID()
          : `toast-${Date.now()}-${Math.random()}`;
      const toast = {
        id,
        variant: input.variant ?? 'info',
        title: input.title,
        description: input.description,
        duration: input.duration ?? DEFAULT_DURATION,
      };
      setToasts((prev) => [...prev, toast].slice(-MAX_VISIBLE));
      if (toast.duration > 0) {
        const timer = window.setTimeout(() => dismiss(id), toast.duration);
        timersRef.current.set(id, timer);
      }
      return id;
    },
    [dismiss],
  );

  const api = useMemo(
    () => ({
      toast: push,
      success: (title, description, opts) =>
        push({ ...opts, variant: 'success', title, description }),
      error: (title, description, opts) =>
        push({ ...opts, variant: 'error', title, description }),
      warning: (title, description, opts) =>
        push({ ...opts, variant: 'warning', title, description }),
      info: (title, description, opts) =>
        push({ ...opts, variant: 'info', title, description }),
      dismiss,
    }),
    [push, dismiss],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <Viewport toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error('useToast must be used inside <ToastProvider>');
  }
  return ctx;
}

function Viewport({ toasts, onDismiss }) {
  return (
    <div
      aria-live="polite"
      aria-atomic="false"
      className="pointer-events-none fixed bottom-4 right-4 z-[60] flex w-[min(22rem,calc(100%-2rem))] flex-col gap-2"
    >
      <AnimatePresence initial={false}>
        {toasts.map((toast) => {
          const variant = VARIANTS[toast.variant] ?? VARIANTS.info;
          const Icon = variant.icon;
          return (
            <motion.div
              key={toast.id}
              layout
              initial={{ opacity: 0, y: 8, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 4, transition: { duration: 0.12 } }}
              transition={{ duration: 0.16, ease: 'easeOut' }}
              className={cn(
                'pointer-events-auto flex items-start gap-2.5 rounded-lg border px-3.5 py-2.5 shadow-card backdrop-blur-sm',
                variant.classes,
              )}
              role="status"
            >
              <Icon size={15} className={cn('mt-0.5 shrink-0', variant.iconClass)} />
              <div className="min-w-0 flex-1">
                {toast.title ? (
                  <div className="text-xs font-medium leading-tight">
                    {toast.title}
                  </div>
                ) : null}
                {toast.description ? (
                  <div className="mt-0.5 text-[11px] leading-snug opacity-80 break-words">
                    {toast.description}
                  </div>
                ) : null}
              </div>
              <button
                type="button"
                onClick={() => onDismiss(toast.id)}
                className="shrink-0 rounded-md p-1 text-current/70 hover:text-current hover:bg-white/5 transition-colors"
                aria-label="Dismiss"
              >
                <X size={12} />
              </button>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}

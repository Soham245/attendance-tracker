import { cn } from '../../utils/cn.js';

export default function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center text-center px-6 py-12',
        className,
      )}
    >
      {Icon ? (
        <div className="grid place-items-center h-12 w-12 rounded-full bg-surface-raised border border-surface-border text-zinc-500">
          <Icon size={20} />
        </div>
      ) : null}
      {title ? (
        <h3 className="mt-4 text-sm font-medium text-zinc-200">{title}</h3>
      ) : null}
      {description ? (
        <p className="mt-1 text-xs text-zinc-500 max-w-sm">{description}</p>
      ) : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

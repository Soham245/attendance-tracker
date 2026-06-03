import { cn } from '../../utils/cn.js';

/**
 * Standard page header: title, optional eyebrow + description, right slot for
 * status indicators or actions. Pages have been replicating this pattern
 * by hand — consolidating keeps typography and spacing identical across the
 * shell.
 */
export default function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  status,
  className,
}) {
  return (
    <header
      className={cn(
        'mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between',
        className,
      )}
    >
      <div className="min-w-0">
        {eyebrow ? (
          <div className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">
            {eyebrow}
          </div>
        ) : null}
        <h1 className="text-lg font-semibold text-zinc-100 truncate">{title}</h1>
        {description ? (
          <p className="text-xs text-zinc-500 mt-0.5">{description}</p>
        ) : null}
      </div>

      {actions || status ? (
        <div className="flex items-center gap-3 shrink-0">
          {status}
          {actions}
        </div>
      ) : null}
    </header>
  );
}

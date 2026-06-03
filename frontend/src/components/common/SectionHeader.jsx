import { cn } from '../../utils/cn.js';

/**
 * Sub-section header. Smaller than PageHeader; used inside long pages to
 * group related panels (e.g. "Runtime · Active model"). Plays nicely with
 * the OperationalPanel container.
 */
export default function SectionHeader({
  title,
  description,
  right,
  className,
}) {
  return (
    <div
      className={cn(
        'mb-3 flex items-end justify-between gap-3',
        className,
      )}
    >
      <div className="min-w-0">
        <h2 className="text-sm font-medium text-zinc-200 truncate">{title}</h2>
        {description ? (
          <p className="text-[11px] text-zinc-500 mt-0.5">{description}</p>
        ) : null}
      </div>
      {right ? <div className="shrink-0">{right}</div> : null}
    </div>
  );
}

import { cn } from '../../utils/cn.js';

const WIDTHS = {
  md: 'max-w-4xl',
  lg: 'max-w-6xl',
  xl: 'max-w-7xl',
  full: 'max-w-none',
};

/**
 * Optional inner container for pages that want a different content width
 * than the layout default. AppLayout already provides the outer max-width
 * (`max-w-6xl`); this is for the rare page that needs to widen or constrain
 * further without forking the layout.
 */
export default function ContentContainer({
  width = 'lg',
  className,
  children,
}) {
  return (
    <div className={cn('mx-auto w-full', WIDTHS[width] ?? WIDTHS.lg, className)}>
      {children}
    </div>
  );
}

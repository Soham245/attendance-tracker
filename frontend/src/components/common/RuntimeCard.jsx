import Card, { CardBody, CardHeader } from './Card.jsx';
import { cn } from '../../utils/cn.js';

/**
 * Operational card with a tight header (title + optional subtitle + right slot)
 * and a `tone` accent that visually flags failure/transitional cards without
 * needing a separate red banner. Composition-friendly via `children`.
 */
const TONES = {
  neutral: '',
  success: 'ring-1 ring-emerald-500/20',
  warning: 'ring-1 ring-amber-500/20',
  danger: 'ring-1 ring-rose-500/30',
};

export default function RuntimeCard({
  title,
  subtitle,
  right,
  icon: Icon,
  tone = 'neutral',
  className,
  bodyClassName,
  children,
}) {
  return (
    <Card className={cn('p-5', TONES[tone], className)}>
      <CardHeader
        title={title}
        subtitle={subtitle}
        right={
          right ?? (Icon ? <Icon size={18} className="text-zinc-600" /> : null)
        }
      />
      <CardBody className={bodyClassName}>{children}</CardBody>
    </Card>
  );
}

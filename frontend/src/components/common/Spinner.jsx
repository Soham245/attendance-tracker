import { Loader2 } from 'lucide-react';
import { cn } from '../../utils/cn.js';

export default function Spinner({ size = 18, label, className }) {
  return (
    <div className={cn('flex items-center gap-2 text-zinc-400', className)}>
      <Loader2 size={size} className="animate-spin" />
      {label ? <span className="text-sm">{label}</span> : null}
    </div>
  );
}

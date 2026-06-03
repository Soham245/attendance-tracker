import { GraduationCap } from 'lucide-react';
import { useClassContext } from '../../context/ClassContext.jsx';

/**
 * Displays the active class for the session control card.
 *
 * Both admin and faculty select their active class from the Dashboard.
 * This component shows the locked-in selection.
 */
export default function ClassSelector({ selectedClassId, onSelect, disabled }) {
  const { activeClass, loading: ctxLoading } = useClassContext();

  if (ctxLoading) {
    return (
      <div className="flex items-center gap-2 text-xs text-zinc-500">
        <GraduationCap size={14} className="animate-pulse" />
        Loading classes...
      </div>
    );
  }

  if (!activeClass) {
    return (
      <div className="flex items-center gap-2 text-xs text-amber-400">
        <GraduationCap size={14} />
        No class selected. Pick one from your Dashboard first.
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 text-xs text-zinc-300">
      <GraduationCap size={14} className="text-accent" />
      <span className="font-mono font-medium">{activeClass.class_code}</span>
      <span className="text-zinc-500">
        {activeClass.major} · Y{activeClass.year} {activeClass.section}
      </span>
    </div>
  );
}

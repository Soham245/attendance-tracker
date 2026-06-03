import { useState } from 'react';
import { ChevronDown, ChevronRight, Settings2 } from 'lucide-react';
import RuntimePerformanceCard from './RuntimePerformanceCard.jsx';
import RecognitionQualityCard from './RecognitionQualityCard.jsx';
import RuntimeHealthCard from './RuntimeHealthCard.jsx';
import WorkerHealthCard from './WorkerHealthCard.jsx';
import QueueHealthCard from './QueueHealthCard.jsx';
import DistanceDiagnosticsPanel from './DistanceDiagnosticsPanel.jsx';

/**
 * Admin-only collapsible section containing all advanced runtime diagnostics.
 * Collapsed by default so the page stays clean for faculty operators.
 * Expanded state persists within the session (local component state).
 */
export default function AdvancedDiagnosticsSection({ status, loading }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-lg border border-surface-border bg-surface-raised/20">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center gap-2.5 px-4 py-3 text-left text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
      >
        {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        <Settings2 size={16} />
        <span className="font-medium">Advanced diagnostics</span>
        <span className="ml-auto text-[11px] text-zinc-600">Admin only</span>
      </button>

      {expanded ? (
        <div className="border-t border-surface-border px-4 pb-4 pt-4 space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <RuntimePerformanceCard status={status} />
            <RecognitionQualityCard status={status} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <RuntimeHealthCard status={status} />
            <div className="grid grid-rows-2 gap-4">
              <WorkerHealthCard status={status} />
              <QueueHealthCard status={status} />
            </div>
          </div>

          <DistanceDiagnosticsPanel status={status} />
        </div>
      ) : null}
    </div>
  );
}

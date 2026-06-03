import { Boxes } from 'lucide-react';
import RuntimeCard from '../common/RuntimeCard.jsx';
import { formatDateTime } from '../../utils/format.js';

/**
 * Surfaces the active model metadata embedded in the session status payload.
 * Now enriched with runtime backend info from runtime_metrics when available.
 */
export default function RuntimeHealthCard({ status }) {
  const model = status?.active_model;
  const backends = status?.runtime_metrics?.backends;
  const counters = status?.runtime_metrics?.counters;
  const uptime = status?.runtime_metrics?.uptime_seconds;

  return (
    <RuntimeCard
      title="Active model"
      subtitle="Currently loaded for recognition."
      icon={Boxes}
    >
      {model ? (
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <Row label="Trained" value={formatDateTime(model.trained_at)} />
          <Row label="Students" value={model.student_count ?? '—'} />
          <Row label="Images" value={model.image_count ?? '—'} />
          <Row
            label="Skipped"
            value={model.skipped_images ?? 0}
            hint={model.skipped_images > 0 ? 'unreadable' : null}
          />
          {model.version ? (
            <Row label="Version" value={model.version} />
          ) : null}
          {model.backend ? (
            <Row label="Backend" value={model.backend.toUpperCase()} />
          ) : null}
          {backends?.detector ? (
            <Row label="Detector" value={backends.detector.toUpperCase()} />
          ) : null}
          {backends?.gallery_size > 0 ? (
            <Row label="Gallery" value={`${backends.gallery_size} embeddings`} />
          ) : null}
        </dl>
      ) : (
        <div className="text-sm text-zinc-500">
          No active model. Run training to produce one.
        </div>
      )}
    </RuntimeCard>
  );
}

function Row({ label, value, hint }) {
  return (
    <>
      <dt className="text-xs text-zinc-500">{label}</dt>
      <dd className="text-sm text-zinc-100 tabular-nums">
        {value}
        {hint ? (
          <span className="ml-1 text-[10px] text-zinc-500">({hint})</span>
        ) : null}
      </dd>
    </>
  );
}

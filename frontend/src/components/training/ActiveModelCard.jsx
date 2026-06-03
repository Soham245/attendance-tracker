import { Boxes } from 'lucide-react';
import Card, { CardBody, CardHeader } from '../common/Card.jsx';
import EmptyState from '../common/EmptyState.jsx';
import { formatDateTime } from '../../utils/format.js';

export default function ActiveModelCard({ model, loading, error }) {
  return (
    <Card className="p-5">
      <CardHeader
        title="Active model"
        subtitle="Metadata for the model currently loaded by the runtime."
        right={<Boxes size={18} className="text-zinc-600" />}
      />
      <CardBody>
        {loading && !model ? (
          <div className="text-sm text-zinc-500">Loading...</div>
        ) : error ? (
          <div className="text-sm text-rose-300">Could not load model metadata.</div>
        ) : !model ? (
          <EmptyState
            icon={Boxes}
            title="No active model"
            description="Run training to produce a model. Until then, recognition will be unavailable."
          />
        ) : (
          <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
            <Row label="Trained at" value={formatDateTime(model.trained_at)} />
            <Row label="Students" value={model.student_count ?? '—'} />
            <Row label="Images" value={model.image_count ?? '—'} />
            <Row
              label="Student IDs"
              value={
                Array.isArray(model.student_ids) && model.student_ids.length > 0
                  ? model.student_ids.join(', ')
                  : '—'
              }
            />
            {model.version ? (
              <Row label="Version" value={model.version} />
            ) : null}
            {model.backend ? (
              <Row
                label="Backend"
                value={model.backend.toUpperCase()}
              />
            ) : null}
            {model.available_versions != null ? (
              <Row
                label="Retained versions"
                value={model.available_versions}
              />
            ) : null}
          </dl>
        )}
      </CardBody>
    </Card>
  );
}

function Row({ label, value }) {
  return (
    <>
      <dt className="text-xs text-zinc-500">{label}</dt>
      <dd className="text-sm text-zinc-100 tabular-nums truncate">{value}</dd>
    </>
  );
}

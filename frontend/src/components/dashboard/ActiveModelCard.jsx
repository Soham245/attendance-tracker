import { BrainCircuit } from 'lucide-react';
import Card, { CardBody, CardHeader } from '../common/Card.jsx';
import { formatDateTime } from '../../utils/format.js';

export default function ActiveModelCard({ status }) {
  const model = status?.active_model;

  return (
    <Card className="p-5">
      <CardHeader
        title="Active model"
        subtitle="Currently loaded for recognition"
        right={<BrainCircuit size={18} className="text-zinc-600" />}
      />
      <CardBody>
        {model ? (
          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            <Row label="Trained" value={formatDateTime(model.trained_at)} />
            <Row label="Students" value={model.student_count ?? '—'} />
            <Row label="Images" value={model.image_count ?? '—'} />
            <Row
              label="Skipped"
              value={model.skipped_images ?? 0}
              hint={model.skipped_images > 0 ? 'corrupted/unreadable' : null}
            />
            {model.version ? (
              <Row label="Version" value={model.version} />
            ) : null}
            {model.backend ? (
              <Row label="Backend" value={model.backend.toUpperCase()} />
            ) : null}
          </dl>
        ) : (
          <div className="text-sm text-zinc-500">
            No active model. Run training to produce one.
          </div>
        )}
      </CardBody>
    </Card>
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

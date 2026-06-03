import { BrainCircuit } from 'lucide-react';
import Card, { CardBody, CardHeader } from '../common/Card.jsx';
import TrainingStateBadge from './TrainingStateBadge.jsx';
import RunTrainingButton from './RunTrainingButton.jsx';
import { formatRelative } from '../../utils/format.js';

export default function TrainingStatusCard({
  status,
  canRun,
  onTriggered,
  onError,
}) {
  const state = status?.state ?? 'idle';

  return (
    <Card className="p-5">
      <CardHeader
        title="Training"
        subtitle="Run the face-recognition model against the current dataset."
        right={
          <div className="flex items-center gap-2">
            <TrainingStateBadge state={state} />
            <BrainCircuit size={18} className="text-zinc-600" />
          </div>
        }
      />

      <CardBody>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Stat label="Students" value={status?.student_count ?? 0} />
          <Stat label="Images" value={status?.image_count ?? 0} />
          <Stat
            label="Skipped"
            value={status?.skipped_images ?? 0}
            hint={status?.skipped_images > 0 ? 'unreadable' : null}
          />
          <Stat label="Last run" value={formatRelative(status?.last_run_at)} />
        </div>

        {status?.last_error ? (
          <div className="mt-4 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
            <span className="font-medium">Last error:</span> {status.last_error}
          </div>
        ) : null}

        {canRun ? (
          <div className="mt-5 flex items-center justify-between gap-3">
            <p className="text-xs text-zinc-500">
              Training reloads the active model when it completes. The desktop
              runtime keeps recognition available throughout.
            </p>
            <RunTrainingButton
              state={state}
              onTriggered={onTriggered}
              onError={onError}
            />
          </div>
        ) : null}
      </CardBody>
    </Card>
  );
}

function Stat({ label, value, hint }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-zinc-500">
        {label}
      </div>
      <div className="mt-0.5 text-base text-zinc-100 tabular-nums">
        {value}
        {hint ? (
          <span className="ml-1 text-[10px] text-zinc-500">({hint})</span>
        ) : null}
      </div>
    </div>
  );
}

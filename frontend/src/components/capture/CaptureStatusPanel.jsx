import { Camera, Database, Image as ImageIcon, Compass } from 'lucide-react';
import CaptureStateBadge from './CaptureStateBadge.jsx';
import CaptureProgress from './CaptureProgress.jsx';
import { formatRelative } from '../../utils/format.js';

const STATE_HINTS = {
  idle: 'Ready for guided enrollment. Press Start to begin.',
  starting: 'Opening the camera on the backend…',
  capturing: 'Follow the on-screen instructions. Hold steady when the frame turns green.',
  stopping: 'Releasing the camera…',
  completed: 'Enrollment complete. Re-run training to incorporate the new samples.',
  failed: 'The backend runtime hit an error. Check the message below and retry.',
};

export default function CaptureStatusPanel({ status, polling, pollError }) {
  const state = status?.state ?? 'idle';
  const datasetCount = status?.dataset_image_count ?? 0;
  const started = status?.started_at;
  const phaseIndex = status?.phase_index ?? 0;
  const phaseCount = 4;
  const phaseInstruction = status?.phase_instruction;
  const samplesInPhase = status?.samples_in_phase ?? 0;
  const samplesPerPhase = status?.samples_per_phase ?? 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <CaptureStateBadge state={state} />
        <RuntimeMeta polling={polling} pollError={pollError} />
      </div>

      <p className="text-xs text-zinc-400 leading-relaxed">
        {STATE_HINTS[state] ?? STATE_HINTS.idle}
      </p>

      <CaptureProgress status={status} />

      {state === 'capturing' && phaseInstruction ? (
        <div className="rounded-lg border border-accent/30 bg-accent/10 px-3 py-2.5">
          <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-zinc-500 mb-1">
            <Compass size={11} />
            Phase {phaseIndex + 1} of {phaseCount}
          </div>
          <div className="text-sm font-medium text-zinc-100">
            {phaseInstruction}
          </div>
          <div className="mt-1 flex items-center gap-1.5">
            {Array.from({ length: samplesPerPhase }, (_, i) => (
              <div
                key={i}
                className={
                  'h-1.5 w-4 rounded-full ' +
                  (i < samplesInPhase ? 'bg-emerald-400' : 'bg-zinc-700')
                }
              />
            ))}
            <span className="ml-1 text-[10px] text-zinc-500 tabular-nums">
              {samplesInPhase}/{samplesPerPhase}
            </span>
          </div>
        </div>
      ) : null}

      {status?.quality_guidance && state === 'capturing' ? (
        <div className="text-xs text-zinc-400">
          <span className="text-zinc-500 uppercase tracking-wider text-[10px]">Guidance: </span>
          {status.quality_guidance}
        </div>
      ) : null}

      <dl className="grid grid-cols-2 gap-3 text-xs">
        <Stat
          icon={Camera}
          label="Camera"
          value={status?.camera_active ? 'Active' : 'Inactive'}
          tone={status?.camera_active ? 'good' : 'muted'}
        />
        <Stat
          icon={ImageIcon}
          label="Started"
          value={started ? formatRelative(started) : '—'}
        />
        <Stat
          icon={Database}
          label="Total in dataset"
          value={datasetCount}
        />
        <Stat
          icon={ImageIcon}
          label="Last sample"
          value={status?.last_sample_filename ? 'saved' : '—'}
          tone={status?.last_sample_filename ? 'good' : 'muted'}
        />
      </dl>
    </div>
  );
}

function Stat({ icon: Icon, label, value, tone }) {
  const valueColor =
    tone === 'good'
      ? 'text-emerald-200'
      : tone === 'muted'
        ? 'text-zinc-400'
        : 'text-zinc-100';
  return (
    <div className="rounded-lg border border-surface-border bg-surface-raised/50 px-3 py-2">
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-zinc-500">
        <Icon size={11} />
        {label}
      </div>
      <div className={`mt-0.5 text-sm font-medium truncate ${valueColor}`}>
        {value || '—'}
      </div>
    </div>
  );
}

function RuntimeMeta({ polling, pollError }) {
  if (pollError) {
    return (
      <span className="text-[11px] text-rose-300">Status poll failed</span>
    );
  }
  return (
    <span className="text-[11px] text-zinc-500">
      {polling ? 'Live' : 'Paused'}
    </span>
  );
}

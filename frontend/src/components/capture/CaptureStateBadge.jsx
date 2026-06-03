import RuntimeStatusBadge from '../common/RuntimeStatusBadge.jsx';

/**
 * Maps capture runtime state -> RuntimeStatusBadge styles. The shared badge
 * already understands {idle, starting, running, stopping, failed}; capture
 * adds two extra terminal states (`capturing`, `completed`) that we coerce
 * into the closest equivalents so the visual language stays consistent.
 */
const STATE_TO_BADGE = {
  idle: { state: 'idle', label: 'Idle' },
  starting: { state: 'starting', label: 'Starting' },
  capturing: { state: 'running', label: 'Capturing' },
  stopping: { state: 'stopping', label: 'Stopping' },
  completed: { state: 'running', label: 'Completed' },
  failed: { state: 'failed', label: 'Failed' },
};

export default function CaptureStateBadge({ state, size = 'md', className }) {
  const mapped = STATE_TO_BADGE[state] ?? STATE_TO_BADGE.idle;
  return (
    <RuntimeStatusBadge
      state={mapped.state}
      label={mapped.label}
      size={size}
      className={className}
    />
  );
}

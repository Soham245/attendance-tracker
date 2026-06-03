import { Play, RotateCcw, Square } from 'lucide-react';
import Button from '../common/Button.jsx';
import LoadingButton from '../common/LoadingButton.jsx';

const TRANSITIONAL = new Set(['starting', 'stopping']);

/**
 * Footer controls for the guided enrollment modal.
 * Target samples are now computed by the backend (phases × samples_per_phase),
 * so the input field is removed.
 */
export default function CaptureControls({
  state,
  onStart,
  onStop,
  onClose,
  submitting,
  canControl,
}) {
  const inTransition = TRANSITIONAL.has(state);
  const isCapturing = state === 'capturing';

  return (
    <div className="flex items-center justify-end gap-2">
      <Button variant="ghost" onClick={onClose} disabled={submitting || isCapturing}>
        Close
      </Button>

      {isCapturing || state === 'stopping' ? (
        <LoadingButton
          loading={submitting && !isCapturing}
          disabled={state === 'stopping' && !isCapturing}
          onClick={onStop}
          className="bg-rose-600 hover:bg-rose-500 text-white"
        >
          {!submitting ? <Square size={14} /> : null}
          Stop capture
        </LoadingButton>
      ) : (
        <LoadingButton
          loading={submitting}
          disabled={inTransition || !canControl}
          onClick={onStart}
          className="bg-accent hover:bg-accent-hover text-white"
        >
          {!submitting ? (
            state === 'completed' || state === 'failed' ? (
              <RotateCcw size={14} />
            ) : (
              <Play size={14} />
            )
          ) : null}
          {state === 'completed'
            ? 'Enroll again'
            : state === 'failed'
              ? 'Retry'
              : 'Start enrollment'}
        </LoadingButton>
      )}
    </div>
  );
}

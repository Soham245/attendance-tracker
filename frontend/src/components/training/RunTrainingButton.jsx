import { useState } from 'react';
import { Play } from 'lucide-react';
import LoadingButton from '../common/LoadingButton.jsx';
import { runTraining } from '../../services/trainingService.js';
import { errorMessage } from '../../services/api.js';

export default function RunTrainingButton({ disabled, state, onTriggered, onError }) {
  const [submitting, setSubmitting] = useState(false);
  const isRunning = state === 'running';

  const handleClick = async () => {
    if (submitting || isRunning) return;
    setSubmitting(true);
    try {
      await runTraining();
      onTriggered?.();
    } catch (err) {
      onError?.(errorMessage(err, 'Could not start training.'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <LoadingButton
      loading={submitting}
      disabled={disabled || isRunning}
      onClick={handleClick}
      className="bg-accent hover:bg-accent-hover text-white"
    >
      {!submitting ? <Play size={14} /> : null}
      {isRunning ? 'Training…' : 'Run training'}
    </LoadingButton>
  );
}

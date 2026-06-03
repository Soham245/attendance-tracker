import { useCallback, useEffect, useRef, useState } from 'react';
import TrainingStatusCard from '../components/training/TrainingStatusCard.jsx';
import ActiveModelCard from '../components/training/ActiveModelCard.jsx';
import ModelVersionsCard from '../components/training/ModelVersionsCard.jsx';
import { useTrainingStatus } from '../hooks/useTrainingStatus.js';
import { fetchActiveModel } from '../services/trainingService.js';
import { errorMessage } from '../services/api.js';
import { useAuth } from '../hooks/useAuth.js';
import { useToast } from '../context/ToastContext.jsx';
import PageHeader from '../components/common/PageHeader.jsx';
import PollingStateIndicator from '../components/common/PollingStateIndicator.jsx';
import ErrorStateBanner from '../components/common/ErrorStateBanner.jsx';

export default function Training() {
  const { user } = useAuth();
  const canRun = user?.role === 'admin';
  const toast = useToast();

  // While idle we don't need an aggressive cadence; while running we want
  // snappier feedback. The hook handles tab visibility for us.
  const { data: status, error: statusError, loading: statusLoading } = useTrainingStatus({
    intervalMs: 4000,
  });

  const [model, setModel] = useState(null);
  const [modelLoading, setModelLoading] = useState(true);
  const [modelError, setModelError] = useState(null);
  const [actionError, setActionError] = useState(null);

  // Bump this counter to force the versions card to refresh.
  const [versionsKey, setVersionsKey] = useState(0);

  const refreshModel = useCallback(async () => {
    setModelLoading(true);
    try {
      const data = await fetchActiveModel();
      setModel(data);
      setModelError(null);
    } catch (err) {
      setModelError(err);
    } finally {
      setModelLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshModel();
  }, [refreshModel]);

  // After a "running -> completed" transition the active model has been
  // replaced on disk; refresh metadata so the UI reflects it. Done via a ref
  // so we react only on the edge, not on every poll tick.
  const prevState = useRef(status?.state);
  useEffect(() => {
    const before = prevState.current;
    const now = status?.state;
    if (before === 'running' && now === 'completed') {
      refreshModel();
      setVersionsKey((k) => k + 1);
      toast.success('Training complete', 'The active model has been reloaded.');
    } else if (before === 'running' && now === 'failed') {
      refreshModel();
      toast.error('Training failed', status?.last_error ?? undefined);
    } else if (before !== 'running' && now === 'running') {
      toast.info('Training started');
    }
    prevState.current = now;
  }, [status?.state, status?.last_error, refreshModel, toast]);

  return (
    <div>
      <PageHeader
        title="Training"
        description="Trigger model training, inspect the active model, and manage version history."
        status={
          <PollingStateIndicator loading={statusLoading} error={statusError} />
        }
      />

      {actionError ? (
        <ErrorStateBanner
          tone="danger"
          message={actionError}
          onDismiss={() => setActionError(null)}
          className="mb-4"
        />
      ) : null}

      {statusError && !status ? (
        <ErrorStateBanner
          tone="danger"
          title="Cannot reach training service"
          message={errorMessage(statusError)}
          className="mb-4"
        />
      ) : null}

      <div className="space-y-4">
        <TrainingStatusCard
          status={status}
          canRun={canRun}
          onTriggered={() => {
            setActionError(null);
          }}
          onError={(msg) => {
            setActionError(msg);
            toast.error('Could not start training', msg);
          }}
        />

        <ActiveModelCard model={model} loading={modelLoading} error={modelError} />

        <ModelVersionsCard
          key={versionsKey}
          onRollback={() => {
            refreshModel();
          }}
        />
      </div>
    </div>
  );
}

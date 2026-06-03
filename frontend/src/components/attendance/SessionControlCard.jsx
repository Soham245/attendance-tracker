import { useState } from 'react';
import { Play, Square, Users } from 'lucide-react';
import RuntimeCard from '../common/RuntimeCard.jsx';
import LoadingButton from '../common/LoadingButton.jsx';
import RuntimeStatusBadge from '../common/RuntimeStatusBadge.jsx';
import RuntimeTransitionWrapper from '../common/RuntimeTransitionWrapper.jsx';
import ClassSelector from './ClassSelector.jsx';
import { startSession, stopSession } from '../../services/sessionService.js';
import { errorMessage } from '../../services/api.js';
import { useAuth } from '../../hooks/useAuth.js';
import { useClassContext } from '../../context/ClassContext.jsx';
import { formatRelative } from '../../utils/format.js';

/**
 * Backend `session_state` values: idle | starting | running | stopping | failed.
 * "starting" and "stopping" are transitional — buttons stay disabled so we don't
 * fire conflicting POSTs while the runtime is mid-transition. The action's own
 * in-flight state is tracked locally (it's invisible from session_state alone).
 */
const TRANSITIONAL = new Set(['starting', 'stopping']);

export default function SessionControlCard({
  status,
  canControl,
  onActionError,
  onTriggered,
}) {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const { activeClass } = useClassContext();

  const [submitting, setSubmitting] = useState(false);
  // Pre-select from active class context for both roles.
  const [selectedClassId, setSelectedClassId] = useState(
    activeClass ? activeClass.class_id : null,
  );
  const state = status?.session_state ?? 'idle';
  const isRunning = state === 'running';
  const isIdle = state === 'idle' || state === 'failed';
  const inTransition = TRANSITIONAL.has(state);
  const startedAt = status?.recognition?.started_at;
  const activeSession = status?.active_session;

  const handleStart = () => action(() => startSession({ classId: selectedClassId }));
  const handleStop = () => action(stopSession);

  const action = async (fn) => {
    if (submitting || inTransition) return;
    setSubmitting(true);
    try {
      await fn();
      onTriggered?.();
    } catch (err) {
      onActionError?.(errorMessage(err, 'Action failed'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <RuntimeCard
      title="Session control"
      subtitle="Start or stop the recognition runtime."
      right={<RuntimeStatusBadge state={state} />}
      tone={state === 'failed' ? 'danger' : isRunning ? 'success' : 'neutral'}
    >
      <div className="flex flex-col gap-4">
        {/* Active session info */}
        {activeSession && !isIdle ? (
          <div className="flex items-center gap-3 rounded-md bg-zinc-800/50 px-3 py-2 text-xs">
            <Users size={14} className="text-accent" />
            <div>
              <span className="font-medium text-zinc-200">{activeSession.session_name}</span>
              <span className="ml-2 text-zinc-500">
                {activeSession.allowed_count} student{activeSession.allowed_count !== 1 ? 's' : ''} enrolled
              </span>
            </div>
          </div>
        ) : null}

        {/* Class selector — only shown when idle and user can control */}
        {canControl && isIdle ? (
          <ClassSelector
            selectedClassId={selectedClassId}
            onSelect={setSelectedClassId}
            disabled={submitting || inTransition}
          />
        ) : null}

        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <RuntimeTransitionWrapper state={state}>
            <div className="text-xs text-zinc-400">
              {isRunning ? (
                <>
                  <span className="text-zinc-300">Running</span>
                  {startedAt ? (
                    <> · started {formatRelative(startedAt)}</>
                  ) : null}
                </>
              ) : inTransition ? (
                <>The runtime is transitioning. Hold on...</>
              ) : state === 'failed' ? (
                <>The runtime stopped after an error. Start again when ready.</>
              ) : (
                <>Select a class and start a session to begin recognition.</>
              )}
            </div>
          </RuntimeTransitionWrapper>

          {canControl ? (
            <div className="flex items-center gap-2">
              {isRunning || state === 'stopping' ? (
                <LoadingButton
                  loading={submitting && !isRunning}
                  disabled={inTransition && !isRunning}
                  onClick={handleStop}
                  className="bg-rose-600 hover:bg-rose-500 text-white"
                >
                  {!submitting ? <Square size={14} /> : null}
                  Stop session
                </LoadingButton>
              ) : (
                <LoadingButton
                  loading={submitting}
                  disabled={inTransition || !selectedClassId}
                  onClick={handleStart}
                  className="bg-accent hover:bg-accent-hover text-white"
                >
                  {!submitting ? <Play size={14} /> : null}
                  Start session
                </LoadingButton>
              )}
            </div>
          ) : (
            <div className="text-[11px] text-zinc-500">
              {isRunning
                ? null
                : 'Faculty or admin role required to control the session.'}
            </div>
          )}
        </div>
      </div>
    </RuntimeCard>
  );
}

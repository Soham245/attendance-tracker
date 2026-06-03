import { useEffect, useRef, useState } from 'react';
import { useSessionStatus } from '../hooks/useSessionStatus.js';
import { useAuth } from '../hooks/useAuth.js';
import { useToast } from '../context/ToastContext.jsx';
import { useHotkey } from '../hooks/useHotkey.js';
import PageHeader from '../components/common/PageHeader.jsx';
import PollingStateIndicator from '../components/common/PollingStateIndicator.jsx';
import ConnectionStatusBanner from '../components/common/ConnectionStatusBanner.jsx';
import SessionControlCard from '../components/attendance/SessionControlCard.jsx';
import OperationalSummaryCard from '../components/attendance/OperationalSummaryCard.jsx';
import RecognitionFeed from '../components/attendance/RecognitionFeed.jsx';
import RecognitionPreview from '../components/attendance/RecognitionPreview.jsx';
import RuntimeErrorBanner from '../components/attendance/RuntimeErrorBanner.jsx';
import StaleModelBanner from '../components/dashboard/StaleModelBanner.jsx';
import AdvancedDiagnosticsSection from '../components/attendance/AdvancedDiagnosticsSection.jsx';

/**
 * Operational console for the live attendance runtime. Faculty users see a
 * clean view: preview, session controls, operational summary, and recent
 * recognitions. Admins additionally get a collapsible advanced diagnostics
 * section with latency breakdowns, similarity distributions, and backend
 * telemetry — collapsed by default.
 */
export default function LiveAttendance() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const toast = useToast();

  const { data: status, error: pollError, loading, refresh, boost } = useSessionStatus();

  const [actionError, setActionError] = useState(null);

  // Surface backend state transitions as one-off toasts.
  const prevStateRef = useRef(status?.session_state);
  useEffect(() => {
    const before = prevStateRef.current;
    const now = status?.session_state;
    if (before && now && before !== now) {
      if (now === 'running' && before === 'starting') {
        toast.success('Session running', 'Recognition pipeline is live.');
      } else if (now === 'idle' && before === 'stopping') {
        toast.info('Session stopped');
      } else if (now === 'failed') {
        toast.error('Session failed', status?.last_error ?? 'Runtime reported an error.');
      }
    }
    prevStateRef.current = now;
  }, [status?.session_state, status?.last_error, toast]);

  useHotkey('r', refresh, { meta: true });

  const canControl = isAdmin || user?.role === 'faculty';

  return (
    <div>
      <PageHeader
        title="Live attendance"
        description={
          isAdmin
            ? 'Control the recognition session and monitor runtime health.'
            : 'Start a session for your class and monitor recognition.'
        }
        status={<PollingStateIndicator loading={loading} error={pollError} />}
      />

      <ConnectionStatusBanner
        error={pollError}
        hasData={Boolean(status)}
        className="mb-4"
      />

      <RuntimeErrorBanner
        status={status}
        pollError={pollError}
        actionError={actionError}
        onDismissAction={() => setActionError(null)}
      />

      <StaleModelBanner status={status} />

      <div className="mt-4 space-y-4">
        {/* Session controls — faculty and admins can control */}
        <SessionControlCard
          status={status}
          canControl={canControl}
          onActionError={(msg) => {
            setActionError(msg);
            toast.error('Action failed', msg);
          }}
          onTriggered={() => {
            setActionError(null);
            refresh();
            boost();
          }}
        />

        {/* Camera preview — visible to all */}
        <RecognitionPreview sessionState={status?.session_state} />

        {/* Faculty-friendly operational summary */}
        <OperationalSummaryCard status={status} />

        {/* Recent recognitions feed — visible to all */}
        <RecognitionFeed status={status} loading={loading} />

        {/* Admin-only: advanced diagnostics (collapsed by default) */}
        {isAdmin ? (
          <AdvancedDiagnosticsSection status={status} loading={loading} />
        ) : null}
      </div>
    </div>
  );
}

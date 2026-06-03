import ErrorStateBanner from '../common/ErrorStateBanner.jsx';
import { errorMessage } from '../../services/api.js';

/**
 * Coalesces three runtime error sources into a single banner:
 *   1. transport error from the status poller (backend unreachable)
 *   2. backend-reported `last_error` (e.g. camera failed to open)
 *   3. action error from start/stop POSTs
 *
 * Renders nothing when there's nothing to report so callers can drop it in
 * unconditionally.
 */
export default function RuntimeErrorBanner({
  status,
  pollError,
  actionError,
  onDismissAction,
}) {
  if (pollError && !status) {
    return (
      <ErrorStateBanner
        tone="danger"
        title="Cannot reach the runtime"
        message={errorMessage(pollError, 'Polling failed')}
      />
    );
  }

  if (actionError) {
    return (
      <ErrorStateBanner
        tone="danger"
        title="Action failed"
        message={actionError}
        onDismiss={onDismissAction}
      />
    );
  }

  if (status?.last_error) {
    return (
      <ErrorStateBanner
        tone="warning"
        title="Runtime reported an error"
        message={status.last_error}
      />
    );
  }

  return null;
}

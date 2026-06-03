import ErrorStateBanner from '../common/ErrorStateBanner.jsx';

/**
 * Capture error surface. Two sources:
 *   1. `actionError` — POST /capture/start|stop returned a non-2xx.
 *   2. `status.last_error` — backend runtime reported a failure during capture.
 *
 * Browser camera errors are gone — the backend owns the webcam entirely.
 */
export default function CaptureErrorBanner({
  actionError,
  status,
  onDismissAction,
}) {
  if (actionError) {
    return (
      <ErrorStateBanner
        tone="danger"
        title="Could not start capture"
        message={actionError}
        onDismiss={onDismissAction}
      />
    );
  }
  if (status?.state === 'failed' && status.last_error) {
    return (
      <ErrorStateBanner
        tone="danger"
        title="Capture failed"
        message={status.last_error}
      />
    );
  }
  return null;
}

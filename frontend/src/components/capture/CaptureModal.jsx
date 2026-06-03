import { useCallback, useEffect, useRef, useState } from 'react';
import { AlertTriangle, Camera } from 'lucide-react';
import BaseModal from '../common/BaseModal.jsx';
import ConfirmDialog from '../common/ConfirmDialog.jsx';
import CapturePreview from './CapturePreview.jsx';
import CaptureStatusPanel from './CaptureStatusPanel.jsx';
import CaptureControls from './CaptureControls.jsx';
import CaptureErrorBanner from './CaptureErrorBanner.jsx';
import CaptureCompletionView from './CaptureCompletionView.jsx';
import { useCaptureStatus, isCaptureActive } from '../../hooks/useCaptureStatus.js';
import {
  startCapture,
  stopCapture,
} from '../../services/captureService.js';
import { errorMessage } from '../../services/api.js';
import { useToast } from '../../context/ToastContext.jsx';

/**
 * Guided enrollment modal — pure MJPEG viewer.
 *
 * The backend owns the webcam entirely. This modal:
 *   1. POSTs /capture/start to begin the guided enrollment
 *   2. Renders the backend's annotated MJPEG stream (quality overlays,
 *      phase instructions, progress) via <img src>
 *   3. Polls /capture/status for phase state + progress
 *   4. POSTs /capture/stop on user request
 *
 * No getUserMedia, no browser camera access.
 */
export default function CaptureModal({
  open,
  student,
  canControl = true,
  onClose,
  onCompleted,
  existingImageCount = 0,
}) {
  const toast = useToast();

  const [actionError, setActionError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [showReplaceConfirm, setShowReplaceConfirm] = useState(false);

  const {
    data: status,
    error: pollError,
    loading: polling,
    refresh,
  } = useCaptureStatus({ enabled: open });

  const statusIsForThisStudent =
    !status ||
    status.student_id == null ||
    student?.id == null ||
    status.student_id === student.id;
  const effectiveStatus = statusIsForThisStudent ? status : null;

  const captureActive =
    isCaptureActive(effectiveStatus) ||
    (status && isCaptureActive(status) && !statusIsForThisStudent);

  // Reset transient state whenever the modal is freshly opened.
  useEffect(() => {
    if (open) {
      setActionError(null);
      setSubmitting(false);
      setShowReplaceConfirm(false);
    }
  }, [open, student?.id]);

  // Fire onCompleted once when capture finishes for this student.
  const completedFiredRef = useRef(false);
  useEffect(() => {
    if (!open) {
      completedFiredRef.current = false;
      return;
    }
    if (
      effectiveStatus?.state === 'completed' &&
      effectiveStatus.student_id === student?.id &&
      !completedFiredRef.current
    ) {
      completedFiredRef.current = true;
      toast.success(
        'Enrollment complete',
        `Saved ${effectiveStatus.samples_collected} sample(s) across all phases.`,
      );
      onCompleted?.();
    }
  }, [open, effectiveStatus, student, onCompleted, toast]);

  const handleStartRequest = () => {
    if (!student) return;
    // If the student already has dataset images, confirm replacement first.
    if (existingImageCount > 0) {
      setShowReplaceConfirm(true);
      return;
    }
    doStart(false);
  };

  const doStart = async (replace) => {
    setShowReplaceConfirm(false);
    setSubmitting(true);
    setActionError(null);
    completedFiredRef.current = false;

    try {
      await startCapture({ studentId: student.id, replace });
      refresh();
    } catch (err) {
      setActionError(errorMessage(err, 'Could not start capture.'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleStop = async () => {
    setSubmitting(true);
    try {
      await stopCapture();
      refresh();
    } catch (err) {
      toast.error('Could not stop capture', errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const isActive = isCaptureActive(effectiveStatus);

  const handleClose = () => {
    if (isActive) {
      toast.warning(
        'Stop capture first',
        'Press Stop to release the camera before closing.',
      );
      return;
    }
    onClose?.();
  };

  if (!student) return null;

  return (
    <>
      <BaseModal
        open={open}
        onClose={handleClose}
        size="xl"
        title={`Guided enrollment · ${student.name}`}
        subtitle={`Roll ${student.roll_number}`}
        closeOnBackdrop={!isActive}
      >
        <div className="grid gap-5 md:grid-cols-[1.4fr,1fr]">
          <div className="space-y-3">
            <CapturePreview
              captureState={effectiveStatus?.state}
              phaseInstruction={effectiveStatus?.phase_instruction}
            />
            <CaptureErrorBanner
              actionError={actionError}
              status={effectiveStatus}
              onDismissAction={() => setActionError(null)}
            />
            <CaptureCompletionView status={effectiveStatus} />
          </div>

          <CaptureStatusPanel
            status={effectiveStatus}
            polling={polling}
            pollError={pollError}
          />
        </div>

        <div className="mt-5 border-t border-surface-border pt-4">
          <CaptureControls
            state={effectiveStatus?.state ?? 'idle'}
            onStart={handleStartRequest}
            onStop={handleStop}
            onClose={handleClose}
            submitting={submitting}
            canControl={canControl}
          />
        </div>
      </BaseModal>

      <ConfirmDialog
        open={showReplaceConfirm}
        onClose={() => setShowReplaceConfirm(false)}
        onConfirm={() => doStart(true)}
        tone="warning"
        title="Replace existing enrollment?"
        confirmLabel="Replace & capture"
        description={
          <>
            This will remove the{' '}
            <span className="font-medium text-zinc-100">
              {existingImageCount} existing photo{existingImageCount === 1 ? '' : 's'}
            </span>{' '}
            and rebuild {student.name}'s face data from scratch.
          </>
        }
      />
    </>
  );
}

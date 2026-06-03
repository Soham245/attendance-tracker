import { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, Camera, RefreshCw, Trash2 } from 'lucide-react';
import BaseModal from '../common/BaseModal.jsx';
import Button from '../common/Button.jsx';
import DatasetGallery from './DatasetGallery.jsx';
import DatasetUpload from './DatasetUpload.jsx';
import TrainingRequiredBadge from './TrainingRequiredBadge.jsx';
import ConfirmDialog from '../common/ConfirmDialog.jsx';
import CaptureModal from '../capture/CaptureModal.jsx';
import {
  deleteDatasetImage,
  deleteAllDatasetImages,
  listDatasetImages,
} from '../../services/datasetService.js';
import { errorMessage } from '../../services/api.js';

export default function DatasetManagerModal({
  open,
  student,
  canMutate,
  onClose,
  onChanged,
}) {
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [pendingDeleteAll, setPendingDeleteAll] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState(null);
  const [captureOpen, setCaptureOpen] = useState(false);

  const studentId = student?.id;

  const refresh = useCallback(async () => {
    if (!studentId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await listDatasetImages(studentId);
      setImages(result?.images ?? []);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [studentId]);

  useEffect(() => {
    if (open && studentId) {
      refresh();
    } else if (!open) {
      setImages([]);
      setError(null);
      setPendingDelete(null);
      setPendingDeleteAll(false);
    }
  }, [open, studentId, refresh]);

  const handleUploaded = () => {
    refresh();
    onChanged?.();
  };

  const handleConfirmDelete = async () => {
    if (!pendingDelete || !studentId) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteDatasetImage(studentId, pendingDelete.filename);
      setPendingDelete(null);
      await refresh();
      onChanged?.();
    } catch (err) {
      setDeleteError(errorMessage(err, 'Could not delete the image.'));
    } finally {
      setDeleting(false);
    }
  };

  const handleConfirmDeleteAll = async () => {
    if (!studentId) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteAllDatasetImages(studentId);
      setPendingDeleteAll(false);
      await refresh();
      onChanged?.();
    } catch (err) {
      setDeleteError(errorMessage(err, 'Could not delete images.'));
    } finally {
      setDeleting(false);
    }
  };

  if (!student) return null;

  return (
    <>
      <BaseModal
        open={open}
        onClose={onClose}
        size="xl"
        title={`Dataset · ${student.name}`}
        subtitle={`Roll ${student.roll_number}`}
        footer={
          <>
            <div className="mr-auto">
              <TrainingRequiredBadge required={Boolean(student.training_required)} />
            </div>
            <Button variant="ghost" onClick={onClose}>
              Close
            </Button>
          </>
        }
      >
        <div className="space-y-5">
          {canMutate ? (
            <div className="flex gap-3 items-stretch">
              <button
                type="button"
                onClick={() => setCaptureOpen(true)}
                className="flex-1 min-w-0 flex flex-col items-center justify-center gap-2 px-6 py-8 rounded-xl border-2 border-dashed border-surface-border bg-surface-raised/40 hover:bg-surface-hover/40 hover:border-accent/40 transition-colors cursor-pointer text-center"
              >
                <div className="grid place-items-center h-10 w-10 rounded-full bg-accent/15 text-accent">
                  <Camera size={18} />
                </div>
                <div className="text-sm text-zinc-200">Capture from webcam</div>
                <div className="text-[11px] text-zinc-500">
                  Guided enrollment with live preview.
                </div>
              </button>
              <div className="flex-1 min-w-0">
                <DatasetUpload
                  studentId={studentId}
                  disabled={!canMutate}
                  onUploaded={handleUploaded}
                />
              </div>
            </div>
          ) : (
            <div className="text-xs text-zinc-500">
              You don't have permission to modify this dataset.
            </div>
          )}

          <div className="flex items-center justify-between gap-2">
            <div className="text-xs text-zinc-400">
              {loading ? 'Loading…' : `${images.length} image${images.length === 1 ? '' : 's'}`}
            </div>
            <div className="flex items-center gap-2">
              {canMutate && images.length > 0 ? (
                <Button
                  variant="ghost"
                  onClick={() => setPendingDeleteAll(true)}
                  className="!py-1 !px-2 text-xs text-rose-300 hover:text-rose-200"
                  title="Delete all images"
                >
                  <Trash2 size={12} />
                  Delete all
                </Button>
              ) : null}
              <Button
                variant="ghost"
                onClick={refresh}
                disabled={loading}
                className="!py-1 !px-2 text-xs"
              >
                <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
                Refresh
              </Button>
            </div>
          </div>

          {error ? (
            <div className="flex items-start gap-2 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
              <AlertTriangle size={14} className="mt-0.5 shrink-0" />
              <span>{errorMessage(error, 'Could not load dataset images.')}</span>
            </div>
          ) : null}

          <DatasetGallery
            images={images}
            loading={loading}
            canMutate={canMutate}
            onDelete={(img) => setPendingDelete(img)}
          />
        </div>
      </BaseModal>

      <CaptureModal
        open={captureOpen}
        student={student}
        canControl={canMutate}
        existingImageCount={images.length}
        onClose={() => setCaptureOpen(false)}
        onCompleted={() => {
          refresh();
          onChanged?.();
        }}
      />

      {/* Single image delete */}
      <ConfirmDialog
        open={Boolean(pendingDelete)}
        onClose={() => {
          setPendingDelete(null);
          setDeleteError(null);
        }}
        onConfirm={handleConfirmDelete}
        loading={deleting}
        error={deleteError}
        tone="danger"
        title="Delete image"
        confirmLabel="Delete"
        description={
          pendingDelete ? (
            <>
              Permanently remove{' '}
              <span className="font-medium text-zinc-100">
                {pendingDelete.filename}
              </span>{' '}
              from this student's dataset?
            </>
          ) : null
        }
      />

      {/* Delete all confirmation */}
      <ConfirmDialog
        open={pendingDeleteAll}
        onClose={() => {
          setPendingDeleteAll(false);
          setDeleteError(null);
        }}
        onConfirm={handleConfirmDeleteAll}
        loading={deleting}
        error={deleteError}
        tone="danger"
        title="Delete all images"
        confirmLabel="Delete all"
        description={
          <>
            Permanently remove all{' '}
            <span className="font-medium text-zinc-100">
              {images.length} image{images.length === 1 ? '' : 's'}
            </span>{' '}
            from {student.name}'s dataset? This cannot be undone.
          </>
        }
      />
    </>
  );
}

import { useCallback, useEffect, useState } from 'react';
import { History, RotateCcw, Trash2 } from 'lucide-react';
import Card, { CardBody, CardHeader } from '../common/Card.jsx';
import EmptyState from '../common/EmptyState.jsx';
import ConfirmDialog from '../common/ConfirmDialog.jsx';
import {
  fetchModelVersions,
  rollbackModel,
  deleteModelVersion,
  dropAllModels,
} from '../../services/trainingService.js';
import { errorMessage } from '../../services/api.js';
import { useToast } from '../../context/ToastContext.jsx';
import { useAuth } from '../../hooks/useAuth.js';

export default function ModelVersionsCard({ onRollback }) {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const toast = useToast();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [rolling, setRolling] = useState(null);
  const [deleting, setDeleting] = useState(null);

  // Confirmation targets
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [showDropAll, setShowDropAll] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchModelVersions();
      setData(result);
    } catch {
      // silently ignore — versions panel is non-critical
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const handleRollback = async (versionId) => {
    if (rolling) return;
    setRolling(versionId);
    try {
      await rollbackModel(versionId);
      toast.success('Rollback complete', `Active model set to ${versionId}.`);
      await refresh();
      onRollback?.();
    } catch (err) {
      toast.error('Rollback failed', errorMessage(err));
    } finally {
      setRolling(null);
    }
  };

  const handleDelete = async (versionId) => {
    setDeleteTarget(null);
    setDeleting(versionId);
    try {
      await deleteModelVersion(versionId);
      toast.success('Version deleted', `${versionId} removed.`);
      await refresh();
      onRollback?.();
    } catch (err) {
      toast.error('Delete failed', errorMessage(err));
    } finally {
      setDeleting(null);
    }
  };

  const handleDropAll = async () => {
    setShowDropAll(false);
    setDeleting('all');
    try {
      await dropAllModels();
      toast.success('All models dropped', 'Version counter reset to v001.');
      await refresh();
      onRollback?.();
    } catch (err) {
      toast.error('Drop failed', errorMessage(err));
    } finally {
      setDeleting(null);
    }
  };

  const versions = data?.versions ?? [];
  const busy = !!rolling || !!deleting;

  return (
    <>
      <Card className="p-5">
        <CardHeader
          title="Model versions"
          subtitle="Retained model history with rollback"
          right={
            <div className="flex items-center gap-2">
              {isAdmin && versions.length > 0 ? (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => setShowDropAll(true)}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-md
                    text-rose-400/80 hover:text-rose-300 hover:bg-rose-500/10
                    disabled:opacity-40 disabled:cursor-not-allowed
                    transition-colors"
                >
                  <Trash2 size={12} />
                  Drop all
                </button>
              ) : null}
              <History size={18} className="text-zinc-600" />
            </div>
          }
        />
        <CardBody>
          {loading && !data ? (
            <div className="text-sm text-zinc-500">Loading...</div>
          ) : versions.length === 0 ? (
            <EmptyState
              icon={History}
              title="No versions yet"
              description="Train a model to create the first version."
            />
          ) : (
            <ul className="divide-y divide-surface-border">
              {versions.map((v) => {
                const isActive = v.status === 'active';
                return (
                  <li
                    key={v.id}
                    className="flex items-center justify-between gap-3 py-3 text-sm"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-zinc-100">{v.id}</span>
                        <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-surface-raised text-zinc-400">
                          {v.backend}
                        </span>
                        {isActive ? (
                          <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-emerald-900/40 text-emerald-300">
                            active
                          </span>
                        ) : null}
                      </div>
                      <div className="text-[11px] text-zinc-500 mt-0.5">
                        {v.student_count} students · {v.image_count} images
                        {v.created_at ? ` · ${new Date(v.created_at).toLocaleDateString()}` : ''}
                      </div>
                    </div>

                    {isAdmin ? (
                      <div className="flex items-center gap-1.5">
                        {!isActive ? (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => handleRollback(v.id)}
                            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-md
                              border border-surface-border text-zinc-300
                              hover:bg-surface-raised hover:text-zinc-100
                              disabled:opacity-40 disabled:cursor-not-allowed
                              transition-colors"
                          >
                            <RotateCcw size={12} className={rolling === v.id ? 'animate-spin' : ''} />
                            Rollback
                          </button>
                        ) : null}
                        {!isActive ? (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => setDeleteTarget(v)}
                            className="flex items-center gap-1.5 px-2 py-1.5 text-xs rounded-md
                              text-rose-400/80 hover:text-rose-300 hover:bg-rose-500/10
                              disabled:opacity-40 disabled:cursor-not-allowed
                              transition-colors"
                            title={`Delete ${v.id}`}
                          >
                            <Trash2 size={12} className={deleting === v.id ? 'animate-pulse' : ''} />
                          </button>
                        ) : null}
                      </div>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          )}
        </CardBody>
      </Card>

      {/* Single version delete confirmation */}
      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => handleDelete(deleteTarget?.id)}
        tone="danger"
        title="Delete model version"
        confirmLabel="Delete"
        description={
          deleteTarget ? (
            <>
              Permanently delete version{' '}
              <span className="font-mono font-medium text-zinc-100">
                {deleteTarget.id}
              </span>
              ? This removes all model files for this version.
            </>
          ) : null
        }
      />

      {/* Drop all confirmation */}
      <ConfirmDialog
        open={showDropAll}
        onClose={() => setShowDropAll(false)}
        onConfirm={handleDropAll}
        tone="danger"
        title="Drop all models"
        confirmLabel="Drop all"
        description={
          <>
            This will permanently delete all{' '}
            <span className="font-medium text-zinc-100">
              {versions.length} model version{versions.length === 1 ? '' : 's'}
            </span>{' '}
            and reset the version counter back to v001.
            You will need to re-train after this.
          </>
        }
      />
    </>
  );
}

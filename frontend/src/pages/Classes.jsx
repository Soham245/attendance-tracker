import { useCallback, useEffect, useState } from 'react';
import {
  ArrowRightLeft,
  GraduationCap,
  Pencil,
  Plus,
  RotateCcw,
  ToggleLeft,
  ToggleRight,
  Trash2,
} from 'lucide-react';
import { useToast } from '../context/ToastContext.jsx';
import { useAuth } from '../hooks/useAuth.js';
import { useSelection } from '../hooks/useSelection.js';
import PageHeader from '../components/common/PageHeader.jsx';
import RuntimeCard from '../components/common/RuntimeCard.jsx';
import DataTable from '../components/common/DataTable.jsx';
import EmptyState from '../components/common/EmptyState.jsx';
import BaseModal from '../components/common/BaseModal.jsx';
import Button from '../components/common/Button.jsx';
import LoadingButton from '../components/common/LoadingButton.jsx';
import ConfirmDialog from '../components/common/ConfirmDialog.jsx';
import PromoteClassDialog from '../components/classes/PromoteClassDialog.jsx';
import GraduateClassDialog from '../components/classes/GraduateClassDialog.jsx';
import BatchPromoteDialog from '../components/classes/BatchPromoteDialog.jsx';
import BatchRestoreDialog from '../components/classes/BatchRestoreDialog.jsx';
import {
  fetchClasses,
  createClass,
  updateClass,
  deleteClass,
} from '../services/classService.js';
import {
  promoteClass,
  graduateClass,
  restoreBatch,
} from '../services/lifecycleService.js';
import { errorMessage } from '../services/api.js';

export default function ClassesPage() {
  const toast = useToast();
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';

  const [classes, setClasses] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  // Modal targets
  const [showCreate, setShowCreate] = useState(false);
  const [editTarget, setEditTarget] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [promoteTarget, setPromoteTarget] = useState(null);
  const [graduateTarget, setGraduateTarget] = useState(null);
  const [batchPromoteMajor, setBatchPromoteMajor] = useState(null);
  const [batchRestoreOpen, setBatchRestoreOpen] = useState(false);
  const [batchRestoreId, setBatchRestoreId] = useState('');
  const [lastBatchResult, setLastBatchResult] = useState(null);

  const selection = useSelection(classes, (c) => c.id);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchClasses();
      setClasses(result.items);
      setTotal(result.total);
    } catch (err) {
      toast.error('Failed to load classes', errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => { load(); }, [load]);

  const handleToggle = async (cls) => {
    try {
      await updateClass(cls.id, { is_active: !cls.is_active });
      toast.success(cls.is_active ? 'Class deactivated' : 'Class activated');
      load();
    } catch (err) {
      toast.error('Action failed', errorMessage(err));
    }
  };

  const handleDelete = async (cls) => {
    setDeleteTarget(null);
    try {
      await deleteClass(cls.id);
      toast.success('Class deleted', cls.class_code);
      load();
    } catch (err) {
      toast.error('Delete failed', errorMessage(err));
    }
  };

  const handlePromote = async (sourceClass) => {
    const result = await promoteClass(sourceClass.id);
    await load();
    toast.success(
      'Class promoted',
      `${result?.promoted_count ?? 0} student(s) moved to ${result?.target_class ?? 'target class'}`,
    );
    if (result?.warnings?.length) {
      result.warnings.forEach((w) => toast.warning('Warning', w));
    }
  };

  const handleGraduateClass = async (cls) => {
    const result = await graduateClass(cls.id);
    setLastBatchResult(result);
    await load();
    toast.success(
      'Class graduated',
      `${result?.graduated_count ?? 0} student(s) graduated from ${result?.class_code ?? cls.class_code}`,
    );
    if (result?.model_stale) {
      toast.warning(
        'Model is stale',
        'The recognition model includes graduated students. Re-train to update it.',
      );
    }
  };

  const handleBatchRestore = async (batchId, targetClassId) => {
    const result = await restoreBatch(batchId, targetClassId);
    setLastBatchResult(null);
    setBatchRestoreId('');
    await load();
    toast.success(
      'Batch restored',
      `${result?.restored_count ?? 0} student(s) restored to ${result?.target_class ?? 'target class'}`,
    );
    if (result?.model_stale) {
      toast.warning(
        'Model is stale',
        'Restored students require retraining before they can be recognized.',
      );
    }
  };

  // Batch selection actions.
  const selectedClasses = classes.filter((c) => selection.isSelected(c.id));

  const handleSelectionPromote = () => {
    if (selectedClasses.length === 1) {
      setPromoteTarget(selectedClasses[0]);
    } else {
      const majors = [...new Set(selectedClasses.map((c) => c.major))];
      if (majors.length === 1) {
        setBatchPromoteMajor(majors[0]);
      } else {
        toast.error('Select classes from the same major for batch promote');
      }
    }
  };

  const handleSelectionGraduate = () => {
    if (selectedClasses.length === 1) {
      setGraduateTarget(selectedClasses[0]);
    } else {
      const majors = [...new Set(selectedClasses.map((c) => c.major))];
      if (majors.length === 1) {
        setBatchPromoteMajor(majors[0]);
      } else {
        toast.error('Select classes from the same major for batch graduate');
      }
    }
  };

  const handleSelectionToggle = async (activate) => {
    let count = 0;
    for (const cls of selectedClasses) {
      if (activate ? !cls.is_active : cls.is_active) {
        try {
          await updateClass(cls.id, { is_active: activate });
          count++;
        } catch { /* skip failures */ }
      }
    }
    selection.clear();
    await load();
    if (count > 0) {
      toast.success(activate ? 'Activated' : 'Deactivated', `${count} class(es)`);
    }
  };

  const handleSelectionDelete = async () => {
    setDeleteTarget({ _batch: true, count: selectedClasses.length, ids: selection.selectedIds });
  };

  const handleBatchDelete = async () => {
    const ids = deleteTarget?.ids ?? [];
    setDeleteTarget(null);
    let count = 0;
    for (const id of ids) {
      try {
        await deleteClass(id);
        count++;
      } catch { /* skip failures */ }
    }
    selection.clear();
    await load();
    if (count > 0) toast.success('Deleted', `${count} class(es)`);
  };

  return (
    <div>
      <PageHeader
        title="Academic classes"
        description="Create and manage academic classes for attendance scoping."
      />

      <div className="mt-4 space-y-4">
        {/* Create class */}
        <RuntimeCard
          title="Add class"
          subtitle="Create a new academic class."
          icon={Plus}
        >
          {showCreate ? (
            <ClassForm
              onSaved={() => { setShowCreate(false); load(); }}
              onCancel={() => setShowCreate(false)}
            />
          ) : (
            <button
              type="button"
              onClick={() => setShowCreate(true)}
              className="px-3 py-1.5 text-sm rounded-md bg-accent hover:bg-accent-hover text-white transition-colors"
            >
              <span className="flex items-center gap-1.5">
                <Plus size={14} />
                New class
              </span>
            </button>
          )}
        </RuntimeCard>

        {/* Selection toolbar */}
        {isAdmin && selection.count > 0 ? (
          <div className="flex items-center gap-3 rounded-lg border border-surface-border bg-surface-panel px-4 py-2 shadow-md">
            <span className="text-sm text-zinc-200 tabular-nums font-medium">
              {selection.count} selected
            </span>
            <div className="ml-auto flex items-center gap-2">
              <button
                type="button"
                onClick={handleSelectionPromote}
                className="inline-flex items-center gap-1.5 rounded-md bg-sky-600 hover:bg-sky-500 px-3 py-1.5 text-xs font-medium text-white transition-colors"
              >
                <ArrowRightLeft size={13} />
                Promote
              </button>
              <button
                type="button"
                onClick={handleSelectionGraduate}
                className="inline-flex items-center gap-1.5 rounded-md bg-amber-600 hover:bg-amber-500 px-3 py-1.5 text-xs font-medium text-white transition-colors"
              >
                <GraduationCap size={13} />
                Graduate
              </button>
              <button
                type="button"
                onClick={() => handleSelectionToggle(true)}
                className="inline-flex items-center gap-1.5 rounded-md bg-emerald-600 hover:bg-emerald-500 px-3 py-1.5 text-xs font-medium text-white transition-colors"
              >
                <ToggleRight size={13} />
                Activate
              </button>
              <button
                type="button"
                onClick={() => handleSelectionToggle(false)}
                className="inline-flex items-center gap-1.5 rounded-md bg-zinc-600 hover:bg-zinc-500 px-3 py-1.5 text-xs font-medium text-white transition-colors"
              >
                <ToggleLeft size={13} />
                Deactivate
              </button>
              <button
                type="button"
                onClick={handleSelectionDelete}
                className="inline-flex items-center gap-1.5 rounded-md bg-rose-600 hover:bg-rose-500 px-3 py-1.5 text-xs font-medium text-white transition-colors"
              >
                <Trash2 size={13} />
                Delete
              </button>
              <button
                type="button"
                onClick={selection.clear}
                className="p-1.5 rounded-md text-zinc-400 hover:text-zinc-100 hover:bg-surface-hover transition-colors"
                title="Clear selection"
              >
                <span className="text-xs">&times;</span>
              </button>
            </div>
          </div>
        ) : null}

        {/* Class list */}
        <RuntimeCard
          title="Classes"
          subtitle={`${total} total class${total !== 1 ? 'es' : ''}`}
          icon={GraduationCap}
        >
          <DataTable
            bare
            columns={classColumns(setEditTarget)}
            data={classes}
            rowKey={(c) => c.id}
            loading={loading}
            selection={isAdmin ? selection : undefined}
            empty={
              <EmptyState
                icon={GraduationCap}
                title="No classes yet"
                description="Create an academic class above to start scoping attendance sessions."
              />
            }
          />
        </RuntimeCard>
      </div>

      {/* Edit modal */}
      <EditClassModal
        open={Boolean(editTarget)}
        cls={editTarget}
        onClose={() => setEditTarget(null)}
        onSaved={() => { setEditTarget(null); load(); }}
      />

      {/* Delete confirmation */}
      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        onConfirm={deleteTarget?._batch ? handleBatchDelete : () => handleDelete(deleteTarget)}
        tone="danger"
        title={deleteTarget?._batch ? 'Delete classes' : 'Delete class'}
        confirmLabel="Delete"
        description={
          deleteTarget ? (
            deleteTarget._batch ? (
              <>
                Permanently delete{' '}
                <span className="font-medium text-zinc-100">
                  {deleteTarget.count} class{deleteTarget.count !== 1 ? 'es' : ''}
                </span>
                ? This is only possible if no students are assigned.
              </>
            ) : (
              <>
                Permanently delete{' '}
                <span className="font-mono font-medium text-zinc-100">
                  {deleteTarget.class_code}
                </span>
                ? This is only possible if no students are assigned.
              </>
            )
          ) : null
        }
      />

      {/* Lifecycle dialogs (admin only) */}
      <PromoteClassDialog
        open={Boolean(promoteTarget)}
        sourceClass={promoteTarget}
        onClose={() => { setPromoteTarget(null); selection.clear(); }}
        onConfirm={async (src) => {
          await handlePromote(src);
          selection.clear();
        }}
      />

      <GraduateClassDialog
        open={Boolean(graduateTarget)}
        cls={graduateTarget}
        onClose={() => { setGraduateTarget(null); selection.clear(); }}
        onConfirm={async (cls) => {
          await handleGraduateClass(cls);
          selection.clear();
        }}
      />

      <BatchPromoteDialog
        open={Boolean(batchPromoteMajor)}
        major={batchPromoteMajor}
        onClose={() => { setBatchPromoteMajor(null); selection.clear(); }}
        onComplete={(result) => {
          load();
          selection.clear();
          const pCount = result?.promoted?.reduce((s, p) => s + p.count, 0) ?? 0;
          const gCount = result?.graduated?.reduce((s, g) => s + g.count, 0) ?? 0;
          if (pCount > 0) toast.success('Promoted', `${pCount} student(s) promoted`);
          if (gCount > 0) toast.success('Graduated', `${gCount} student(s) graduated`);
          if (result?.model_stale) {
            toast.warning('Model is stale', 'Re-train to update the recognition model.');
          }
          if (result?.graduated?.length) {
            setLastBatchResult({
              class_code: result.graduated.map((g) => g.source).join(', '),
              graduated_count: gCount,
              batch_id: result.graduated[0].batch_id,
            });
          }
        }}
      />

      <BatchRestoreDialog
        open={batchRestoreOpen}
        batchId={batchRestoreId}
        batchInfo={lastBatchResult ? {
          classCode: lastBatchResult.class_code,
          count: lastBatchResult.graduated_count,
        } : null}
        onClose={() => {
          setBatchRestoreOpen(false);
          setBatchRestoreId('');
        }}
        onConfirm={handleBatchRestore}
      />

      {/* Batch restore from last graduation result */}
      {isAdmin && lastBatchResult?.batch_id ? (
        <div className="mt-4">
          <RuntimeCard
            title="Undo last graduation"
            subtitle={`Batch from ${lastBatchResult.class_code} — ${lastBatchResult.graduated_count} student(s)`}
            icon={RotateCcw}
          >
            <div className="flex items-center gap-3">
              <p className="text-xs text-zinc-400 flex-1">
                You can undo the last class graduation by restoring all students
                in this batch to an active class.
              </p>
              <button
                type="button"
                onClick={() => {
                  setBatchRestoreId(lastBatchResult.batch_id);
                  setBatchRestoreOpen(true);
                }}
                className="px-3 py-1.5 text-sm rounded-md bg-accent hover:bg-accent-hover text-white transition-colors whitespace-nowrap"
              >
                <span className="flex items-center gap-1.5">
                  <RotateCcw size={14} />
                  Restore batch
                </span>
              </button>
            </div>
          </RuntimeCard>
        </div>
      ) : null}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Column definitions                                                 */
/* ------------------------------------------------------------------ */

function classColumns(setEditTarget) {
  return [
    {
      key: 'code',
      header: 'Code',
      width: '180px',
      render: (c) => (
        <span className="font-mono font-medium text-zinc-100">{c.class_code}</span>
      ),
    },
    {
      key: 'major',
      header: 'Major',
      render: (c) => <span className="text-zinc-300">{c.major}</span>,
    },
    {
      key: 'year',
      header: 'Year',
      width: '80px',
      render: (c) => <span className="text-zinc-400">Year {c.year}</span>,
    },
    {
      key: 'section',
      header: 'Section',
      width: '80px',
      render: (c) => <span className="text-zinc-400">{c.section}</span>,
    },
    {
      key: 'academic_year',
      header: 'Academic Year',
      width: '130px',
      render: (c) => <span className="text-zinc-400">{c.academic_year}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      width: '100px',
      render: (c) => <StatusBadge active={c.is_active} />,
    },
    {
      key: 'actions',
      header: '',
      width: '50px',
      headerClassName: 'text-right',
      className: 'text-right',
      render: (c) => (
        <IconBtn
          title="Edit"
          icon={Pencil}
          onClick={() => setEditTarget(c)}
        />
      ),
    },
  ];
}

/* ------------------------------------------------------------------ */
/*  Small UI components                                                */
/* ------------------------------------------------------------------ */

function IconBtn({ icon: Icon, title, onClick, className = '' }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      className={`p-1.5 rounded-md text-zinc-400 hover:text-zinc-100 hover:bg-surface-hover transition-colors ${className}`}
    >
      <Icon size={15} />
    </button>
  );
}

function StatusBadge({ active }) {
  return (
    <span
      className={`text-xs px-2 py-0.5 rounded-full ${
        active
          ? 'bg-emerald-500/15 text-emerald-300'
          : 'bg-zinc-500/15 text-zinc-400'
      }`}
    >
      {active ? 'Active' : 'Inactive'}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/*  Inline create form                                                 */
/* ------------------------------------------------------------------ */

function ClassForm({ onSaved, onCancel }) {
  const toast = useToast();
  const [form, setForm] = useState({
    major: '',
    year: '1',
    section: '',
    academic_year: '',
    class_code: '',
  });
  const [submitting, setSubmitting] = useState(false);

  // Auto-generate class_code preview
  const autoCode = form.major && form.academic_year && form.section
    ? `${form.major.toUpperCase()}-${form.academic_year.split('-')[0]}-Y${form.year}-${form.section.toUpperCase()}`
    : '';

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.major || !form.section || !form.academic_year) return;
    setSubmitting(true);
    try {
      const payload = {
        major: form.major,
        year: parseInt(form.year, 10),
        section: form.section,
        academic_year: form.academic_year,
      };
      // Only send class_code if admin overrode the auto-generated one.
      if (form.class_code && form.class_code !== autoCode) {
        payload.class_code = form.class_code;
      }
      await createClass(payload);
      toast.success('Class created');
      onSaved();
    } catch (err) {
      toast.error('Failed to create class', errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  return (
    <form onSubmit={handleSubmit} className="space-y-3 max-w-lg">
      <div className="grid grid-cols-2 gap-3">
        <FormField label="Major">
          <input
            type="text"
            value={form.major}
            onChange={set('major')}
            className="w-full px-3 py-1.5 text-sm rounded-md bg-surface-raised border border-surface-border text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-accent"
            placeholder="e.g. MCA"
            required
          />
        </FormField>
        <FormField label="Academic Year">
          <input
            type="text"
            value={form.academic_year}
            onChange={set('academic_year')}
            className="w-full px-3 py-1.5 text-sm rounded-md bg-surface-raised border border-surface-border text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-accent"
            placeholder="e.g. 2026-27"
            required
            pattern="\d{4}-\d{2,4}"
          />
        </FormField>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <FormField label="Year">
          <select
            value={form.year}
            onChange={set('year')}
            className="w-full px-3 py-1.5 text-sm rounded-md bg-surface-raised border border-surface-border text-zinc-100 focus:outline-none focus:ring-1 focus:ring-accent"
          >
            {[1, 2, 3, 4, 5, 6].map((y) => (
              <option key={y} value={y}>Year {y}</option>
            ))}
          </select>
        </FormField>
        <FormField label="Section">
          <input
            type="text"
            value={form.section}
            onChange={set('section')}
            className="w-full px-3 py-1.5 text-sm rounded-md bg-surface-raised border border-surface-border text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-accent"
            placeholder="e.g. A"
            required
            maxLength={8}
          />
        </FormField>
      </div>
      <FormField label="Class Code" hint={autoCode ? `Auto-generated: ${autoCode}` : 'Fill in fields above to preview'}>
        <input
          type="text"
          value={form.class_code || autoCode}
          onChange={set('class_code')}
          className="w-full px-3 py-1.5 text-sm rounded-md bg-surface-raised border border-surface-border text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-accent font-mono"
          placeholder="Auto-generated"
        />
      </FormField>
      <div className="flex items-center gap-2 pt-1">
        <LoadingButton
          type="submit"
          loading={submitting}
          className="bg-accent hover:bg-accent-hover text-white"
        >
          Create
        </LoadingButton>
        <button
          type="button"
          onClick={onCancel}
          className="px-3 py-1.5 text-sm rounded-md text-zinc-400 hover:text-zinc-200 transition-colors"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

/* ------------------------------------------------------------------ */
/*  Edit class modal                                                   */
/* ------------------------------------------------------------------ */

function EditClassModal({ open, cls, onClose, onSaved }) {
  const toast = useToast();
  const [form, setForm] = useState({
    major: '',
    year: '1',
    section: '',
    academic_year: '',
    class_code: '',
  });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (cls) {
      setForm({
        major: cls.major,
        year: String(cls.year),
        section: cls.section,
        academic_year: cls.academic_year,
        class_code: cls.class_code,
      });
    }
  }, [cls]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!cls) return;
    setSubmitting(true);
    try {
      const payload = {};
      if (form.major !== cls.major) payload.major = form.major;
      if (parseInt(form.year, 10) !== cls.year) payload.year = parseInt(form.year, 10);
      if (form.section !== cls.section) payload.section = form.section;
      if (form.academic_year !== cls.academic_year) payload.academic_year = form.academic_year;
      if (form.class_code !== cls.class_code) payload.class_code = form.class_code;
      await updateClass(cls.id, payload);
      toast.success('Class updated');
      onSaved();
    } catch (err) {
      toast.error('Update failed', errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  return (
    <BaseModal
      open={open}
      onClose={onClose}
      size="sm"
      title="Edit class"
      subtitle={cls?.class_code}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <LoadingButton
            loading={submitting}
            onClick={handleSubmit}
            className="bg-accent hover:bg-accent-hover text-white"
          >
            Save changes
          </LoadingButton>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <FormField label="Major">
            <input
              type="text"
              value={form.major}
              onChange={set('major')}
              className="w-full px-3 py-1.5 text-sm rounded-md bg-surface-raised border border-surface-border text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-accent"
              required
            />
          </FormField>
          <FormField label="Academic Year">
            <input
              type="text"
              value={form.academic_year}
              onChange={set('academic_year')}
              className="w-full px-3 py-1.5 text-sm rounded-md bg-surface-raised border border-surface-border text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-accent"
              required
              pattern="\d{4}-\d{2,4}"
            />
          </FormField>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <FormField label="Year">
            <select
              value={form.year}
              onChange={set('year')}
              className="w-full px-3 py-1.5 text-sm rounded-md bg-surface-raised border border-surface-border text-zinc-100 focus:outline-none focus:ring-1 focus:ring-accent"
            >
              {[1, 2, 3, 4, 5, 6].map((y) => (
                <option key={y} value={y}>Year {y}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Section">
            <input
              type="text"
              value={form.section}
              onChange={set('section')}
              className="w-full px-3 py-1.5 text-sm rounded-md bg-surface-raised border border-surface-border text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-accent"
              required
              maxLength={8}
            />
          </FormField>
        </div>
        <FormField label="Class Code">
          <input
            type="text"
            value={form.class_code}
            onChange={set('class_code')}
            className="w-full px-3 py-1.5 text-sm rounded-md bg-surface-raised border border-surface-border text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-accent font-mono"
            required
          />
        </FormField>
      </form>
    </BaseModal>
  );
}

/* ------------------------------------------------------------------ */
/*  Shared form field wrapper                                          */
/* ------------------------------------------------------------------ */

function FormField({ label, hint, children }) {
  return (
    <div>
      <label className="block text-xs text-zinc-500 mb-1">{label}</label>
      {children}
      {hint ? (
        <div className="mt-1 text-[11px] text-zinc-600">{hint}</div>
      ) : null}
    </div>
  );
}

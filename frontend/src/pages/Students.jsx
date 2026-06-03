import { useCallback, useEffect, useMemo, useState } from 'react';
import { RefreshCw, UserPlus } from 'lucide-react';
import Button from '../components/common/Button.jsx';
import PageHeader from '../components/common/PageHeader.jsx';
import ErrorStateBanner from '../components/common/ErrorStateBanner.jsx';
import SelectionToolbar from '../components/common/SelectionToolbar.jsx';
import BulkDeleteDialog from '../components/common/BulkDeleteDialog.jsx';
import StudentsTable from '../components/students/StudentsTable.jsx';
import StudentSearchBar from '../components/students/StudentSearchBar.jsx';
import StudentFormModal from '../components/students/StudentFormModal.jsx';

import DatasetManagerModal from '../components/datasets/DatasetManagerModal.jsx';
import LifecycleDialog from '../components/students/LifecycleDialog.jsx';
import RestoreStudentDialog from '../components/students/RestoreStudentDialog.jsx';
import {
  bulkDeleteStudents,
  createStudent,
listStudents,
  updateStudent,
} from '../services/studentService.js';
import {
  graduateStudent,
  deactivateStudent,
  restoreStudent,
  restoreBatch,
} from '../services/lifecycleService.js';
import BatchRestoreDialog from '../components/classes/BatchRestoreDialog.jsx';
import { errorMessage } from '../services/api.js';
import { useAuth } from '../hooks/useAuth.js';
import { useClassContext } from '../context/ClassContext.jsx';
import { useToast } from '../context/ToastContext.jsx';
import { useHotkey } from '../hooks/useHotkey.js';
import { useSelection } from '../hooks/useSelection.js';

const PAGE_SIZE = 50;

export default function Students() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const canMutate = isAdmin;
  const toast = useToast();
  const { activeClass } = useClassContext();

  const [students, setStudents] = useState([]);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState(null);
  const [datasetTarget, setDatasetTarget] = useState(null);
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false);
  const [graduateTarget, setGraduateTarget] = useState(null);
  const [deactivateTarget, setDeactivateTarget] = useState(null);
  const [restoreTarget, setRestoreTarget] = useState(null);
  const [batchRestoreOpen, setBatchRestoreOpen] = useState(false);
  const [batchRestoreId, setBatchRestoreId] = useState('');

  // Both faculty and admin: scope to active class when selected.
  const classIdFilter = activeClass ? activeClass.class_id : undefined;

  const refresh = useCallback(
    async (nextSkip = skip) => {
      setLoading(true);
      try {
        const result = await listStudents({
          skip: nextSkip,
          limit: PAGE_SIZE,
          classId: classIdFilter,
          status: statusFilter || undefined,
        });
        setStudents(result?.items ?? []);
        setTotal(result?.total ?? 0);
        setFetchError(null);
      } catch (err) {
        setFetchError(err);
      } finally {
        setLoading(false);
      }
    },
    [skip, classIdFilter, statusFilter],
  );

  useEffect(() => {
    refresh(skip);
  }, [refresh, skip]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return students;
    return students.filter((s) =>
      [s.name, s.roll_number, s.department, s.email]
        .filter(Boolean)
        .some((v) => String(v).toLowerCase().includes(q)),
    );
  }, [students, search]);

  const selection = useSelection(filtered, (s) => s.id);

  const handleCreate = async (payload) => {
    const created = await createStudent(payload);
    await refresh(0);
    setSkip(0);
    toast.success('Student added', created?.name ?? undefined);
    // Auto-open dataset manager for the new student so the operator can
    // immediately begin guided enrollment capture.
    if (created) {
      setDatasetTarget(created);
    }
  };

  const handleEdit = async (payload) => {
    const updated = await updateStudent(editTarget.id, payload);
    await refresh(skip);
    toast.success('Student updated', updated?.name ?? undefined);
  };

  useHotkey('r', () => refresh(skip), { meta: true });

  const showPagination = total > PAGE_SIZE;
  const page = Math.floor(skip / PAGE_SIZE) + 1;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <PageHeader
        title="Students"
        description="Manage enrolled students and their face-recognition datasets."
        actions={
          <>
            <Button
              variant="ghost"
              onClick={() => refresh(skip)}
              disabled={loading}
              title="Refresh (⌘R)"
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              Refresh
            </Button>
            {canMutate ? (
              <Button onClick={() => setCreateOpen(true)}>
                <UserPlus size={16} />
                Add student
              </Button>
            ) : null}
          </>
        }
      />

      {/* Active class scope */}
      {activeClass ? (
        <div className="card mb-4 flex items-center gap-4 p-4">
          <div className="flex items-center gap-2 text-xs text-zinc-300">
            <span className="text-zinc-500">Class:</span>
            <span className="font-mono font-medium">{activeClass.class_code}</span>
          </div>
          <div className="ml-auto text-xs text-zinc-500">
            {total} student{total !== 1 ? 's' : ''}
          </div>
        </div>
      ) : null}

      <div className="mb-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-3">
          <StudentSearchBar value={search} onChange={setSearch} />
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setSkip(0);
            }}
            className="rounded-md border border-surface-border bg-surface-raised px-2.5 py-1.5 text-xs text-zinc-300 focus:border-accent focus:outline-none"
          >
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="graduated">Graduated</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>
        <div className="text-xs text-zinc-500 tabular-nums">
          {loading && !students.length
            ? 'Loading…'
            : `${filtered.length} of ${total} students`}
        </div>
      </div>

      {fetchError ? (
        <ErrorStateBanner
          tone="danger"
          title="Could not load students"
          message={errorMessage(fetchError)}
          className="mb-4"
        />
      ) : null}

      {canMutate ? (
        <SelectionToolbar
          count={selection.count}
          onDelete={() => setBulkDeleteOpen(true)}
          onClear={selection.clear}
        />
      ) : null}

      <StudentsTable
        students={filtered}
        loading={loading}
        filtered={Boolean(search.trim()) && filtered.length === 0 && students.length > 0}
        canMutate={canMutate}
        onCreate={() => setCreateOpen(true)}
        onEdit={(s) => setEditTarget(s)}
        onManageDataset={(s) => setDatasetTarget(s)}
        onGraduate={isAdmin ? (s) => setGraduateTarget(s) : undefined}
        onDeactivate={isAdmin ? (s) => setDeactivateTarget(s) : undefined}
        onRestore={isAdmin ? (s) => setRestoreTarget(s) : undefined}
        onBatchRestore={isAdmin ? (batchId) => {
          setBatchRestoreId(batchId);
          setBatchRestoreOpen(true);
        } : undefined}
        selection={canMutate ? selection : undefined}
      />

      {showPagination ? (
        <div className="mt-4 flex items-center justify-end gap-2 text-xs text-zinc-400">
          <span>
            Page {page} of {pageCount}
          </span>
          <Button
            variant="ghost"
            disabled={skip === 0 || loading}
            onClick={() => setSkip(Math.max(0, skip - PAGE_SIZE))}
          >
            Previous
          </Button>
          <Button
            variant="ghost"
            disabled={skip + PAGE_SIZE >= total || loading}
            onClick={() => setSkip(skip + PAGE_SIZE)}
          >
            Next
          </Button>
        </div>
      ) : null}

      <StudentFormModal
        open={createOpen}
        mode="create"
        defaultClassId={activeClass?.class_id}
        onClose={() => setCreateOpen(false)}
        onSubmit={handleCreate}
      />

      <StudentFormModal
        open={Boolean(editTarget)}
        mode="edit"
        student={editTarget}
        onClose={() => setEditTarget(null)}
        onSubmit={handleEdit}
      />

      <BulkDeleteDialog
        open={bulkDeleteOpen}
        count={selection.count}
        noun="student"
        onClose={() => setBulkDeleteOpen(false)}
        onConfirm={async () => {
          const result = await bulkDeleteStudents(selection.selectedIds);
          selection.clear();
          await refresh(0);
          setSkip(0);
          toast.success('Bulk delete', `Deleted ${result?.deleted ?? selection.count} student(s)`);
          if (result?.model_stale) {
            toast.warning(
              'Model is stale',
              'The active recognition model still includes deleted students. Re-train to update it.',
            );
          }
        }}
      />

      <DatasetManagerModal
        open={Boolean(datasetTarget)}
        student={datasetTarget}
        canMutate={canMutate}
        onClose={() => setDatasetTarget(null)}
        onChanged={() => refresh(skip)}
      />

      {/* Lifecycle dialogs (admin only) */}
      <LifecycleDialog
        open={Boolean(graduateTarget)}
        student={graduateTarget}
        onClose={() => setGraduateTarget(null)}
        onConfirm={async (student) => {
          await graduateStudent(student.id);
          await refresh(skip);
          toast.success('Student graduated', student.name);
        }}
        title="Graduate student"
        description={
          graduateTarget ? (
            <p>
              Graduate{' '}
              <span className="font-medium text-zinc-100">
                {graduateTarget.name}
              </span>
              ? They will be removed from the active class roster and will no
              longer be recognized during attendance sessions. All history is
              preserved.
            </p>
          ) : null
        }
        confirmLabel="Graduate"
        tone="warning"
      />

      <LifecycleDialog
        open={Boolean(deactivateTarget)}
        student={deactivateTarget}
        onClose={() => setDeactivateTarget(null)}
        onConfirm={async (student) => {
          await deactivateStudent(student.id);
          await refresh(skip);
          toast.success('Student deactivated', student.name);
        }}
        title="Deactivate student"
        description={
          deactivateTarget ? (
            <p>
              Deactivate{' '}
              <span className="font-medium text-zinc-100">
                {deactivateTarget.name}
              </span>
              ? Use this for transfers, dropouts, or suspensions. The student
              will be removed from the active roster. All history is preserved
              and the student can be restored later.
            </p>
          ) : null
        }
        confirmLabel="Deactivate"
        tone="danger"
      />

      <RestoreStudentDialog
        open={Boolean(restoreTarget)}
        student={restoreTarget}
        onClose={() => setRestoreTarget(null)}
        onConfirm={async (student, targetClassId) => {
          await restoreStudent(student.id, targetClassId);
          await refresh(skip);
          toast.success('Student restored', student.name);
        }}
      />

      <BatchRestoreDialog
        open={batchRestoreOpen}
        batchId={batchRestoreId}
        onClose={() => {
          setBatchRestoreOpen(false);
          setBatchRestoreId('');
        }}
        onConfirm={async (batchId, targetClassId) => {
          const result = await restoreBatch(batchId, targetClassId);
          await refresh(skip);
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
        }}
      />
    </div>
  );
}

import { useCallback, useEffect, useState } from 'react';
import {
  KeyRound,
  Lock,
  Pencil,
  Shield,
  ShieldCheck,
  ToggleLeft,
  ToggleRight,
  Trash2,
  UserPlus,
  Users,
} from 'lucide-react';
import PasswordInput from '../components/common/PasswordInput.jsx';
import { useAuth } from '../hooks/useAuth.js';
import { useToast } from '../context/ToastContext.jsx';
import PageHeader from '../components/common/PageHeader.jsx';
import RuntimeCard from '../components/common/RuntimeCard.jsx';
import DataTable from '../components/common/DataTable.jsx';
import EmptyState from '../components/common/EmptyState.jsx';
import LoadingButton from '../components/common/LoadingButton.jsx';
import BaseModal from '../components/common/BaseModal.jsx';
import Button from '../components/common/Button.jsx';
import ConfirmDialog from '../components/common/ConfirmDialog.jsx';
import {
  fetchUsers,
  createFaculty,
  updateFaculty,
  toggleUserActive,
  deleteFaculty,
  resetFacultyPassword,
  fetchFacultyClasses,
  updateFacultyClasses,
} from '../services/userService.js';
import { fetchClasses } from '../services/classService.js';
import { errorMessage } from '../services/api.js';
import { formatDateTime } from '../utils/format.js';

export default function UsersPage() {
  const { user: currentUser } = useAuth();
  const toast = useToast();

  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);

  // Edit / delete / reset targets
  const [editTarget, setEditTarget] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [resetTarget, setResetTarget] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchUsers();
      setUsers(result.users);
      setTotal(result.total);
    } catch (err) {
      toast.error('Failed to load users', errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => { load(); }, [load]);

  const handleToggle = async (userId, currentActive) => {
    try {
      await toggleUserActive(userId, !currentActive);
      toast.success(currentActive ? 'User deactivated' : 'User activated');
      load();
    } catch (err) {
      toast.error('Action failed', errorMessage(err));
    }
  };

  const handleDelete = async (user) => {
    try {
      await deleteFaculty(user.id);
      toast.success('Faculty account deleted', user.username);
      load();
    } catch (err) {
      toast.error('Delete failed', errorMessage(err));
    }
  };

  return (
    <div>
      <PageHeader
        title="User management"
        description="Create and manage faculty accounts."
      />

      <div className="mt-4 space-y-4">
        {/* Create faculty form */}
        <RuntimeCard
          title="Add faculty"
          subtitle="Create a new faculty account for session access."
          icon={UserPlus}
        >
          {showCreate ? (
            <CreateFacultyForm
              onCreated={() => { setShowCreate(false); load(); }}
              onCancel={() => setShowCreate(false)}
            />
          ) : (
            <button
              type="button"
              onClick={() => setShowCreate(true)}
              className="px-3 py-1.5 text-sm rounded-md bg-accent hover:bg-accent-hover text-white transition-colors"
            >
              <span className="flex items-center gap-1.5">
                <UserPlus size={14} />
                New faculty user
              </span>
            </button>
          )}
        </RuntimeCard>

        {/* User list */}
        <RuntimeCard
          title="Users"
          subtitle={`${total} total account${total !== 1 ? 's' : ''}`}
          icon={ShieldCheck}
        >
          <DataTable
            bare
            columns={userColumns(setEditTarget, handleToggle, setResetTarget, setDeleteTarget)}
            data={users}
            rowKey={(u) => u.id}
            loading={loading}
            empty={
              <EmptyState
                icon={Users}
                title="No users yet"
                description="Create a faculty account above to grant session access."
              />
            }
          />
        </RuntimeCard>
      </div>

      {/* Edit faculty modal */}
      <EditFacultyModal
        open={Boolean(editTarget)}
        user={editTarget}
        onClose={() => setEditTarget(null)}
        onSaved={() => { setEditTarget(null); load(); }}
      />

      {/* Reset password modal */}
      <ResetPasswordModal
        open={Boolean(resetTarget)}
        user={resetTarget}
        onClose={() => setResetTarget(null)}
        onReset={() => { setResetTarget(null); load(); }}
      />

      {/* Delete confirmation */}
      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => handleDelete(deleteTarget)}
        tone="danger"
        title="Delete faculty account"
        confirmLabel="Delete"
        description={
          deleteTarget ? (
            <>
              This will permanently remove{' '}
              <span className="font-medium text-zinc-100">
                {deleteTarget.username}
              </span>
              's account. This cannot be undone.
            </>
          ) : null
        }
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Column definitions                                                 */
/* ------------------------------------------------------------------ */

const isFaculty = (u) => u.role !== 'admin';

function userColumns(setEditTarget, handleToggle, setResetTarget, setDeleteTarget) {
  return [
    {
      key: 'username',
      header: 'Username',
      render: (u) => <span className="font-medium text-zinc-100">{u.username}</span>,
    },
    {
      key: 'email',
      header: 'Email',
      render: (u) => <span className="text-zinc-400">{u.email}</span>,
    },
    {
      key: 'role',
      header: 'Role',
      width: '100px',
      render: (u) => <RoleBadge role={u.role} />,
    },
    {
      key: 'status',
      header: 'Status',
      width: '100px',
      render: (u) => <StatusBadge active={u.is_active} />,
    },
    {
      key: 'created',
      header: 'Created',
      width: '140px',
      render: (u) => (
        <span className="text-zinc-500 text-xs tabular-nums">
          {formatDateTime(u.created_at)}
        </span>
      ),
    },
    {
      key: 'actions',
      header: '',
      width: '220px',
      render: (u) =>
        isFaculty(u) ? (
          <div className="flex items-center gap-1">
            <ActionButton icon={Pencil} label="Edit" onClick={() => setEditTarget(u)} />
            <ActionButton
              icon={u.is_active ? ToggleRight : ToggleLeft}
              label={u.is_active ? 'Deactivate' : 'Activate'}
              iconClassName={u.is_active ? 'text-emerald-400' : 'text-zinc-500'}
              onClick={() => handleToggle(u.id, u.is_active)}
            />
            <ActionButton icon={KeyRound} label="Reset pw" onClick={() => setResetTarget(u)} />
            <ActionButton
              icon={Trash2}
              label="Delete"
              tone="danger"
              onClick={() => setDeleteTarget(u)}
            />
          </div>
        ) : (
          <span className="inline-flex items-center gap-1.5 text-xs text-zinc-600 px-2 py-1">
            <Lock size={10} />
            Protected
          </span>
        ),
    },
  ];
}

/* ------------------------------------------------------------------ */
/*  Small UI components                                                */
/* ------------------------------------------------------------------ */

const ACTION_TONES = {
  default: 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700/50',
  danger: 'text-rose-400/80 hover:text-rose-300 hover:bg-rose-500/10',
};

function ActionButton({ icon: Icon, label, onClick, tone = 'default', iconClassName = '' }) {
  const colors = ACTION_TONES[tone] ?? ACTION_TONES.default;
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs transition-colors ${colors}`}
      title={label}
    >
      <Icon size={13} className={iconClassName} />
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
}

function RoleBadge({ role }) {
  const isAdmin = role === 'admin';
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${
        isAdmin
          ? 'bg-amber-500/15 text-amber-300'
          : 'bg-sky-500/15 text-sky-300'
      }`}
    >
      {isAdmin ? <Shield size={10} /> : <ShieldCheck size={10} />}
      {role}
    </span>
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
/*  Create faculty inline form                                         */
/* ------------------------------------------------------------------ */

function CreateFacultyForm({ onCreated, onCancel }) {
  const toast = useToast();
  const [form, setForm] = useState({ username: '', email: '', password: '' });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.username || !form.email || !form.password) return;
    setSubmitting(true);
    try {
      await createFaculty(form);
      toast.success('Faculty user created');
      onCreated();
    } catch (err) {
      toast.error('Failed to create user', errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3 max-w-md">
      <FormField label="Username">
        <input
          type="text"
          value={form.username}
          onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
          className="w-full px-3 py-1.5 text-sm rounded-md bg-surface-raised border border-surface-border text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-accent"
          placeholder="e.g. jdoe"
          required
          minLength={2}
        />
      </FormField>
      <FormField label="Email">
        <input
          type="email"
          value={form.email}
          onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
          className="w-full px-3 py-1.5 text-sm rounded-md bg-surface-raised border border-surface-border text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-accent"
          placeholder="e.g. jdoe@school.edu"
          required
        />
      </FormField>
      <FormField label="Password">
        <PasswordInput
          value={form.password}
          onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
          className="w-full px-3 py-1.5 pr-9 text-sm rounded-md bg-surface-raised border border-surface-border text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-accent"
          placeholder="Min 6 characters"
          required
          minLength={6}
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
/*  Edit faculty modal                                                 */
/* ------------------------------------------------------------------ */

function EditFacultyModal({ open, user, onClose, onSaved }) {
  const toast = useToast();
  const [form, setForm] = useState({ username: '', email: '', password: '' });
  const [submitting, setSubmitting] = useState(false);

  // Class assignment state
  const [allClasses, setAllClasses] = useState([]);
  const [assignedIds, setAssignedIds] = useState(new Set());

  // Sync form + load class data when target user changes.
  useEffect(() => {
    if (user && open) {
      setForm({ username: user.username, email: user.email, password: '' });
      // Load all active classes + current assignments in parallel.
      Promise.all([
        fetchClasses({ activeOnly: true }).catch(() => ({ items: [] })),
        fetchFacultyClasses(user.id).catch(() => ({ assignments: [] })),
      ]).then(([classResult, assignResult]) => {
        setAllClasses(classResult.items ?? []);
        setAssignedIds(new Set((assignResult.assignments ?? []).map((a) => a.class_id)));
      });
    }
  }, [user, open]);

  const toggleClass = (classId) => {
    setAssignedIds((prev) => {
      const next = new Set(prev);
      if (next.has(classId)) {
        next.delete(classId);
      } else {
        next.add(classId);
      }
      return next;
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!user) return;
    setSubmitting(true);
    try {
      // Update profile fields.
      await updateFaculty(user.id, {
        username: form.username !== user.username ? form.username : undefined,
        email: form.email !== user.email ? form.email : undefined,
        password: form.password || undefined,
      });
      // Update class assignments.
      await updateFacultyClasses(user.id, [...assignedIds]);
      toast.success('Faculty user updated');
      onSaved();
    } catch (err) {
      toast.error('Update failed', errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <BaseModal
      open={open}
      onClose={onClose}
      size="md"
      title="Edit faculty account"
      subtitle={user?.username}
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
      <form onSubmit={handleSubmit} className="space-y-4">
        <FormField label="Username">
          <input
            type="text"
            value={form.username}
            onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
            className="w-full px-3 py-1.5 text-sm rounded-md bg-surface-raised border border-surface-border text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-accent"
            required
            minLength={2}
          />
        </FormField>
        <FormField label="Email">
          <input
            type="email"
            value={form.email}
            onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
            className="w-full px-3 py-1.5 text-sm rounded-md bg-surface-raised border border-surface-border text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-accent"
            required
          />
        </FormField>
        <FormField label="New password" hint="Leave blank to keep current password">
          <PasswordInput
            value={form.password}
            onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
            className="w-full px-3 py-1.5 pr-9 text-sm rounded-md bg-surface-raised border border-surface-border text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-accent"
            placeholder="Optional"
            minLength={6}
          />
        </FormField>

        {/* Class assignments */}
        <FormField label="Assigned classes" hint="Select which classes this faculty member teaches">
          {allClasses.length === 0 ? (
            <div className="text-xs text-zinc-600 py-1">No active classes available</div>
          ) : (
            <div className="max-h-40 overflow-y-auto space-y-1 rounded-md border border-surface-border bg-surface-raised p-2">
              {allClasses.map((c) => (
                <label
                  key={c.id}
                  className="flex items-center gap-2 px-2 py-1 rounded hover:bg-zinc-700/40 cursor-pointer text-sm"
                >
                  <input
                    type="checkbox"
                    checked={assignedIds.has(c.id)}
                    onChange={() => toggleClass(c.id)}
                    className="rounded border-zinc-600 bg-zinc-800 text-accent focus:ring-accent focus:ring-offset-0"
                  />
                  <span className="font-mono text-xs text-zinc-200">{c.class_code}</span>
                  <span className="text-[11px] text-zinc-500">
                    {c.major} Y{c.year} {c.section}
                  </span>
                </label>
              ))}
            </div>
          )}
        </FormField>
      </form>
    </BaseModal>
  );
}

/* ------------------------------------------------------------------ */
/*  Reset password modal                                               */
/* ------------------------------------------------------------------ */

function ResetPasswordModal({ open, user, onClose, onReset }) {
  const toast = useToast();
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) setPassword('');
  }, [open]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!user || password.length < 6) return;
    setSubmitting(true);
    try {
      await resetFacultyPassword(user.id, password);
      toast.success(
        'Password reset',
        `${user.username} must change their password on next login.`,
      );
      onReset();
    } catch (err) {
      toast.error('Reset failed', errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <BaseModal
      open={open}
      onClose={onClose}
      title="Reset password"
      subtitle={user?.username}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <LoadingButton
            loading={submitting}
            onClick={handleSubmit}
            disabled={password.length < 6}
            className="bg-accent hover:bg-accent-hover text-white"
          >
            Reset password
          </LoadingButton>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <p className="text-xs text-zinc-400">
          Set a temporary password for{' '}
          <span className="font-medium text-zinc-200">{user?.username}</span>.
          They will be required to change it on their next login.
        </p>
        <FormField label="New temporary password">
          <PasswordInput
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-3 py-1.5 pr-9 text-sm rounded-md bg-surface-raised border border-surface-border text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-accent"
            placeholder="Min 6 characters"
            required
            minLength={6}
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

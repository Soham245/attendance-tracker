import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Calendar,
  ChevronRight,
  Download,
  Filter,
  RefreshCw,
  X,
} from 'lucide-react';
import Button from '../components/common/Button.jsx';
import DataTable from '../components/common/DataTable.jsx';
import EmptyState from '../components/common/EmptyState.jsx';
import PageHeader from '../components/common/PageHeader.jsx';
import ErrorStateBanner from '../components/common/ErrorStateBanner.jsx';
import SelectionToolbar from '../components/common/SelectionToolbar.jsx';
import BulkDeleteDialog from '../components/common/BulkDeleteDialog.jsx';
import { bulkDeleteSessions, fetchSessions } from '../services/sessionService.js';
import { fetchUsers } from '../services/userService.js';
import { errorMessage } from '../services/api.js';
import { useAuth } from '../hooks/useAuth.js';
import { useClassContext } from '../context/ClassContext.jsx';
import { useSelection } from '../hooks/useSelection.js';
import { useHotkey } from '../hooks/useHotkey.js';
import { useToast } from '../context/ToastContext.jsx';
import { formatDateTime, formatRelative } from '../utils/format.js';
import { tokenStore } from '../services/api.js';
import { cn } from '../utils/cn.js';

const PAGE_SIZE = 20;
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';

function SessionStatusBadge({ status }) {
  const isActive = status === 'active';
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium',
        isActive
          ? 'bg-emerald-500/15 text-emerald-400'
          : 'bg-zinc-700/50 text-zinc-400',
      )}
    >
      {isActive ? 'Active' : 'Ended'}
    </span>
  );
}

function sessionColumns(onExport) {
  return [
    {
      key: 'session_name',
      header: 'Session',
      render: (s) => <span className="font-medium text-zinc-200">{s.session_name}</span>,
    },
    {
      key: 'class_code',
      header: 'Class',
      width: '140px',
      render: (s) => <span className="font-mono text-zinc-400">{s.class_code ?? '—'}</span>,
    },
    {
      key: 'faculty',
      header: 'Faculty',
      render: (s) => <span className="text-zinc-400">{s.faculty_name ?? '—'}</span>,
    },
    {
      key: 'started',
      header: 'Started',
      width: '160px',
      render: (s) => <span className="text-zinc-400">{formatDateTime(s.started_at)}</span>,
    },
    {
      key: 'ended',
      header: 'Ended',
      width: '120px',
      render: (s) => (
        <span className="text-zinc-400">{s.ended_at ? formatRelative(s.ended_at) : '—'}</span>
      ),
    },
    {
      key: 'attendance',
      header: 'Attendance',
      width: '100px',
      render: (s) => <span className="tabular-nums text-zinc-300">{s.attendance_count}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      width: '90px',
      render: (s) => <SessionStatusBadge status={s.status} />,
    },
    {
      key: 'actions',
      header: '',
      width: '60px',
      headerClassName: 'text-right',
      className: 'text-right',
      render: (s) => (
        <div className="flex items-center gap-1 justify-end">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onExport(s);
            }}
            className="rounded p-1 text-zinc-500 hover:bg-zinc-700 hover:text-zinc-300"
            title="Export CSV"
          >
            <Download size={14} />
          </button>
          <ChevronRight size={14} className="text-zinc-600" />
        </div>
      ),
    },
  ];
}

export default function SessionHistory() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const isAdmin = user?.role === 'admin';
  const canDelete = isAdmin || user?.role === 'faculty';
  const { activeClass } = useClassContext();
  const toast = useToast();

  // Class filter — derived from active class context for both roles.
  const classFilter = activeClass ? String(activeClass.class_id) : '';

  // Filters
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [facultyFilter, setFacultyFilter] = useState('');
  const [facultyList, setFacultyList] = useState([]);

  // Data
  const [sessions, setSessions] = useState([]);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false);

  const selection = useSelection(sessions, (s) => s.id);

  // Load faculty list for admin filter dropdown.
  useEffect(() => {
    if (!isAdmin) return;
    fetchUsers({ limit: 200 })
      .then((result) => setFacultyList(result?.items ?? []))
      .catch(() => setFacultyList([]));
  }, [isAdmin]);

  const queryRef = useRef({ classFilter, skip, dateFrom, dateTo, facultyFilter });
  queryRef.current = { classFilter, skip, dateFrom, dateTo, facultyFilter };

  const fetchData = useCallback(async () => {
    const { classFilter: cf, skip: s, dateFrom: df, dateTo: dt, facultyFilter: ff } = queryRef.current;
    setLoading(true);
    try {
      const result = await fetchSessions({
        classId: cf ? Number(cf) : undefined,
        facultyId: ff ? Number(ff) : undefined,
        dateFrom: df || undefined,
        dateTo: dt || undefined,
        skip: s,
        limit: PAGE_SIZE,
      });
      setSessions(result?.items ?? []);
      setTotal(result?.total ?? 0);
      setError(null);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData, classFilter, skip, dateFrom, dateTo, facultyFilter]);

  const hasFilters = dateFrom || dateTo || facultyFilter;

  const clearFilters = () => {
    setDateFrom('');
    setDateTo('');
    setFacultyFilter('');
    setSkip(0);
  };

  const handleExport = (session) => {
    const token = tokenStore.get();
    const url = `${API_BASE}/sessions/${session.id}/export/csv`;
    // Open in new tab with auth header via fetch + download
    fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.blob())
      .then((blob) => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `attendance_${session.id}.csv`;
        a.click();
        URL.revokeObjectURL(a.href);
      })
      .catch(() => {
        // Fallback: open directly (won't have auth in some setups)
        window.open(url, '_blank');
      });
  };

  useHotkey('r', fetchData, { meta: true });

  const showPagination = total > PAGE_SIZE;
  const page = Math.floor(skip / PAGE_SIZE) + 1;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <PageHeader
        title="Session history"
        description={
          isAdmin
            ? 'All attendance sessions across classes and faculty.'
            : 'Your past attendance sessions.'
        }
        actions={
          <Button
            variant="ghost"
            onClick={fetchData}
            disabled={loading}
            title="Refresh (Cmd+R)"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </Button>
        }
      />

      {/* Active class scope */}
      <div className="card mb-4 flex items-center gap-4 p-4">
        {activeClass ? (
          <div className="flex items-center gap-2 text-xs text-zinc-300">
            <span className="text-zinc-500">Class:</span>
            <span className="font-mono font-medium">{activeClass.class_code}</span>
          </div>
        ) : (
          <div className="text-xs text-amber-400">
            Select a class from the Dashboard to view sessions.
          </div>
        )}
        <div className="ml-auto text-xs text-zinc-500">
          {total} session{total !== 1 ? 's' : ''}
        </div>
      </div>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-[11px] text-zinc-500 mb-1">From</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => { setDateFrom(e.target.value); setSkip(0); }}
            className="rounded-md border border-surface-border bg-surface-raised px-2.5 py-1.5 text-xs text-zinc-300 focus:border-accent focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-[11px] text-zinc-500 mb-1">To</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => { setDateTo(e.target.value); setSkip(0); }}
            className="rounded-md border border-surface-border bg-surface-raised px-2.5 py-1.5 text-xs text-zinc-300 focus:border-accent focus:outline-none"
          />
        </div>
        {isAdmin ? (
          <div>
            <label className="block text-[11px] text-zinc-500 mb-1">Faculty</label>
            <select
              value={facultyFilter}
              onChange={(e) => { setFacultyFilter(e.target.value); setSkip(0); }}
              className="rounded-md border border-surface-border bg-surface-raised px-2.5 py-1.5 text-xs text-zinc-300 focus:border-accent focus:outline-none"
            >
              <option value="">All faculty</option>
              {facultyList.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.username}
                </option>
              ))}
            </select>
          </div>
        ) : null}
        {hasFilters ? (
          <button
            type="button"
            onClick={clearFilters}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1.5 text-xs text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700/50 transition-colors"
            title="Clear filters"
          >
            <X size={12} />
            Clear
          </button>
        ) : null}
      </div>

      {error ? (
        <ErrorStateBanner
          tone="danger"
          title="Could not load sessions"
          message={errorMessage(error)}
          className="mb-4"
        />
      ) : null}

      {canDelete ? (
        <SelectionToolbar
          count={selection.count}
          onDelete={() => setBulkDeleteOpen(true)}
          onClear={selection.clear}
        />
      ) : null}

      {/* Sessions table */}
      <DataTable
        columns={sessionColumns(handleExport)}
        data={sessions}
        rowKey={(s) => s.id}
        loading={loading}
        onRowClick={(s) => navigate(`/sessions/${s.id}`)}
        selection={canDelete ? selection : undefined}
        empty={
          <EmptyState
            icon={Calendar}
            title="No sessions found"
            description={
              classFilter
                ? 'No sessions match the selected class. Try a different filter or clear it.'
                : 'Start an attendance session from the Live Attendance page to see it here.'
            }
          />
        }
      />

      {/* Pagination */}
      {showPagination ? (
        <div className="mt-3 flex items-center justify-end gap-2 text-xs text-zinc-500">
          <span className="tabular-nums">
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

      {/* Bulk delete confirmation */}
      <BulkDeleteDialog
        open={bulkDeleteOpen}
        count={selection.count}
        noun="session"
        onClose={() => setBulkDeleteOpen(false)}
        onConfirm={async () => {
          const count = selection.count;
          await bulkDeleteSessions(selection.selectedIds);
          selection.clear();
          await fetchData();
          toast.success('Bulk delete', `Deleted ${count} session(s)`);
        }}
      />
    </div>
  );
}

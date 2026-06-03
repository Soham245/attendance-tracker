import { useCallback, useEffect, useRef, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import Button from '../components/common/Button.jsx';
import PageHeader from '../components/common/PageHeader.jsx';
import ErrorStateBanner from '../components/common/ErrorStateBanner.jsx';
import PollingStateIndicator from '../components/common/PollingStateIndicator.jsx';
import SelectionToolbar from '../components/common/SelectionToolbar.jsx';
import BulkDeleteDialog from '../components/common/BulkDeleteDialog.jsx';
import AttendanceFilters from '../components/attendance/AttendanceFilters.jsx';
import AttendanceTable from '../components/attendance/AttendanceTable.jsx';
import AttendanceDetailModal from '../components/attendance/AttendanceDetailModal.jsx';
import { bulkDeleteAttendance, listAttendance } from '../services/attendanceService.js';
import { errorMessage } from '../services/api.js';
import { useHotkey } from '../hooks/useHotkey.js';
import { useSelection } from '../hooks/useSelection.js';
import { useAuth } from '../hooks/useAuth.js';
import { useClassContext } from '../context/ClassContext.jsx';
import { useToast } from '../context/ToastContext.jsx';

const PAGE_SIZE = 50;

const EMPTY_FILTERS = { studentId: '', onDate: '' };

/**
 * History view. Polling here is slow + manual:
 *   - 30s background poll while the tab is visible (handled by usePolling
 *     elsewhere; we just call the service on a timer because we also want
 *     control over the loading flag relative to pagination/filters).
 *   - Explicit refresh button.
 *
 * Filters are applied via the Apply button, never on keystroke. Pagination
 * resets to page 0 on any filter change.
 */
export default function AttendanceHistory() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const { activeClass } = useClassContext();
  const toast = useToast();
  const canDelete = isAdmin || user?.role === 'faculty';

  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [pendingFilters, setPendingFilters] = useState(EMPTY_FILTERS);
  const [skip, setSkip] = useState(0);

  const [records, setRecords] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [selected, setSelected] = useState(null);
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false);

  const selection = useSelection(records, (r) => r.id);

  // Derive class filter from active class context.
  const classId = activeClass ? activeClass.class_id : undefined;

  // Refs let the polling timer use the latest query without re-creating itself
  // on every state change, while still respecting tab visibility.
  const queryRef = useRef({ filters, skip, classId });
  queryRef.current = { filters, skip, classId };

  const fetchData = useCallback(async () => {
    const { filters: f, skip: s, classId: cid } = queryRef.current;
    setLoading(true);
    try {
      const result = await listAttendance({
        studentId: f.studentId ? Number(f.studentId) : undefined,
        classId: cid,
        onDate: f.onDate || undefined,
        skip: s,
        limit: PAGE_SIZE,
      });
      setRecords(result?.items ?? []);
      setTotal(result?.total ?? 0);
      setError(null);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch on filter/page/class change.
  useEffect(() => {
    fetchData();
  }, [fetchData, filters, skip, classId]);

  // Background poll — slow, respects visibility.
  useEffect(() => {
    const tick = () => {
      if (typeof document !== 'undefined' && document.hidden) return;
      fetchData();
    };
    const timer = window.setInterval(tick, 30000);
    const onVis = () => {
      if (!document.hidden) tick();
    };
    document.addEventListener('visibilitychange', onVis);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', onVis);
    };
  }, [fetchData]);

  const handleApply = () => {
    setFilters(pendingFilters);
    setSkip(0);
  };

  const handleClear = () => {
    setPendingFilters(EMPTY_FILTERS);
    setFilters(EMPTY_FILTERS);
    setSkip(0);
  };

  useHotkey('r', fetchData, { meta: true });

  const hasFilters = Boolean(filters.studentId || filters.onDate);
  const showPagination = total > PAGE_SIZE;
  const page = Math.floor(skip / PAGE_SIZE) + 1;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <PageHeader
        title="Attendance history"
        description="Persisted attendance records. Filter by student or date."
        status={
          <PollingStateIndicator
            loading={loading}
            error={error}
            label={loading ? 'Refreshing' : error ? 'Stale' : 'Up to date'}
          />
        }
        actions={
          <Button
            variant="ghost"
            onClick={fetchData}
            disabled={loading}
            title="Refresh (⌘R)"
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
            Select a class from the Dashboard to view attendance.
          </div>
        )}
        <div className="ml-auto text-xs text-zinc-500">
          {total} record{total !== 1 ? 's' : ''}
        </div>
      </div>

      <div className="card p-4 mb-4">
        <AttendanceFilters
          values={pendingFilters}
          onChange={setPendingFilters}
          onApply={handleApply}
          onClear={handleClear}
          loading={loading}
        />
      </div>

      {error ? (
        <ErrorStateBanner
          tone="danger"
          title="Could not load attendance"
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

      <AttendanceTable
        records={records}
        loading={loading}
        filtered={hasFilters && records.length === 0}
        onView={(r) => setSelected(r)}
        selection={canDelete ? selection : undefined}
      />

      <div className="mt-3 flex items-center justify-between text-xs text-zinc-500">
        <span>
          {loading && records.length === 0
            ? 'Loading…'
            : `${records.length} of ${total} records`}
        </span>

        {showPagination ? (
          <div className="flex items-center gap-2">
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
      </div>

      <AttendanceDetailModal
        open={Boolean(selected)}
        record={selected}
        onClose={() => setSelected(null)}
      />

      <BulkDeleteDialog
        open={bulkDeleteOpen}
        count={selection.count}
        noun="attendance record"
        onClose={() => setBulkDeleteOpen(false)}
        onConfirm={async () => {
          const count = selection.count;
          await bulkDeleteAttendance(selection.selectedIds);
          selection.clear();
          await fetchData();
          toast.success('Bulk delete', `Deleted ${count} record(s)`);
        }}
      />
    </div>
  );
}

import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  Calendar,
  Clock,
  Download,
  GraduationCap,
  RefreshCw,
  User,
  Users,
} from 'lucide-react';
import Button from '../components/common/Button.jsx';
import DataTable from '../components/common/DataTable.jsx';
import EmptyState from '../components/common/EmptyState.jsx';
import Skeleton from '../components/common/Skeleton.jsx';
import PageHeader from '../components/common/PageHeader.jsx';
import ErrorStateBanner from '../components/common/ErrorStateBanner.jsx';
import { fetchSession } from '../services/sessionService.js';
import { api, errorMessage, tokenStore } from '../services/api.js';
import { useHotkey } from '../hooks/useHotkey.js';
import { formatDateTime } from '../utils/format.js';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';
const PAGE_SIZE = 100;

function MetaItem({ icon: Icon, label, value }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <Icon size={14} className="text-zinc-500" />
      <span className="text-zinc-500">{label}:</span>
      <span className="text-zinc-200">{value || '—'}</span>
    </div>
  );
}

function StatusBadge({ status }) {
  const isActive = status === 'active';
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${
        isActive
          ? 'bg-emerald-500/15 text-emerald-400'
          : 'bg-zinc-700/50 text-zinc-400'
      }`}
    >
      {isActive ? 'Active' : 'Ended'}
    </span>
  );
}

function AttendanceStatusPill({ status }) {
  const tones = {
    present: 'bg-emerald-500/15 text-emerald-400',
    late: 'bg-amber-500/15 text-amber-400',
    absent: 'bg-rose-500/15 text-rose-400',
  };
  const tone = tones[status] ?? 'bg-zinc-700/50 text-zinc-400';
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${tone}`}>
      {status ?? '—'}
    </span>
  );
}

function attendanceColumns(offset) {
  return [
    {
      key: 'index',
      header: '#',
      width: '50px',
      render: (_r, _c, idx) => (
        <span className="text-xs tabular-nums text-zinc-500">{offset + idx + 1}</span>
      ),
    },
    {
      key: 'student',
      header: 'Student',
      render: (r) => (
        <span className="text-zinc-200">{r.student?.name ?? `Student #${r.student_id}`}</span>
      ),
    },
    {
      key: 'roll',
      header: 'Roll Number',
      width: '140px',
      render: (r) => (
        <span className="font-mono text-zinc-400">{r.student?.student_code ?? '—'}</span>
      ),
    },
    {
      key: 'time',
      header: 'Time',
      width: '160px',
      render: (r) => <span className="text-zinc-400">{formatDateTime(r.recognized_at)}</span>,
    },
    {
      key: 'confidence',
      header: 'Confidence',
      width: '100px',
      render: (r) => (
        <span className="font-mono tabular-nums text-zinc-300">
          {r.confidence != null ? `${(r.confidence * 100).toFixed(0)}%` : '—'}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      width: '100px',
      render: (r) => <AttendanceStatusPill status={r.status} />,
    },
  ];
}

export default function SessionDetail() {
  const { sessionId } = useParams();
  const navigate = useNavigate();

  const [session, setSession] = useState(null);
  const [attendance, setAttendance] = useState([]);
  const [attTotal, setAttTotal] = useState(0);
  const [attSkip, setAttSkip] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [sessResult, attResult] = await Promise.all([
        fetchSession(sessionId),
        api.get(`/sessions/${sessionId}/attendance`, {
          params: { skip: attSkip, limit: PAGE_SIZE },
        }).then((r) => r.data?.data),
      ]);
      setSession(sessResult);
      setAttendance(attResult?.items ?? []);
      setAttTotal(attResult?.total ?? 0);
      setError(null);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [sessionId, attSkip]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleExport = () => {
    const token = tokenStore.get();
    const url = `${API_BASE}/sessions/${sessionId}/export/csv`;
    fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.blob())
      .then((blob) => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `attendance_session_${sessionId}.csv`;
        a.click();
        URL.revokeObjectURL(a.href);
      })
      .catch(() => window.open(url, '_blank'));
  };

  useHotkey('r', fetchData, { meta: true });

  const showPagination = attTotal > PAGE_SIZE;
  const page = Math.floor(attSkip / PAGE_SIZE) + 1;
  const pageCount = Math.max(1, Math.ceil(attTotal / PAGE_SIZE));

  return (
    <div>
      <div className="flex items-center gap-3 mb-1">
        <button
          onClick={() => navigate('/sessions')}
          className="grid place-items-center h-8 w-8 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-colors"
          title="Back to sessions"
        >
          <ArrowLeft size={16} />
        </button>
        <div className="flex-1">
          <PageHeader
            title={session?.session_name ?? 'Session detail'}
            description="Attendance session metadata and records."
            actions={
              <div className="flex items-center gap-2">
                <Button variant="ghost" onClick={fetchData} disabled={loading}>
                  <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                </Button>
                <Button variant="ghost" onClick={handleExport}>
                  <Download size={14} />
                  Export CSV
                </Button>
              </div>
            }
          />
        </div>
      </div>

      {error ? (
        <ErrorStateBanner
          tone="danger"
          title="Could not load session"
          message={errorMessage(error)}
          className="mb-4"
        />
      ) : null}

      {/* Session metadata */}
      {session ? (
        <div className="card mb-4 grid grid-cols-2 gap-3 p-4 sm:grid-cols-3 lg:grid-cols-4">
          <MetaItem icon={GraduationCap} label="Class" value={session.class_code} />
          <MetaItem icon={User} label="Faculty" value={session.faculty_name} />
          <MetaItem icon={Calendar} label="Started" value={formatDateTime(session.started_at)} />
          <MetaItem
            icon={Clock}
            label="Ended"
            value={session.ended_at ? formatDateTime(session.ended_at) : 'Still active'}
          />
          <MetaItem icon={Users} label="Attendance" value={session.attendance_count} />
          <div className="flex items-center gap-2">
            <StatusBadge status={session.status} />
          </div>
        </div>
      ) : loading ? (
        <div className="card mb-4 grid grid-cols-2 gap-3 p-4 sm:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="flex items-center gap-2">
              <Skeleton className="h-4 w-4 rounded" />
              <div className="space-y-1.5 flex-1">
                <Skeleton className="h-2.5 w-16" />
                <Skeleton className="h-3.5 w-24" />
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {/* Attendance table */}
      <DataTable
        columns={attendanceColumns(attSkip)}
        data={attendance}
        rowKey={(r) => r.id}
        loading={loading}
        empty={
          <EmptyState
            icon={Users}
            title="No attendance records"
            description="No students were recognised during this session."
          />
        }
      />

      {/* Pagination */}
      <div className="mt-3 flex items-center justify-between text-xs text-zinc-500">
        <span>
          {attendance.length} of {attTotal} record{attTotal !== 1 ? 's' : ''}
        </span>
        {showPagination ? (
          <div className="flex items-center gap-2">
            <span className="tabular-nums">
              Page {page} of {pageCount}
            </span>
            <Button
              variant="ghost"
              disabled={attSkip === 0 || loading}
              onClick={() => setAttSkip(Math.max(0, attSkip - PAGE_SIZE))}
            >
              Previous
            </Button>
            <Button
              variant="ghost"
              disabled={attSkip + PAGE_SIZE >= attTotal || loading}
              onClick={() => setAttSkip(attSkip + PAGE_SIZE)}
            >
              Next
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  );
}

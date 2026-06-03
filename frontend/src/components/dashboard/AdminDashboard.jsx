import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BookOpen,
  Check,
  ClipboardList,
  GraduationCap,
  Play,
  Radio,
  Users,
  UserCog,
} from 'lucide-react';
import PageHeader from '../common/PageHeader.jsx';
import { useAuth } from '../../hooks/useAuth.js';
import { useClassContext } from '../../context/ClassContext.jsx';
import { useSessionStatus } from '../../hooks/useSessionStatus.js';
import { fetchUsers } from '../../services/userService.js';
import { fetchSessions } from '../../services/sessionService.js';
import { fetchClassFaculty } from '../../services/classService.js';

function StatCard({ icon: Icon, label, value, color = 'text-accent' }) {
  return (
    <div className="card p-4 flex items-center gap-3">
      <div className={`grid place-items-center h-9 w-9 rounded-lg bg-zinc-800 ${color}`}>
        <Icon size={18} />
      </div>
      <div>
        <div className="text-lg font-semibold text-zinc-100 tabular-nums">{value ?? '—'}</div>
        <div className="text-[11px] text-zinc-500 uppercase tracking-wider">{label}</div>
      </div>
    </div>
  );
}

function QuickAction({ icon: Icon, label, onClick, disabled }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="card flex items-center gap-3 p-4 transition-colors hover:bg-zinc-800/80 text-left w-full disabled:opacity-50 disabled:cursor-not-allowed"
    >
      <div className="grid place-items-center h-9 w-9 rounded-lg bg-accent/15 text-accent">
        <Icon size={18} />
      </div>
      <span className="text-sm font-medium text-zinc-200">{label}</span>
    </button>
  );
}

function ClassCard({ cls, isActive, onSelect }) {
  return (
    <button
      onClick={() => onSelect(cls)}
      className={`relative text-left rounded-xl border p-4 transition-all ${
        isActive
          ? 'border-accent bg-accent/10 ring-1 ring-accent/30'
          : 'border-surface-border bg-surface-panel hover:border-zinc-600 hover:bg-zinc-800/60'
      }`}
    >
      {isActive ? (
        <div className="absolute top-2.5 right-2.5 grid place-items-center h-5 w-5 rounded-full bg-accent text-white">
          <Check size={12} />
        </div>
      ) : null}
      <div className="font-mono text-sm font-semibold text-zinc-100">
        {cls.class_code}
      </div>
      <div className="mt-1 text-[11px] text-zinc-500">
        Year {cls.year} · Section {cls.section}
      </div>
    </button>
  );
}

function FacultyListCard({ classId }) {
  const [faculty, setFaculty] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!classId) return;
    setLoading(true);
    fetchClassFaculty(classId)
      .then((res) => setFaculty(res?.faculty ?? []))
      .catch(() => setFaculty([]))
      .finally(() => setLoading(false));
  }, [classId]);

  if (loading) {
    return (
      <div className="card p-4 text-sm text-zinc-500 animate-pulse">
        Loading faculty...
      </div>
    );
  }

  if (faculty.length === 0) {
    return (
      <div className="card p-6 text-center">
        <UserCog size={24} className="mx-auto text-zinc-600 mb-2" />
        <p className="text-sm text-zinc-400">No faculty assigned to this class.</p>
        <p className="text-xs text-zinc-600 mt-1">
          Assign faculty from User Management.
        </p>
      </div>
    );
  }

  return (
    <div className="card overflow-hidden">
      <div className="px-4 py-3 border-b border-surface-border bg-surface-raised/40">
        <h3 className="text-xs font-medium uppercase tracking-wider text-zinc-500">
          Faculty assigned · {faculty.length}
        </h3>
      </div>
      <div className="divide-y divide-surface-border/60">
        {faculty.map((f) => (
          <div key={f.user_id} className="flex items-center gap-3 px-4 py-3">
            <div className="grid place-items-center h-8 w-8 rounded-full bg-zinc-800 text-zinc-400">
              <UserCog size={14} />
            </div>
            <span className="text-sm text-zinc-200">{f.username}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function AdminDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { grouped, activeClass, setActiveClass, loading: classLoading } = useClassContext();
  const { data: status } = useSessionStatus();

  const [stats, setStats] = useState({
    totalFaculty: null,
    totalSessions: null,
  });

  useEffect(() => {
    (async () => {
      try {
        const [userRes, sessRes] = await Promise.all([
          fetchUsers({ role: 'faculty' }).catch(() => ({ total: 0 })),
          fetchSessions({ limit: 1 }).catch(() => ({ total: 0 })),
        ]);
        setStats({
          totalFaculty: userRes?.total ?? 0,
          totalSessions: sessRes?.total ?? 0,
        });
      } catch {
        // ignore
      }
    })();
  }, []);

  const isRunning = status?.session_state === 'running';
  const majors = Object.keys(grouped).sort();

  return (
    <div>
      <PageHeader
        title={`Welcome, ${user?.username ?? 'Admin'}`}
        description="Select a class to scope your workspace."
      />

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <StatCard
          icon={GraduationCap}
          label="Active class"
          value={activeClass?.class_code ?? 'None'}
          color="text-sky-400"
        />
        <StatCard
          icon={Users}
          label="Faculty"
          value={stats.totalFaculty}
          color="text-emerald-400"
        />
        <StatCard
          icon={BookOpen}
          label="Sessions"
          value={stats.totalSessions}
          color="text-amber-400"
        />
        <StatCard
          icon={Radio}
          label="Runtime"
          value={isRunning ? 'Active' : 'Idle'}
          color={isRunning ? 'text-emerald-400' : 'text-zinc-400'}
        />
      </div>

      {/* Classes grouped by major */}
      {classLoading ? (
        <div className="card p-6 text-center text-sm text-zinc-500 animate-pulse">
          Loading classes...
        </div>
      ) : majors.length === 0 ? (
        <div className="card p-6 text-center">
          <GraduationCap size={28} className="mx-auto text-zinc-600 mb-2" />
          <p className="text-sm text-zinc-400">No classes created yet.</p>
          <p className="text-xs text-zinc-600 mt-1">Create classes from Academic Classes.</p>
        </div>
      ) : (
        <div className="space-y-5 mb-6">
          {majors.map((major) => (
            <div key={major}>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-3 px-1">
                {major}
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                {grouped[major].map((cls) => (
                  <ClassCard
                    key={cls.class_id}
                    cls={cls}
                    isActive={activeClass?.class_id === cls.class_id}
                    onSelect={setActiveClass}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Quick actions + faculty list when a class is selected */}
      {activeClass ? (
        <>
          <h3 className="text-xs font-medium uppercase tracking-wider text-zinc-500 mb-3">
            Quick actions
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
            <QuickAction
              icon={Play}
              label="Start attendance"
              onClick={() => navigate('/live')}
            />
            <QuickAction
              icon={ClipboardList}
              label="Session history"
              onClick={() => navigate('/sessions')}
            />
            <QuickAction
              icon={Users}
              label="Students"
              onClick={() => navigate('/students')}
            />
            <QuickAction
              icon={UserCog}
              label="User management"
              onClick={() => navigate('/users')}
            />
          </div>

          <FacultyListCard classId={activeClass.class_id} />
        </>
      ) : majors.length > 0 ? (
        <div className="text-center text-sm text-zinc-500 py-4">
          Select a class above to scope your workspace.
        </div>
      ) : null}
    </div>
  );
}

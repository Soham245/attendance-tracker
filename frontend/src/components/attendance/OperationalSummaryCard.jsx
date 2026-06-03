import { Users, ClipboardCheck, Camera, Activity } from 'lucide-react';
import RuntimeCard from '../common/RuntimeCard.jsx';

/**
 * Faculty-friendly operational summary. Shows metrics that matter for
 * running an attendance session: unique students present, attendance
 * records persisted, and system health at a glance.
 *
 * "Students present" = unique student IDs recognized this session.
 * "Attendance marked" = records successfully persisted to the database.
 */
export default function OperationalSummaryCard({ status }) {
  const recognition = status?.recognition ?? {};
  const operational = status?.runtime_metrics?.operational;
  const isRunning = recognition.state === 'running';

  const studentsPresent = operational?.unique_students_present ?? 0;
  const attendanceMarked = operational?.attendance_marked ?? 0;
  const cameraOnline = Boolean(recognition.camera_active);
  const modelLoaded = Boolean(recognition.model_loaded);

  return (
    <RuntimeCard
      title="Session overview"
      subtitle="Recognition activity at a glance."
    >
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Tile
          icon={Users}
          label="Students present"
          value={studentsPresent}
          color="text-emerald-300"
          active={isRunning}
        />
        <Tile
          icon={ClipboardCheck}
          label="Attendance marked"
          value={attendanceMarked}
          color="text-sky-300"
          active={isRunning}
        />
        <Tile
          icon={Camera}
          label="Camera"
          value={cameraOnline ? 'Online' : 'Offline'}
          color={cameraOnline ? 'text-emerald-300' : 'text-zinc-500'}
          active={isRunning}
        />
        <Tile
          icon={Activity}
          label="Runtime"
          value={isRunning ? 'Active' : modelLoaded ? 'Ready' : 'Idle'}
          color={isRunning ? 'text-emerald-300' : 'text-zinc-500'}
          active={isRunning}
        />
      </div>
    </RuntimeCard>
  );
}

function Tile({ icon: Icon, label, value, color }) {
  return (
    <div className="rounded-lg border border-surface-border bg-surface-raised/50 px-3 py-3 text-center">
      <div className="flex items-center justify-center gap-1.5 mb-2">
        <Icon size={14} className="text-zinc-500" />
        <span className="text-[10px] uppercase tracking-wider text-zinc-500">
          {label}
        </span>
      </div>
      <div className={`text-lg font-semibold tabular-nums ${color}`}>
        {value}
      </div>
    </div>
  );
}

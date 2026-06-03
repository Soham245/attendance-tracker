import { useNavigate } from 'react-router-dom';
import {
  GraduationCap,
  KeyRound,
  Mail,
  Shield,
  ShieldCheck,
  User,
} from 'lucide-react';
import PageHeader from '../components/common/PageHeader.jsx';
import Button from '../components/common/Button.jsx';
import { useAuth } from '../hooks/useAuth.js';
import { useClassContext } from '../context/ClassContext.jsx';
import { formatDateTime } from '../utils/format.js';

function InfoRow({ icon: Icon, label, value }) {
  return (
    <div className="flex items-start gap-3 py-2.5">
      <Icon size={15} className="mt-0.5 text-zinc-500 shrink-0" />
      <div>
        <div className="text-[11px] uppercase tracking-wider text-zinc-500">{label}</div>
        <div className="text-sm text-zinc-200">{value || '—'}</div>
      </div>
    </div>
  );
}

export default function Profile() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const isAdmin = user?.role === 'admin';
  const { classes: assignedClasses, activeClass } = useClassContext();
  const classNames = assignedClasses.map((a) => a.class_code);

  return (
    <div>
      <PageHeader
        title="My profile"
        description="Your account information."
        actions={
          <Button variant="ghost" onClick={() => navigate('/change-password')}>
            <KeyRound size={14} />
            Change password
          </Button>
        }
      />

      <div className="card max-w-lg p-6">
        <div className="flex items-center gap-3 mb-5 pb-4 border-b border-zinc-800">
          <div className="grid place-items-center h-10 w-10 rounded-full bg-accent/15 text-accent">
            <User size={20} />
          </div>
          <div>
            <div className="text-base font-semibold text-zinc-100">{user?.username}</div>
            <div className="flex items-center gap-1.5 text-xs text-zinc-400">
              {isAdmin ? <Shield size={11} /> : <ShieldCheck size={11} />}
              {user?.role}
            </div>
          </div>
        </div>

        <div className="divide-y divide-zinc-800/50">
          <InfoRow icon={User} label="Username" value={user?.username} />
          <InfoRow icon={Mail} label="Email" value={user?.email} />
          <InfoRow
            icon={isAdmin ? Shield : ShieldCheck}
            label="Role"
            value={user?.role}
          />
          <InfoRow
            icon={GraduationCap}
            label="Account created"
            value={formatDateTime(user?.created_at)}
          />
          {!isAdmin && classNames.length > 0 ? (
            <div className="py-2.5">
              <div className="flex items-center gap-2 mb-2">
                <GraduationCap size={15} className="text-zinc-500" />
                <div className="text-[11px] uppercase tracking-wider text-zinc-500">
                  Assigned classes
                </div>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {classNames.map((code) => (
                  <span
                    key={code}
                    className={`rounded-full px-2.5 py-0.5 text-xs font-mono ${
                      activeClass?.class_code === code
                        ? 'bg-accent/15 text-accent border border-accent/30'
                        : 'bg-sky-500/10 text-sky-300'
                    }`}
                  >
                    {code}
                  </span>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

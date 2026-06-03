import { NavLink } from 'react-router-dom';
import {
  BrainCircuit,
  CalendarCheck,
  ChevronDown,
  CircleUser,
  ClipboardList,
  GraduationCap,
  LayoutDashboard,
  Radio,
  ScanFace,
  UserCog,
  Users,
} from 'lucide-react';
import { cn } from '../../utils/cn.js';
import { useAuth } from '../../hooks/useAuth.js';
import { useClassContext } from '../../context/ClassContext.jsx';

const SHARED_NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/live', label: 'Live attendance', icon: Radio },
  { to: '/attendance', label: 'Attendance', icon: CalendarCheck },
  { to: '/sessions', label: 'Session history', icon: ClipboardList },
  { to: '/students', label: 'Students', icon: Users },
];

const ADMIN_ONLY_NAV = [
  { to: '/training', label: 'Training', icon: BrainCircuit },
];

const ADMIN_SECTION_NAV = [
  { to: '/classes', label: 'Academic classes', icon: GraduationCap },
  { to: '/users', label: 'User management', icon: UserCog },
];

export default function Sidebar() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';

  // Build nav items: faculty doesn't see Training.
  const primaryNav = isAdmin ? [...SHARED_NAV, ...ADMIN_ONLY_NAV] : SHARED_NAV;

  return (
    <aside className="hidden md:flex md:w-60 lg:w-64 shrink-0 flex-col border-r border-surface-border bg-surface-raised">
      <div className="flex items-center gap-2 px-5 h-14 border-b border-surface-border">
        <div className="grid place-items-center h-8 w-8 rounded-lg bg-accent/15 text-accent">
          <ScanFace size={18} />
        </div>
        <div className="leading-tight">
          <div className="text-sm font-semibold text-zinc-100">VisionAttend</div>
          <div className="text-[10px] uppercase tracking-wider text-zinc-500">
            Desktop
          </div>
        </div>
      </div>

      {/* Active class indicator */}
      <ActiveClassBadge />

      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <SectionLabel>Workspace</SectionLabel>
        <div className="mt-1 space-y-1">
          {primaryNav.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn('nav-item', isActive && 'nav-item-active')
              }
            >
              <Icon size={16} />
              <span>{label}</span>
            </NavLink>
          ))}
        </div>

        {isAdmin && ADMIN_SECTION_NAV.length > 0 ? (
          <>
            <SectionLabel className="mt-6">Admin</SectionLabel>
            <div className="mt-1 space-y-1">
              {ADMIN_SECTION_NAV.map(({ to, label, icon: Icon, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  className={({ isActive }) =>
                    cn('nav-item', isActive && 'nav-item-active')
                  }
                >
                  <Icon size={16} />
                  <span>{label}</span>
                </NavLink>
              ))}
            </div>
          </>
        ) : null}
      </nav>

      <div className="px-3 py-3 border-t border-surface-border">
        <NavLink
          to="/profile"
          className={({ isActive }) =>
            cn('nav-item', isActive && 'nav-item-active')
          }
        >
          <CircleUser size={16} />
          <span>My profile</span>
        </NavLink>
        <div className="px-3 mt-2 text-[11px] text-zinc-500">
          v0.1 · local runtime
        </div>
      </div>
    </aside>
  );
}

function ActiveClassBadge() {
  const { activeClass } = useClassContext();

  return (
    <NavLink
      to="/"
      className="flex items-center gap-2 mx-3 mt-3 px-3 py-2 rounded-lg bg-accent/10 border border-accent/20 transition-colors hover:bg-accent/15"
    >
      <GraduationCap size={14} className="text-accent shrink-0" />
      <div className="flex-1 min-w-0">
        {activeClass ? (
          <>
            <div className="text-xs font-semibold text-zinc-100 truncate">
              {activeClass.class_code}
            </div>
            <div className="text-[10px] text-zinc-500 truncate">
              {activeClass.major} · Y{activeClass.year} {activeClass.section}
            </div>
          </>
        ) : (
          <div className="text-xs text-zinc-400">No class selected</div>
        )}
      </div>
      <ChevronDown size={12} className="text-zinc-500 shrink-0" />
    </NavLink>
  );
}

function SectionLabel({ children, className }) {
  return (
    <div
      className={cn(
        'px-3 text-[10px] font-medium uppercase tracking-wider text-zinc-500',
        className,
      )}
    >
      {children}
    </div>
  );
}

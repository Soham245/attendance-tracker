import { useState } from 'react';
import { LogOut, User } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth.js';

export default function Header() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);

  return (
    <header className="h-14 border-b border-surface-border bg-surface-raised/60 backdrop-blur flex items-center px-6">
      <div>
        <div className="text-xs uppercase tracking-wider text-zinc-500">
          Workspace
        </div>
        <div className="text-sm font-medium text-zinc-200">
          Live attendance runtime
        </div>
      </div>

      <div className="ml-auto relative">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex items-center gap-2 rounded-lg border border-surface-border bg-surface-panel px-3 py-1.5 text-sm text-zinc-200 hover:bg-surface-hover transition-colors"
        >
          <span className="grid place-items-center h-6 w-6 rounded-full bg-accent/15 text-accent">
            <User size={14} />
          </span>
          <span className="hidden sm:inline">
            {user?.username ?? 'Account'}
          </span>
          {user?.role ? (
            <span className="hidden sm:inline rounded-md bg-surface-hover px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-zinc-400">
              {user.role}
            </span>
          ) : null}
        </button>

        {open ? (
          <div
            className="absolute right-0 mt-2 w-48 rounded-lg border border-surface-border bg-surface-panel shadow-xl py-1 z-30"
            onMouseLeave={() => setOpen(false)}
          >
            <div className="px-3 py-2 border-b border-surface-border">
              <div className="text-xs text-zinc-500">Signed in as</div>
              <div className="text-sm text-zinc-200 truncate">
                {user?.email ?? user?.username ?? '—'}
              </div>
            </div>
            <button
              type="button"
              onClick={() => {
                setOpen(false);
                logout();
              }}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-zinc-300 hover:bg-surface-hover hover:text-zinc-100"
            >
              <LogOut size={14} />
              Sign out
            </button>
          </div>
        ) : null}
      </div>
    </header>
  );
}

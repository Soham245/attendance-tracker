import { Link } from 'react-router-dom';
import { Compass } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="min-h-full grid place-items-center px-4 py-10 bg-surface">
      <div className="text-center max-w-sm">
        <div className="mx-auto grid place-items-center h-11 w-11 rounded-xl bg-surface-panel border border-surface-border text-zinc-400 mb-3">
          <Compass size={22} />
        </div>
        <h1 className="text-xl font-semibold text-zinc-100">Page not found</h1>
        <p className="mt-1 text-sm text-zinc-500">
          The page you were looking for doesn't exist or has been moved.
        </p>
        <Link to="/" className="btn-primary mt-5 inline-flex">
          Back to dashboard
        </Link>
      </div>
    </div>
  );
}

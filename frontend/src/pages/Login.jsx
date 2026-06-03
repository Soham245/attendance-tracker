import { motion } from 'framer-motion';
import { ScanFace } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import LoginForm from '../components/auth/LoginForm.jsx';

export default function Login() {
  const navigate = useNavigate();

  return (
    <div className="min-h-full grid place-items-center px-4 py-10 bg-surface">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, ease: 'easeOut' }}
        className="w-full max-w-sm"
      >
        <div className="flex flex-col items-center text-center mb-8">
          <div className="grid place-items-center h-11 w-11 rounded-xl bg-accent/15 text-accent mb-3">
            <ScanFace size={22} />
          </div>
          <h1 className="text-xl font-semibold text-zinc-100">
            Sign in to VisionAttend
          </h1>
          <p className="mt-1 text-sm text-zinc-500">
            Local desktop attendance runtime
          </p>
        </div>

        <div className="card-padded">
          <LoginForm onSuccess={() => navigate('/', { replace: true })} />
        </div>

        <p className="mt-4 text-center text-xs text-zinc-600">
          Your session is stored locally on this device.
        </p>
      </motion.div>
    </div>
  );
}

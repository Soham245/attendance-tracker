import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { KeyRound } from 'lucide-react';
import { motion } from 'framer-motion';
import Button from '../components/common/Button.jsx';
import PasswordInput from '../components/common/PasswordInput.jsx';
import { changePassword } from '../services/authService.js';
import { errorMessage } from '../services/api.js';
import { useAuth } from '../hooks/useAuth.js';
import { useToast } from '../context/ToastContext.jsx';

export default function ChangePassword() {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const isForced = user?.must_change_password;

  const [form, setForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (form.newPassword !== form.confirmPassword) {
      setError('New password and confirmation do not match.');
      return;
    }
    if (form.newPassword.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }
    setLoading(true);
    try {
      await changePassword({
        currentPassword: form.currentPassword,
        newPassword: form.newPassword,
        confirmPassword: form.confirmPassword,
      });
      await refreshUser();
      toast.success('Password changed', 'Your password has been updated.');
      navigate('/');
    } catch (err) {
      setError(errorMessage(err, 'Failed to change password'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={isForced ? 'min-h-full grid place-items-center px-4 py-10 bg-surface' : ''}>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, ease: 'easeOut' }}
        className={isForced ? 'w-full max-w-sm' : 'max-w-md mx-auto'}
      >
        {isForced ? (
          <div className="flex flex-col items-center text-center mb-8">
            <div className="grid place-items-center h-11 w-11 rounded-xl bg-amber-500/15 text-amber-400 mb-3">
              <KeyRound size={22} />
            </div>
            <h1 className="text-xl font-semibold text-zinc-100">
              Change your password
            </h1>
            <p className="mt-1 text-sm text-zinc-500">
              Your password must be changed before you can continue.
            </p>
          </div>
        ) : (
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-zinc-100">Change password</h2>
            <p className="mt-1 text-sm text-zinc-500">
              Update your account password.
            </p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="card p-6 space-y-4">
          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1">
              Current password
            </label>
            <PasswordInput
              name="currentPassword"
              value={form.currentPassword}
              onChange={handleChange}
              required
              className="w-full rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 pr-9 text-sm
                         text-zinc-200 placeholder:text-zinc-600 focus:border-accent
                         focus:outline-none focus:ring-1 focus:ring-accent"
              placeholder="Enter current password"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1">
              New password
            </label>
            <PasswordInput
              name="newPassword"
              value={form.newPassword}
              onChange={handleChange}
              required
              minLength={6}
              className="w-full rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 pr-9 text-sm
                         text-zinc-200 placeholder:text-zinc-600 focus:border-accent
                         focus:outline-none focus:ring-1 focus:ring-accent"
              placeholder="At least 6 characters"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1">
              Confirm new password
            </label>
            <PasswordInput
              name="confirmPassword"
              value={form.confirmPassword}
              onChange={handleChange}
              required
              minLength={6}
              className="w-full rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 pr-9 text-sm
                         text-zinc-200 placeholder:text-zinc-600 focus:border-accent
                         focus:outline-none focus:ring-1 focus:ring-accent"
              placeholder="Confirm new password"
            />
          </div>

          {error ? (
            <div className="rounded-md bg-rose-500/10 border border-rose-500/20 px-3 py-2 text-xs text-rose-400">
              {error}
            </div>
          ) : null}

          <div className="flex items-center gap-3 pt-2">
            <Button type="submit" loading={loading} className="flex-1">
              <KeyRound size={14} />
              Change password
            </Button>
            {!isForced ? (
              <Button
                variant="ghost"
                type="button"
                onClick={() => navigate(-1)}
                disabled={loading}
              >
                Cancel
              </Button>
            ) : null}
          </div>
        </form>
      </motion.div>
    </div>
  );
}

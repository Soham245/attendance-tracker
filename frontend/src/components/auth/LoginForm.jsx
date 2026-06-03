import { useState } from 'react';
import { AlertCircle, Lock, User } from 'lucide-react';
import PasswordInput from '../common/PasswordInput.jsx';
import Button from '../common/Button.jsx';
import { useAuth } from '../../hooks/useAuth.js';
import { errorMessage } from '../../services/api.js';

export default function LoginForm({ onSuccess }) {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (submitting) return;
    setError(null);
    setSubmitting(true);
    try {
      await login(username.trim(), password);
      onSuccess?.();
    } catch (err) {
      setError(errorMessage(err, 'Unable to sign in'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      <Field
        id="username"
        label="Username"
        icon={User}
        value={username}
        onChange={setUsername}
        autoComplete="username"
        autoFocus
      />

      <Field
        id="password"
        label="Password"
        icon={Lock}
        type="password"
        value={password}
        onChange={setPassword}
        autoComplete="current-password"
      />

      {error ? (
        <div className="flex items-start gap-2 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
          <AlertCircle size={16} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      ) : null}

      <Button
        type="submit"
        className="w-full"
        loading={submitting}
        disabled={!username || !password}
      >
        {submitting ? 'Signing in…' : 'Sign in'}
      </Button>
    </form>
  );
}

function Field({ id, label, icon: Icon, value, onChange, type = 'text', ...rest }) {
  const isPassword = type === 'password';
  const InputComponent = isPassword ? PasswordInput : 'input';

  return (
    <label htmlFor={id} className="block">
      <span className="mb-1.5 block text-xs font-medium text-zinc-400">
        {label}
      </span>
      <div className="relative">
        <Icon
          size={15}
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 z-10"
        />
        <InputComponent
          id={id}
          {...(isPassword ? {} : { type })}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={`input pl-9${isPassword ? ' pr-9' : ''}`}
          {...rest}
        />
      </div>
    </label>
  );
}

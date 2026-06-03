import { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';

/**
 * Password input with a visibility toggle button.
 *
 * Accepts the same props as a normal `<input>` — it just swaps
 * `type` between "password" and "text" and shows an eye icon.
 */
export default function PasswordInput({ className = '', ...rest }) {
  const [visible, setVisible] = useState(false);

  return (
    <div className="relative">
      <input
        {...rest}
        type={visible ? 'text' : 'password'}
        className={className}
      />
      <button
        type="button"
        tabIndex={-1}
        onClick={() => setVisible((v) => !v)}
        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 transition-colors"
        aria-label={visible ? 'Hide password' : 'Show password'}
      >
        {visible ? <EyeOff size={15} /> : <Eye size={15} />}
      </button>
    </div>
  );
}

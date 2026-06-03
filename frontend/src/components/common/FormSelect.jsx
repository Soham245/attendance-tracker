import { forwardRef } from 'react';
import { cn } from '../../utils/cn.js';

const FormSelect = forwardRef(function FormSelect(
  { label, error, id, options = [], className, placeholder, required, ...props },
  ref,
) {
  return (
    <label htmlFor={id} className="block">
      {label ? (
        <div className="mb-1.5 text-xs font-medium text-zinc-300">
          {label}
          {required ? <span className="ml-0.5 text-rose-400">*</span> : null}
        </div>
      ) : null}
      <select
        ref={ref}
        id={id}
        className={cn(
          'input appearance-none cursor-pointer',
          error && 'border-rose-500/60',
          className,
        )}
        {...props}
      >
        {placeholder ? (
          <option value="" disabled>
            {placeholder}
          </option>
        ) : null}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {error ? (
        <div className="mt-1 text-xs text-rose-300">{error}</div>
      ) : null}
    </label>
  );
});

export default FormSelect;

import { forwardRef } from 'react';
import { cn } from '../../utils/cn.js';

const FormInput = forwardRef(function FormInput(
  { label, hint, error, id, className, required, ...props },
  ref,
) {
  return (
    <label htmlFor={id} className="block">
      {label ? (
        <div className="mb-1.5 flex items-center justify-between">
          <span className="text-xs font-medium text-zinc-300">
            {label}
            {required ? <span className="ml-0.5 text-rose-400">*</span> : null}
          </span>
          {hint ? (
            <span className="text-[10px] text-zinc-500">{hint}</span>
          ) : null}
        </div>
      ) : null}
      <input
        ref={ref}
        id={id}
        className={cn(
          'input',
          error && 'border-rose-500/60 focus:border-rose-500 focus:ring-rose-500/40',
          className,
        )}
        {...props}
      />
      {error ? (
        <div className="mt-1 text-xs text-rose-300">{error}</div>
      ) : null}
    </label>
  );
});

export default FormInput;

"use client";

import { forwardRef } from "react";

type AuthFieldProps = React.InputHTMLAttributes<HTMLInputElement> & {
  id: string;
  label: string;
  hint?: string;
  error?: string;
};

export const AuthField = forwardRef<HTMLInputElement, AuthFieldProps>(function AuthField(
  { id, label, type = "text", placeholder, hint, error, className, ...rest },
  ref,
) {
  const inputClassName = [
    "w-full rounded-xl border bg-white px-4 py-2.5 text-slate-900 placeholder:text-slate-400 transition-colors outline-none",
    error
      ? "border-red-300 focus:border-red-400 focus:ring-4 focus:ring-red-100"
      : "border-slate-200 focus:border-[var(--primary)] focus:ring-4 focus:ring-sky-100",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-medium text-slate-700">
        {label}
      </label>
      <input
        ref={ref}
        id={id}
        name={id}
        type={type}
        placeholder={placeholder}
        className={inputClassName}
        aria-invalid={error ? true : undefined}
        {...rest}
      />
      {error ? <p className="text-xs text-red-600">{error}</p> : hint ? <p className="text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
});

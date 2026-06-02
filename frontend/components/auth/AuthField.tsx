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
    "w-full rounded-xl border bg-[var(--background)] px-4 py-2.5 text-[var(--foreground)] placeholder:text-[var(--subtle)] transition-colors outline-none",
    error
      ? "border-[var(--danger-border)] focus:border-[var(--danger-text)] focus:ring-4 focus:ring-[color:var(--danger-bg)]"
      : "border-[var(--border)] focus:border-[var(--primary)] focus:ring-4 focus:ring-[color:var(--focus-ring)]",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-medium text-[var(--foreground)]">
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
      {error ? <p className="text-xs text-[var(--danger-text)]">{error}</p> : hint ? <p className="text-xs text-[var(--muted)]">{hint}</p> : null}
    </div>
  );
});

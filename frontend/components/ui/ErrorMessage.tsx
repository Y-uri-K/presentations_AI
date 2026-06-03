import type { ReactNode } from "react";

type ErrorMessageProps = {
  children: ReactNode;
  className?: string;
  variant?: "block" | "text";
};

export function ErrorMessage({ children, className = "", variant = "block" }: ErrorMessageProps) {
  if (!children) {
    return null;
  }

  if (variant === "text") {
    return (
      <p className={`text-sm text-[var(--danger-text)] ${className}`.trim()}>
        {children}
      </p>
    );
  }

  return (
    <p
      className={`rounded-lg border border-[var(--danger-border)] bg-[var(--danger-bg)] px-3 py-2 text-sm text-[var(--danger-text)] ${className}`.trim()}
    >
      {children}
    </p>
  );
}

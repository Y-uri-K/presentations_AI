"use client";

import type { FormEvent, ReactNode } from "react";

type AuthFormProps = {
  children: ReactNode;
  className?: string;
};

export function AuthForm({ children, className = "space-y-5" }: AuthFormProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
  }

  return (
    <form className={className} onSubmit={handleSubmit} noValidate>
      {children}
    </form>
  );
}

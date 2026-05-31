"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { ROUTES } from "@/lib/auth/constants";
import { ensureValidSession } from "@/lib/auth/session";

type AuthGuardProps = {
  children: ReactNode;
};

export function AuthGuard({ children }: AuthGuardProps) {
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    let cancelled = false;

    ensureValidSession().then((ok) => {
      if (cancelled) {
        return;
      }
      if (!ok) {
        router.replace(ROUTES.login);
        return;
      }
      setAllowed(true);
    });

    return () => {
      cancelled = true;
    };
  }, [router]);

  if (!allowed) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--background)]">
        <p className="text-sm text-slate-500">Проверка авторизации…</p>
      </div>
    );
  }

  return <>{children}</>;
}

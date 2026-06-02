"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { ROUTES } from "@/lib/auth/constants";
import { ensureValidSession } from "@/lib/auth/session";

type GuestGuardProps = {
  children: ReactNode;
};

/** На страницах входа/регистрации — переадресация в кабинет, если сессия уже активна. */
export function GuestGuard({ children }: GuestGuardProps) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;

    ensureValidSession().then((ok) => {
      if (cancelled) {
        return;
      }
      if (ok) {
        router.replace(ROUTES.dashboard);
        return;
      }
      setReady(true);
    });

    return () => {
      cancelled = true;
    };
  }, [router]);

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--background)]">
        <p className="text-sm text-[var(--muted)]">Загрузка…</p>
      </div>
    );
  }

  return <>{children}</>;
}

"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

import { fetchMe, type UserMeResponse } from "@/lib/api/auth";
import { ROUTES } from "@/lib/auth/constants";
import { getAccessToken } from "@/lib/auth/token";

export function AppHeader() {
  const [user, setUser] = useState<UserMeResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    const accessToken = getAccessToken();

    if (!accessToken) {
      return;
    }

    fetchMe(accessToken)
      .then((profile) => {
        if (!cancelled) {
          setUser(profile);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setUser(null);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <header className="sticky top-0 z-10 border-b border-[var(--border)] bg-[var(--surface)]/85 backdrop-blur-sm">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <Link
          href={ROUTES.dashboard}
          className="inline-flex h-11 items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 text-sm font-medium text-[var(--foreground)] shadow-sm transition-colors hover:border-[var(--primary)] hover:bg-[var(--surface-muted)]"
        >
          <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            className="h-4 w-4 text-[var(--muted)]"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="m3 11 9-8 9 8" />
            <path d="M5 10v10h14V10" />
            <path d="M9 20v-6h6v6" />
          </svg>
          Главная
        </Link>
        <Link
          href={ROUTES.profile}
          className="inline-flex h-11 max-w-[240px] items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] py-1 pl-4 pr-1 text-sm font-medium text-[var(--foreground)] shadow-sm transition-colors hover:border-[var(--primary)] hover:bg-[var(--surface-muted)]"
          aria-label="Личный кабинет"
          title="Личный кабинет"
        >
          <span className="truncate">{user?.username ?? "Профиль"}</span>
          <span className="relative inline-flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] text-[var(--muted)]">
            {user?.profile_image ? (
              <Image
                src={user.profile_image}
                alt="Фото профиля"
                fill
                sizes="40px"
                unoptimized
                className="object-cover"
              />
            ) : (
              <svg
                aria-hidden="true"
                viewBox="0 0 24 24"
                className="h-5 w-5"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M20 21a8 8 0 0 0-16 0" />
                <circle cx="12" cy="8" r="4" />
              </svg>
            )}
          </span>
        </Link>
      </div>
    </header>
  );
}

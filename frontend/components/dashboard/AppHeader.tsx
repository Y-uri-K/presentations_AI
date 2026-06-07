"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

import { fetchMe, type UserMeResponse } from "@/lib/api/auth";
import { ROUTES } from "@/lib/auth/constants";
import { getAccessToken } from "@/lib/auth/token";

const NAV_LINKS = [
  {
    href: ROUTES.dashboard,
    label: "Главная",
    icon: (
      <svg
        aria-hidden="true"
        viewBox="0 0 24 24"
        className="h-4 w-4 shrink-0"
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
    ),
  },
  {
    href: ROUTES.templates,
    label: "Шаблоны",
    icon: (
      <svg
        aria-hidden="true"
        viewBox="0 0 24 24"
        className="h-4 w-4 shrink-0"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </svg>
    ),
  },
] as const;

function navLinkClassName(isMobile = false) {
  return [
    "inline-flex items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--surface)] text-sm font-medium text-[var(--foreground)] shadow-sm transition-colors hover:border-[var(--primary)] hover:bg-[var(--surface-muted)]",
    isMobile ? "w-full px-4 py-3" : "h-11 px-3 sm:px-4",
  ].join(" ");
}

export function AppHeader() {
  const [user, setUser] = useState<UserMeResponse | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

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

  useEffect(() => {
    if (!menuOpen) {
      return;
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMenuOpen(false);
      }
    }

    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleEscape);

    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleEscape);
    };
  }, [menuOpen]);

  return (
    <header className="sticky top-0 z-30 border-b border-[var(--border)] bg-[var(--surface)]/85 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-2 px-4 sm:h-16 sm:px-6">
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-[var(--border)] bg-[var(--surface)] text-[var(--foreground)] shadow-sm transition-colors hover:border-[var(--primary)] hover:bg-[var(--surface-muted)] md:hidden"
            aria-expanded={menuOpen}
            aria-controls="mobile-nav"
            aria-label={menuOpen ? "Закрыть меню" : "Открыть меню"}
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? (
              <svg
                aria-hidden="true"
                viewBox="0 0 24 24"
                className="h-5 w-5"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              >
                <path d="M6 6l12 12M18 6 6 18" />
              </svg>
            ) : (
              <svg
                aria-hidden="true"
                viewBox="0 0 24 24"
                className="h-5 w-5"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              >
                <path d="M4 7h16M4 12h16M4 17h16" />
              </svg>
            )}
          </button>

          <nav className="hidden items-center gap-2 md:flex" aria-label="Основная навигация">
            {NAV_LINKS.map((item) => (
              <Link key={item.href} href={item.href} className={navLinkClassName()}>
                <span className="text-[var(--muted)]">{item.icon}</span>
                {item.label}
              </Link>
            ))}
          </nav>
        </div>

        <Link
          href={ROUTES.dashboard}
          className="flex-1 truncate text-center text-sm font-bold text-[var(--foreground)] md:hidden"
        >
          AIDeck
        </Link>

        <div className="hidden flex-1 md:block" aria-hidden="true" />

        <Link
          href={ROUTES.profile}
          className="inline-flex h-11 shrink-0 items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--surface)] py-1 pl-2 pr-1 text-sm font-medium text-[var(--foreground)] shadow-sm transition-colors hover:border-[var(--primary)] hover:bg-[var(--surface-muted)] sm:gap-3 sm:pl-4"
          aria-label="Личный кабинет"
          title="Личный кабинет"
        >
          <span className="hidden max-w-[140px] truncate sm:inline md:max-w-[200px]">
            {user?.username ?? "Профиль"}
          </span>
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

      {menuOpen ? (
        <>
          <button
            type="button"
            className="fixed inset-0 top-14 z-20 bg-slate-950/40 md:hidden"
            aria-label="Закрыть меню"
            onClick={() => setMenuOpen(false)}
          />
          <nav
            id="mobile-nav"
            className="absolute left-0 right-0 top-full z-30 border-b border-[var(--border)] bg-[var(--surface)] p-4 shadow-lg md:hidden"
            aria-label="Мобильная навигация"
          >
            <div className="mx-auto flex max-w-6xl flex-col gap-2">
              {NAV_LINKS.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={navLinkClassName(true)}
                  onClick={() => setMenuOpen(false)}
                >
                  <span className="text-[var(--muted)]">{item.icon}</span>
                  {item.label}
                </Link>
              ))}
            </div>
          </nav>
        </>
      ) : null}
    </header>
  );
}

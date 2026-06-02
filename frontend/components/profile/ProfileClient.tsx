"use client";

import { type ChangeEvent, type FormEvent, useEffect, useMemo, useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";

import {
  ApiError,
  deleteCurrentAccount,
  fetchMe,
  updateMe,
  uploadProfileImage,
  type UserMeResponse,
} from "@/lib/api/auth";
import { ROUTES } from "@/lib/auth/constants";
import { ensureValidSession } from "@/lib/auth/session";
import { clearTokens, getAccessToken } from "@/lib/auth/token";
import {
  applyAppTheme,
  getSavedAppTheme,
  type AppTheme,
} from "@/components/theme/ThemeInitializer";

type StatusKind = "success" | "error" | "info";

type StatusMessage = {
  kind: StatusKind;
  text: string;
};

function getInitial(username: string) {
  return username.trim().slice(0, 1).toUpperCase() || "U";
}

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof ApiError ? error.message : fallback;
}

export function ProfileClient() {
  const router = useRouter();
  const [user, setUser] = useState<UserMeResponse | null>(null);
  const [username, setUsername] = useState("");
  const [theme, setTheme] = useState<AppTheme>("light");
  const [loading, setLoading] = useState(true);
  const [savingUsername, setSavingUsername] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [status, setStatus] = useState<StatusMessage | null>(null);

  const usernameChanged = useMemo(() => {
    return user ? username.trim() !== user.username : false;
  }, [user, username]);

  useEffect(() => {
    let cancelled = false;

    async function loadProfile() {
      const ok = await ensureValidSession();
      const accessToken = getAccessToken();

      if (!ok || !accessToken) {
        router.replace(ROUTES.login);
        return;
      }

      try {
        const profile = await fetchMe(accessToken);
        if (cancelled) {
          return;
        }
        setUser(profile);
        setUsername(profile.username);
        setTheme(getSavedAppTheme());
      } catch (error) {
        if (!cancelled) {
          setStatus({ kind: "error", text: getErrorMessage(error, "Не удалось загрузить профиль") });
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadProfile();

    return () => {
      cancelled = true;
    };
  }, [router]);

  function handleThemeChange(nextTheme: AppTheme) {
    setTheme(nextTheme);
    applyAppTheme(nextTheme);
    setStatus({
      kind: "success",
      text: nextTheme === "dark" ? "Включена тёмная тема" : "Включена светлая тема",
    });
  }

  async function handleUsernameSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const accessToken = getAccessToken();
    const nextUsername = username.trim();

    if (!accessToken || !user || !usernameChanged) {
      return;
    }

    setSavingUsername(true);
    setStatus(null);

    try {
      const updated = await updateMe(accessToken, { username: nextUsername });
      setUser(updated);
      setUsername(updated.username);
      setStatus({ kind: "success", text: "Username обновлён и сохранён в базе" });
    } catch (error) {
      setStatus({ kind: "error", text: getErrorMessage(error, "Не удалось сохранить username") });
    } finally {
      setSavingUsername(false);
    }
  }

  async function handleImageChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    const accessToken = getAccessToken();
    if (!file || !accessToken) {
      return;
    }

    setUploadingImage(true);
    setStatus(null);

    try {
      const updated = await uploadProfileImage(accessToken, file);
      setUser(updated);
      setStatus({ kind: "success", text: "Фото профиля обновлено и сохранено в базе" });
    } catch (error) {
      setStatus({ kind: "error", text: getErrorMessage(error, "Не удалось загрузить фото") });
    } finally {
      setUploadingImage(false);
      event.target.value = "";
    }
  }

  function handleLogout() {
    clearTokens();
    router.push(ROUTES.login);
  }

  async function handleDeleteAccount() {
    const confirmed = window.confirm(
      "Удалить аккаунт? Это действие нельзя отменить. Все связанные данные будут удалены.",
    );
    const accessToken = getAccessToken();

    if (!confirmed || !accessToken) {
      return;
    }

    setDeleting(true);
    setStatus(null);

    try {
      await deleteCurrentAccount(accessToken);
      clearTokens();
      router.replace(ROUTES.register);
    } catch (error) {
      setStatus({ kind: "error", text: getErrorMessage(error, "Не удалось удалить аккаунт") });
      setDeleting(false);
    }
  }

  if (loading) {
    return (
      <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-8 text-sm text-[var(--muted)] shadow-sm">
        Загрузка профиля…
      </div>
    );
  }

  if (!user) {
    return (
      <div className="rounded-2xl border border-[var(--danger-border)] bg-[var(--danger-bg)] p-8 text-sm text-[var(--danger-text)] shadow-sm">
        Профиль не найден.
      </div>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
      <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-sm sm:p-8">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
          <div className="relative h-28 w-28 shrink-0 overflow-hidden rounded-3xl border border-[var(--border)] bg-[var(--surface-muted)]">
            {user.profile_image ? (
              <Image
                src={user.profile_image}
                alt="Фото профиля"
                fill
                sizes="112px"
                unoptimized
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center text-4xl font-bold text-[var(--primary)]">
                {getInitial(user.username)}
              </div>
            )}
          </div>

          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-[var(--muted)]">Профиль</p>
            <h1 className="mt-1 truncate text-3xl font-bold text-[var(--foreground)]">
              {user.username}
            </h1>
            <p className="mt-2 text-sm text-[var(--muted)]">{user.email}</p>

            <label className="mt-5 inline-flex cursor-pointer items-center rounded-xl bg-[var(--primary)] px-4 py-2 text-sm font-semibold text-[var(--on-primary)] shadow-sm transition-colors hover:bg-[var(--primary-dark)]">
              {uploadingImage ? "Загрузка…" : "Сменить / добавить фото"}
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp,image/gif"
                className="sr-only"
                disabled={uploadingImage}
                onChange={handleImageChange}
              />
            </label>
            <p className="mt-2 text-xs text-[var(--muted)]">
              JPG, PNG, WEBP или GIF до 2 МБ. Новая фотография перезапишет старую.
            </p>
          </div>
        </div>

        <form className="mt-8 border-t border-[var(--border)] pt-6" onSubmit={handleUsernameSubmit}>
          <label className="block text-sm font-semibold text-[var(--foreground)]" htmlFor="username">
            Username
          </label>
          <div className="mt-2 flex flex-col gap-3 sm:flex-row">
            <input
              id="username"
              value={username}
              minLength={3}
              maxLength={64}
              pattern="[A-Za-z0-9_]+"
              onChange={(event) => setUsername(event.target.value)}
              className="min-h-11 flex-1 rounded-xl border border-[var(--border)] bg-[var(--background)] px-4 text-sm text-[var(--foreground)] outline-none transition-colors focus:border-[var(--primary)]"
              placeholder="username"
            />
            <button
              type="submit"
              disabled={!usernameChanged || savingUsername}
              className="rounded-xl bg-[var(--primary)] px-5 py-2.5 text-sm font-semibold text-[var(--on-primary)] transition-colors hover:bg-[var(--primary-dark)] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {savingUsername ? "Сохранение…" : "Сохранить"}
            </button>
          </div>
          <p className="mt-2 text-xs text-[var(--muted)]">
            Допустимы латинские буквы, цифры и подчёркивание.
          </p>
        </form>

        {status && (
          <div
            className={`mt-6 rounded-xl border px-4 py-3 text-sm ${
              status.kind === "error"
                ? "border-[var(--danger-border)] bg-[var(--danger-bg)] text-[var(--danger-text)]"
                : status.kind === "success"
                  ? "border-[var(--success-border)] bg-[var(--success-bg)] text-[var(--success-text)]"
                  : "border-[var(--border)] bg-[var(--surface-muted)] text-[var(--foreground)]"
            }`}
          >
            {status.text}
          </div>
        )}
      </section>

      <aside className="space-y-6">
        <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-[var(--foreground)]">Тема интерфейса</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">Переключение применяется сразу.</p>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => handleThemeChange("light")}
              className={`rounded-xl border px-4 py-3 text-sm font-semibold transition-colors ${
                theme === "light"
                  ? "border-[var(--primary)] bg-[var(--accent-light)] text-[var(--primary-dark)]"
                  : "border-[var(--border)] text-[var(--muted)] hover:border-[var(--primary)]"
              }`}
            >
              Светлая
            </button>
            <button
              type="button"
              onClick={() => handleThemeChange("dark")}
              className={`rounded-xl border px-4 py-3 text-sm font-semibold transition-colors ${
                theme === "dark"
                  ? "border-[var(--primary)] bg-[var(--surface-muted)] text-[var(--primary)]"
                  : "border-[var(--border)] text-[var(--muted)] hover:border-[var(--primary)]"
              }`}
            >
              Тёмная
            </button>
          </div>
        </section>

        <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-[var(--foreground)]">Роль</h2>
          <div className="mt-3 inline-flex rounded-full border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-1 text-sm font-semibold uppercase tracking-wide text-[var(--muted)]">
            {user.role}
          </div>
          <p className="mt-3 text-sm text-[var(--muted)]">
            Здесь будет отображаться роль пользователя: user или admin.
          </p>
        </section>

        <section className="rounded-2xl border border-[var(--danger-border)] bg-[var(--danger-bg)] p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-[var(--danger-text)]">Аккаунт</h2>
          <div className="mt-4 grid gap-3">
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-xl border border-[var(--danger-border)] bg-[var(--surface)] px-4 py-2.5 text-sm font-semibold text-[var(--danger-text)] transition-colors hover:bg-[var(--surface-muted)]"
            >
              Выйти из аккаунта
            </button>
            <button
              type="button"
              onClick={handleDeleteAccount}
              disabled={deleting}
              className="rounded-xl bg-[var(--danger-text)] px-4 py-2.5 text-sm font-semibold text-[var(--surface)] transition-colors hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {deleting ? "Удаление…" : "Удалить аккаунт"}
            </button>
          </div>
        </section>
      </aside>
    </div>
  );
}

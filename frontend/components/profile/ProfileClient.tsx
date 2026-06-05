"use client";

import { type ChangeEvent, type FormEvent, useEffect, useMemo, useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";

import {
  ApiError,
  deleteCurrentAccount,
  deleteProfileImage,
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
import { ErrorMessage } from "@/components/ui/ErrorMessage";

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

function validateUsername(value: string) {
  const trimmed = value.trim();
  if (trimmed.length < 3) {
    return "Логин — не менее 3 символов";
  }
  if (trimmed.length > 64) {
    return "Логин — не более 64 символов";
  }
  if (!/^[a-zA-Z0-9_]+$/.test(trimmed)) {
    return "Только латиница, цифры и подчёркивание";
  }
  return null;
}

export function ProfileClient() {
  const router = useRouter();
  const [user, setUser] = useState<UserMeResponse | null>(null);
  const [username, setUsername] = useState("");
  const [fullName, setFullName] = useState("");
  const [theme, setTheme] = useState<AppTheme>("light");
  const [loading, setLoading] = useState(true);
  const [savingProfile, setSavingProfile] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [deletingImage, setDeletingImage] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [status, setStatus] = useState<StatusMessage | null>(null);

  const usernameChanged = useMemo(() => {
    return user ? username.trim() !== user.username : false;
  }, [user, username]);

  const fullNameChanged = useMemo(() => {
    return user ? fullName.trim() !== (user.full_name ?? "") : false;
  }, [fullName, user]);

  const profileChanged = usernameChanged || fullNameChanged;
  const usernameError = usernameChanged ? validateUsername(username) : null;

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
        setFullName(profile.full_name ?? "");
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

  async function handleProfileSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const accessToken = getAccessToken();
    const nextUsername = username.trim();
    const nextFullName = fullName.trim();

    if (!accessToken || !user || !profileChanged || usernameError) {
      return;
    }

    setSavingProfile(true);
    setStatus(null);

    try {
      const updated = await updateMe(accessToken, {
        username: nextUsername,
        full_name: nextFullName || null,
      });
      setUser(updated);
      setUsername(updated.username);
      setFullName(updated.full_name ?? "");
      setStatus({ kind: "success", text: "Профиль обновлён и сохранён в базе" });
    } catch (error) {
      setStatus({ kind: "error", text: getErrorMessage(error, "Не удалось сохранить профиль") });
    } finally {
      setSavingProfile(false);
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

  async function handleDeleteImage() {
    const accessToken = getAccessToken();
    if (!accessToken || !user?.profile_image) {
      return;
    }

    setDeletingImage(true);
    setStatus(null);

    try {
      const updated = await deleteProfileImage(accessToken);
      setUser(updated);
      setStatus({ kind: "success", text: "Фото профиля удалено" });
    } catch (error) {
      setStatus({ kind: "error", text: getErrorMessage(error, "Не удалось удалить фото") });
    } finally {
      setDeletingImage(false);
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
      <ErrorMessage className="rounded-2xl p-8 shadow-sm">
        Профиль не найден.
      </ErrorMessage>
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
            {user.full_name ? (
              <p className="mt-2 text-sm font-semibold text-[var(--foreground)]">{user.full_name}</p>
            ) : null}
            <p className="mt-2 text-sm text-[var(--muted)]">{user.email}</p>

            <div className="mt-5 flex flex-wrap gap-3">
              <label className="inline-flex cursor-pointer items-center rounded-xl bg-[var(--primary)] px-4 py-2 text-sm font-semibold text-[var(--on-primary)] shadow-sm transition-colors hover:bg-[var(--primary-dark)]">
                {uploadingImage
                  ? "Загрузка…"
                  : user.profile_image
                    ? "Сменить фото"
                    : "Добавить фото"}
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp,image/gif"
                  className="sr-only"
                  disabled={uploadingImage}
                  onChange={handleImageChange}
                />
              </label>
              {user.profile_image ? (
                <button
                  type="button"
                  onClick={handleDeleteImage}
                  disabled={deletingImage}
                  className="rounded-xl border border-[var(--danger-border)] bg-[var(--danger-bg)] px-4 py-2 text-sm font-semibold text-[var(--danger-text)] transition-colors hover:opacity-85 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {deletingImage ? "Удаление…" : "Удалить фото"}
                </button>
              ) : null}
            </div>
            <p className="mt-2 text-xs text-[var(--muted)]">
              JPG, PNG, WEBP или GIF до 2 МБ. Новая фотография перезапишет старую.
            </p>
          </div>
        </div>

        <form className="mt-8 border-t border-[var(--border)] pt-6" onSubmit={handleProfileSubmit} noValidate>
          <div className="grid gap-5">
            <div>
              <label className="block text-sm font-semibold text-[var(--foreground)]" htmlFor="fullName">
                ФИО
              </label>
              <input
                id="fullName"
                value={fullName}
                maxLength={255}
                onChange={(event) => setFullName(event.target.value)}
                className="mt-2 min-h-11 w-full rounded-xl border border-[var(--border)] bg-[var(--background)] px-4 text-sm text-[var(--foreground)] outline-none transition-colors focus:border-[var(--primary)]"
                placeholder="Иванов Иван Иванович"
              />
              <p className="mt-2 text-xs text-[var(--muted)]">
                Будет использоваться в будущей генерации презентаций.
              </p>
            </div>

            <div>
              <label className="block text-sm font-semibold text-[var(--foreground)]" htmlFor="username">
                Username
              </label>
              <input
                id="username"
                value={username}
                maxLength={64}
                onChange={(event) => setUsername(event.target.value)}
                aria-invalid={usernameError ? true : undefined}
                className={`mt-2 min-h-11 w-full rounded-xl border bg-[var(--background)] px-4 text-sm text-[var(--foreground)] outline-none transition-colors ${
                  usernameError
                    ? "border-[var(--danger-border)] focus:border-[var(--danger-text)] focus:ring-4 focus:ring-[color:var(--danger-bg)]"
                    : "border-[var(--border)] focus:border-[var(--primary)]"
                }`}
                placeholder="username"
              />
              {usernameError ? (
                <ErrorMessage className="mt-2 text-xs" variant="text">
                  {usernameError}
                </ErrorMessage>
              ) : (
                <p className="mt-2 text-xs text-[var(--muted)]">
                  Допустимы латинские буквы, цифры и подчёркивание.
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={!profileChanged || Boolean(usernameError) || savingProfile}
              className="w-full rounded-xl bg-[var(--primary)] px-5 py-2.5 text-sm font-semibold text-[var(--on-primary)] transition-colors hover:bg-[var(--primary-dark)] disabled:cursor-not-allowed disabled:opacity-50 sm:w-fit"
            >
              {savingProfile ? "Сохранение…" : "Сохранить профиль"}
            </button>
          </div>
        </form>

        {status?.kind === "error" ? (
          <ErrorMessage className="mt-6">{status.text}</ErrorMessage>
        ) : status ? (
          <div
            className={`mt-6 rounded-xl border px-4 py-3 text-sm ${
              status.kind === "success"
                  ? "border-[var(--success-border)] bg-[var(--success-bg)] text-[var(--success-text)]"
                  : "border-[var(--border)] bg-[var(--surface-muted)] text-[var(--foreground)]"
            }`}
          >
            {status.text}
          </div>
        ) : null}
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

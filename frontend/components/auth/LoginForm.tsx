"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AuthField } from "@/components/auth/AuthField";
import { ApiError, login } from "@/lib/api/auth";
import { POST_LOGIN_REDIRECT, ROUTES } from "@/lib/auth/constants";
import { saveTokens } from "@/lib/auth/token";

const loginSchema = z.object({
  username: z.string().trim().min(3, "Введите логин"),
  password: z.string().min(1, "Введите пароль"),
});

type LoginFormValues = z.infer<typeof loginSchema>;

const INVALID_CREDENTIALS_MESSAGE = "Логин или пароль неправильные";

export function LoginForm() {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      username: "",
      password: "",
    },
  });

  async function onSubmit(data: LoginFormValues) {
    setFormError(null);

    try {
      const tokens = await login({
        username: data.username,
        password: data.password,
      });
      saveTokens(tokens.access_token, tokens.refresh_token);
      router.push(POST_LOGIN_REDIRECT);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setFormError(INVALID_CREDENTIALS_MESSAGE);
        return;
      }
      setFormError(error instanceof ApiError ? error.message : "Не удалось выполнить вход");
    }
  }

  return (
    <form className="space-y-5" onSubmit={handleSubmit(onSubmit)} noValidate>
      <AuthField
        id="username"
        label="Логин"
        placeholder="your_login"
        autoComplete="username"
        error={errors.username?.message}
        {...register("username")}
      />
      <AuthField
        id="password"
        label="Пароль"
        type="password"
        placeholder="••••••••"
        autoComplete="current-password"
        error={errors.password?.message}
        {...register("password")}
      />

      <div className="flex items-center justify-end">
        <Link
          href={ROUTES.forgotPassword}
          className="text-sm font-medium text-[var(--primary)] hover:text-[var(--primary-dark)] transition-colors"
        >
          Забыли пароль?
        </Link>
      </div>

      {formError ? (
        <p className="rounded-lg border border-[var(--danger-border)] bg-[var(--danger-bg)] px-3 py-2 text-sm text-[var(--danger-text)]">{formError}</p>
      ) : null}

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full rounded-xl bg-gradient-to-r from-[var(--primary)] to-[var(--accent)] px-4 py-3 text-sm font-semibold text-[var(--on-primary)] shadow-lg shadow-[color:var(--primary)]/20 transition-all hover:from-[var(--primary-dark)] hover:to-[var(--primary)] hover:shadow-[color:var(--primary)]/25 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isSubmitting ? "Вход…" : "Войти"}
      </button>
    </form>
  );
}

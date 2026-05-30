import Link from "next/link";
import type { Metadata } from "next";
import { AuthField } from "@/components/auth/AuthField";
import { AuthForm } from "@/components/auth/AuthForm";
import { AuthShell } from "@/components/auth/AuthShell";

export const metadata: Metadata = {
  title: "Вход — AIDeck",
  description: "Войдите в аккаунт AIDeck",
};

export default function LoginPage() {
  return (
    <AuthShell
      title="Создавайте презентации быстрее"
      subtitle="Войдите в аккаунт и продолжите работу над своими проектами."
      footer={
        <>
          Нет аккаунта?{" "}
          <Link
            href="/register"
            className="font-medium text-[var(--primary)] hover:text-[var(--primary-dark)] transition-colors"
          >
            Зарегистрироваться
          </Link>
        </>
      }
    >
      <div className="mb-8">
        <h2 className="text-2xl font-semibold text-slate-900 tracking-tight">Вход</h2>
        <p className="mt-1 text-sm text-slate-500">Введите логин и пароль</p>
      </div>

      <AuthForm>
        <AuthField
          id="username"
          label="Логин"
          placeholder="your_login"
          autoComplete="username"
        />
        <AuthField
          id="password"
          label="Пароль"
          type="password"
          placeholder="••••••••"
          autoComplete="current-password"
        />

        <div className="flex items-center justify-end">
          <button
            type="button"
            className="text-sm font-medium text-[var(--primary)] hover:text-[var(--primary-dark)] transition-colors"
          >
            Забыли пароль?
          </button>
        </div>

        <button
          type="submit"
          className="w-full rounded-xl bg-gradient-to-r from-[var(--primary)] to-[#3b82f6] px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-500/25 transition-all hover:from-[var(--primary-dark)] hover:to-[var(--primary)] hover:shadow-blue-500/35 active:scale-[0.99]"
        >
          Войти
        </button>
      </AuthForm>
    </AuthShell>
  );
}

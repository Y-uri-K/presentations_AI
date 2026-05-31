import Link from "next/link";
import type { Metadata } from "next";
import { GuestGuard } from "@/components/auth/GuestGuard";
import { LoginForm } from "@/components/auth/LoginForm";
import { AuthShell } from "@/components/auth/AuthShell";

export const metadata: Metadata = {
  title: "Вход — AIDeck",
  description: "Войдите в аккаунт AIDeck",
};

export default function LoginPage() {
  return (
    <GuestGuard>
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

        <LoginForm />
      </AuthShell>
    </GuestGuard>
  );
}

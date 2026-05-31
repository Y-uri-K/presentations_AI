import Link from "next/link";
import type { Metadata } from "next";
import { GuestGuard } from "@/components/auth/GuestGuard";
import { RegisterForm } from "@/components/auth/RegisterForm";
import { AuthShell } from "@/components/auth/AuthShell";

export const metadata: Metadata = {
  title: "Регистрация — AIDeck",
  description: "Создайте аккаунт AIDeck",
};

export default function RegisterPage() {
  return (
    <GuestGuard>
    <AuthShell
      title="Начните уже сейчас!"
      subtitle="Создайте аккаунт: мы отправим код подтверждения на вашу почту."
      footer={
        <>
          Уже есть аккаунт?{" "}
          <Link
            href="/login"
            className="font-medium text-[var(--primary)] hover:text-[var(--primary-dark)] transition-colors"
          >
            Войти
          </Link>
        </>
      }
    >
      <div className="mb-8">
        <h2 className="text-2xl font-semibold text-slate-900 tracking-tight">Регистрация</h2>
        <p className="mt-1 text-sm text-slate-500">Заполните данные и подтвердите почту</p>
      </div>

      <RegisterForm />
    </AuthShell>
    </GuestGuard>
  );
}

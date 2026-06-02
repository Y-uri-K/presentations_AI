import Link from "next/link";
import type { Metadata } from "next";
import { ForgotPasswordForm } from "@/components/auth/ForgotPasswordForm";
import { GuestGuard } from "@/components/auth/GuestGuard";
import { AuthShell } from "@/components/auth/AuthShell";
import { ROUTES } from "@/lib/auth/constants";

export const metadata: Metadata = {
  title: "Восстановление пароля — AIDeck",
  description: "Сброс пароля AIDeck",
};

export default function ForgotPasswordPage() {
  return (
    <GuestGuard>
      <AuthShell
        title="Восстановление доступа"
        subtitle="Укажите почту, подтвердите код из письма и задайте новый пароль."
        footer={
          <>
            Вспомнили пароль?{" "}
            <Link
              href={ROUTES.login}
              className="font-medium text-[var(--primary)] hover:text-[var(--primary-dark)] transition-colors"
            >
              Войти
            </Link>
          </>
        }
      >
        <div className="mb-8">
          <h2 className="text-2xl font-semibold tracking-tight text-[var(--foreground)]">Сброс пароля</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">Только для зарегистрированной почты</p>
        </div>

        <ForgotPasswordForm />
      </AuthShell>
    </GuestGuard>
  );
}

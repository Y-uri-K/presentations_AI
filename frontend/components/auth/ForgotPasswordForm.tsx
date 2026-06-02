"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { AuthField } from "@/components/auth/AuthField";
import {
  ApiError,
  confirmPasswordReset,
  requestPasswordResetCode,
  resendPasswordResetCode,
} from "@/lib/api/auth";
import { ROUTES } from "@/lib/auth/constants";
import { useEmailSendCooldown } from "@/lib/hooks/useEmailSendCooldown";
import {
  passwordResetCompleteSchema,
  passwordResetEmailSchema,
  type PasswordResetFormValues,
} from "@/lib/validation/passwordResetSchema";

export function ForgotPasswordForm() {
  const router = useRouter();
  const [codeSent, setCodeSent] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSendingCode, setIsSendingCode] = useState(false);
  const { isOnCooldown, cooldownSeconds, applyRateLimitError } = useEmailSendCooldown();

  const {
    register,
    handleSubmit,
    getValues,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<PasswordResetFormValues>({
    resolver: zodResolver(passwordResetCompleteSchema),
    mode: "onBlur",
    reValidateMode: "onChange",
    defaultValues: {
      email: "",
      verification_code: "",
      password: "",
      password_confirm: "",
    },
  });

  async function handleSendCode() {
    setFormError(null);
    setStatusMessage(null);
    setIsSendingCode(true);

    const values = getValues();
    const parsed = passwordResetEmailSchema.safeParse({ email: values.email });

    if (!parsed.success) {
      parsed.error.issues.forEach((issue) => {
        if (issue.path[0] === "email") {
          setError("email", { message: issue.message });
        }
      });
      setIsSendingCode(false);
      return;
    }

    try {
      const sendCode = codeSent ? resendPasswordResetCode : requestPasswordResetCode;
      const response = await sendCode(parsed.data.email);
      setCodeSent(true);
      setStatusMessage(response.message);
    } catch (error) {
      const rateLimitMessage = applyRateLimitError(error);
      setFormError(
        rateLimitMessage ?? (error instanceof ApiError ? error.message : "Не удалось отправить код"),
      );
    } finally {
      setIsSendingCode(false);
    }
  }

  async function onSubmit(data: PasswordResetFormValues) {
    setFormError(null);
    setStatusMessage(null);

    if (!codeSent) {
      setFormError("Сначала получите код подтверждения на почту");
      return;
    }

    try {
      const response = await confirmPasswordReset({
        email: data.email,
        code: data.verification_code,
        password: data.password,
        password_confirm: data.password_confirm,
      });
      setStatusMessage(response.message);
      router.push(ROUTES.login);
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "Не удалось сменить пароль");
    }
  }

  return (
    <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
      <AuthField
        id="email"
        label="Почта"
        type="email"
        placeholder="you@example.com"
        autoComplete="email"
        error={errors.email?.message}
        {...register("email")}
      />

      <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] px-4 py-3">
        <AuthField
          id="verification_code"
          label="Код из письма"
          placeholder="000000"
          autoComplete="one-time-code"
          hint={
            errors.verification_code
              ? undefined
              : codeSent
                ? "Код отправлен. Проверьте почту или запросите повторно"
                : "Нажмите «Получить код», затем введите 6 цифр из письма"
          }
          error={errors.verification_code?.message}
          disabled={!codeSent}
          {...register("verification_code")}
        />
      </div>

      <AuthField
        id="password"
        label="Новый пароль"
        type="password"
        placeholder="не менее 8 символов, буква и цифра"
        autoComplete="new-password"
        error={errors.password?.message}
        disabled={!codeSent}
        {...register("password")}
      />
      <AuthField
        id="password_confirm"
        label="Подтверждение пароля"
        type="password"
        placeholder="повторите пароль"
        autoComplete="new-password"
        error={errors.password_confirm?.message}
        disabled={!codeSent}
        {...register("password_confirm")}
      />

      {statusMessage ? (
        <p className="rounded-lg border border-[var(--success-border)] bg-[var(--success-bg)] px-3 py-2 text-sm text-[var(--success-text)]">{statusMessage}</p>
      ) : null}
      {formError ? (
        <p className="rounded-lg border border-[var(--danger-border)] bg-[var(--danger-bg)] px-3 py-2 text-sm text-[var(--danger-text)]">{formError}</p>
      ) : null}

      <button
        type="button"
        onClick={handleSendCode}
        disabled={isSendingCode || isSubmitting || isOnCooldown}
        className="w-full rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm font-semibold text-[var(--primary)] transition-colors hover:bg-[var(--surface-muted)] disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isOnCooldown
          ? `Повторная отправка через ${cooldownSeconds} сек.`
          : isSendingCode
            ? "Отправка…"
            : codeSent
              ? "Отправить код снова"
              : "Получить код на почту"}
      </button>

      <button
        type="submit"
        disabled={isSubmitting || !codeSent}
        className="w-full rounded-xl bg-gradient-to-r from-[var(--primary)] to-[var(--accent)] px-4 py-3 text-sm font-semibold text-[var(--on-primary)] shadow-lg shadow-[color:var(--primary)]/20 transition-all hover:from-[var(--primary-dark)] hover:to-[var(--primary)] hover:shadow-[color:var(--primary)]/25 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isSubmitting ? "Сохранение…" : "Сменить пароль"}
      </button>

      <p className="text-center text-sm text-[var(--muted)]">
        <Link
          href={ROUTES.login}
          className="font-medium text-[var(--primary)] hover:text-[var(--primary-dark)] transition-colors"
        >
          Вернуться ко входу
        </Link>
      </p>
    </form>
  );
}

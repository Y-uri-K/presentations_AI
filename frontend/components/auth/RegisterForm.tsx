"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { AuthField } from "@/components/auth/AuthField";
import {
  ApiError,
  requestRegistrationCode,
  resendRegistrationCode,
  verifyRegistration,
} from "@/lib/api/auth";
import { POST_LOGIN_REDIRECT } from "@/lib/auth/constants";
import { saveTokens } from "@/lib/auth/token";
import { useEmailSendCooldown } from "@/lib/hooks/useEmailSendCooldown";
import {
  registerCompleteSchema,
  registerRequestSchema,
  type RegisterFormValues,
} from "@/lib/validation/registerSchema";

export function RegisterForm() {
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
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerCompleteSchema),
    mode: "onBlur",
    reValidateMode: "onChange",
    defaultValues: {
      username: "",
      email: "",
      password: "",
      password_confirm: "",
      verification_code: "",
      agreement: false,
    },
  });

  async function handleSendCode() {
    setFormError(null);
    setStatusMessage(null);
    setIsSendingCode(true);

    const values = getValues();
    const parsed = await registerRequestSchema.safeParseAsync({
      username: values.username,
      email: values.email,
      password: values.password,
      password_confirm: values.password_confirm,
      agreement: values.agreement,
    });

    if (!parsed.success) {
      parsed.error.issues.forEach((issue) => {
        const field = issue.path[0];
        if (field && typeof field === "string") {
          setError(field as keyof RegisterFormValues, { message: issue.message });
        }
      });
      setIsSendingCode(false);
      return;
    }

    try {
      const response = codeSent
        ? await resendRegistrationCode(parsed.data.email)
        : await requestRegistrationCode(parsed.data);
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

  async function onSubmit(data: RegisterFormValues) {
    setFormError(null);
    setStatusMessage(null);

    if (!codeSent) {
      setFormError("Сначала получите код подтверждения на почту");
      return;
    }

    try {
      const tokenResponse = await verifyRegistration({
        email: data.email,
        code: data.verification_code,
      });
      saveTokens(tokenResponse.access_token, tokenResponse.refresh_token);
      router.push(POST_LOGIN_REDIRECT);
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "Не удалось завершить регистрацию");
    }
  }

  return (
    <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
      <AuthField
        id="username"
        label="Логин"
        placeholder="придумайте логин"
        autoComplete="username"
        error={errors.username?.message}
        {...register("username")}
      />
      <AuthField
        id="email"
        label="Почта"
        type="email"
        placeholder="you@example.com"
        autoComplete="email"
        error={errors.email?.message}
        {...register("email")}
      />
      <AuthField
        id="password"
        label="Пароль"
        type="password"
        placeholder="не менее 8 символов, буква и цифра"
        autoComplete="new-password"
        error={errors.password?.message}
        {...register("password")}
      />
      <AuthField
        id="password_confirm"
        label="Подтверждение пароля"
        type="password"
        placeholder="повторите пароль"
        autoComplete="new-password"
        error={errors.password_confirm?.message}
        {...register("password_confirm")}
      />

      <div className="rounded-xl border border-sky-100 bg-sky-50/80 px-4 py-3">
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

      <label className="flex items-start gap-3 cursor-pointer group">
        <input
          type="checkbox"
          className="mt-1 h-4 w-4 rounded border-slate-300 text-[var(--primary)] focus:ring-sky-200"
          {...register("agreement")}
        />
        <span className="text-sm text-slate-600 leading-snug group-hover:text-slate-800 transition-colors">
          Я согласен с{" "}
          <span className="text-[var(--primary)] font-medium">условиями использования</span> и{" "}
          <span className="text-[var(--primary)] font-medium">политикой конфиденциальности</span>
        </span>
      </label>
      {errors.agreement ? <p className="text-xs text-red-600 -mt-2">{errors.agreement.message}</p> : null}

      {statusMessage ? (
        <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{statusMessage}</p>
      ) : null}
      {formError ? (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{formError}</p>
      ) : null}

      <button
        type="button"
        onClick={handleSendCode}
        disabled={isSendingCode || isSubmitting || isOnCooldown}
        className="w-full rounded-xl border border-sky-200 bg-white px-4 py-3 text-sm font-semibold text-[var(--primary)] transition-colors hover:bg-sky-50 disabled:cursor-not-allowed disabled:opacity-60"
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
        className="w-full rounded-xl bg-gradient-to-r from-[var(--primary)] to-[#3b82f6] px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-500/25 transition-all hover:from-[var(--primary-dark)] hover:to-[var(--primary)] hover:shadow-blue-500/35 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isSubmitting ? "Регистрация…" : "Зарегистрироваться"}
      </button>
    </form>
  );
}

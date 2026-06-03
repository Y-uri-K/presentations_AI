"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm, type FieldErrors } from "react-hook-form";

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

function isPasswordInvalid(value: string) {
  return value.length < 8 || !/[A-Za-zА-Яа-я]/.test(value) || !/\d/.test(value);
}

export function RegisterForm() {
  const router = useRouter();
  const [codeSent, setCodeSent] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSendingCode, setIsSendingCode] = useState(false);
  const [shakePassword, setShakePassword] = useState(false);
  const [shakePasswordConfirm, setShakePasswordConfirm] = useState(false);
  const { isOnCooldown, cooldownSeconds, applyRateLimitError } = useEmailSendCooldown();

  const {
    register,
    handleSubmit,
    getValues,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerCompleteSchema),
    mode: "onChange",
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

  function triggerShake(target: "password" | "password_confirm") {
    const setter = target === "password" ? setShakePassword : setShakePasswordConfirm;
    setter(false);
    window.requestAnimationFrame(() => {
      setter(true);
      window.setTimeout(() => setter(false), 420);
    });
  }

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
        if (field === "password" || field === "password_confirm") {
          triggerShake(field);
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

  function onInvalid(errors: FieldErrors<RegisterFormValues>) {
    if (errors.password) {
      triggerShake("password");
    }
    if (errors.password_confirm) {
      triggerShake("password_confirm");
    }
  }

  const passwordRegistration = register("password");
  const passwordConfirmRegistration = register("password_confirm");

  return (
    <form className="space-y-4" onSubmit={handleSubmit(onSubmit, onInvalid)} noValidate>
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
        shake={shakePassword}
        {...passwordRegistration}
        onBlur={(event) => {
          void passwordRegistration.onBlur(event);
          if (isPasswordInvalid(event.target.value)) {
            triggerShake("password");
          }
        }}
      />
      <AuthField
        id="password_confirm"
        label="Подтверждение пароля"
        type="password"
        placeholder="повторите пароль"
        autoComplete="new-password"
        error={errors.password_confirm?.message}
        shake={shakePasswordConfirm}
        {...passwordConfirmRegistration}
        onBlur={(event) => {
          void passwordConfirmRegistration.onBlur(event);
          const password = getValues("password");
          if (!event.target.value || event.target.value !== password) {
            triggerShake("password_confirm");
          }
        }}
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

      <label className="flex items-start gap-3 cursor-pointer group">
        <input
          type="checkbox"
          className="mt-1 h-4 w-4 rounded border-[var(--border)] text-[var(--primary)] focus:ring-[color:var(--focus-ring)]"
          {...register("agreement")}
        />
        <span className="text-sm leading-snug text-[var(--muted)] transition-colors group-hover:text-[var(--foreground)]">
          Я согласен с{" "}
          <span className="text-[var(--primary)] font-medium">условиями использования</span> и{" "}
          <span className="text-[var(--primary)] font-medium">политикой конфиденциальности</span>
        </span>
      </label>
      {errors.agreement ? <p className="text-xs text-red-600 -mt-2">{errors.agreement.message}</p> : null}

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
        {isSubmitting ? "Регистрация…" : "Зарегистрироваться"}
      </button>
    </form>
  );
}

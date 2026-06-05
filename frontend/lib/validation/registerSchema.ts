import { z } from "zod";

import { checkEmailAvailable, checkUsernameAvailable } from "@/lib/api/auth";

const usernameField = z
  .string()
  .trim()
  .min(3, "Логин — не менее 3 символов")
  .max(64, "Логин — не более 64 символов")
  .regex(/^[a-zA-Z0-9_]+$/, "Только латиница, цифры и подчёркивание");

const emailField = z.string().trim().email("Некорректный адрес почты");

const passwordField = z
  .string()
  .min(8, "Пароль — не менее 8 символов")
  .regex(/[A-Za-zА-Яа-я]/, "Пароль должен содержать букву")
  .regex(/\d/, "Пароль должен содержать цифру");

async function validateAvailability(data: { username: string; email: string }, ctx: z.RefinementCtx) {
  if (data.username.length >= 3 && /^[a-zA-Z0-9_]+$/.test(data.username)) {
    try {
      const available = await checkUsernameAvailable(data.username);
      if (!available) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Этот логин уже занят",
          path: ["username"],
        });
      }
    } catch {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Не удалось проверить логин. Попробуйте позже",
        path: ["username"],
      });
    }
  }

  const emailResult = z.string().email().safeParse(data.email);
  if (emailResult.success) {
    try {
      const available = await checkEmailAvailable(data.email);
      if (!available) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Эта почта уже зарегистрирована",
          path: ["email"],
        });
      }
    } catch {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Не удалось проверить почту. Попробуйте позже",
        path: ["email"],
      });
    }
  }
}

export const registerRequestSchema = z
  .object({
    username: usernameField,
    email: emailField,
    password: passwordField,
    password_confirm: z.string().min(1, "Подтвердите пароль"),
  })
  .refine((data) => data.password === data.password_confirm, {
    message: "Пароли не совпадают",
    path: ["password_confirm"],
  })
  .superRefine(async (data, ctx) => {
    await validateAvailability(data, ctx);
  });

export const registerCompleteSchema = registerRequestSchema
  .extend({
    verification_code: z
      .string()
      .trim()
      .min(1, "Введите код из письма")
      .regex(/^\d{6}$/, "Код — 6 цифр"),
  });

export type RegisterFormValues = z.infer<typeof registerCompleteSchema>;

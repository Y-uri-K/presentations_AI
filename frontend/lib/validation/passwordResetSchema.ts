import { z } from "zod";

const emailField = z.string().trim().email("Некорректный адрес почты");

const passwordField = z
  .string()
  .min(8, "Пароль — не менее 8 символов")
  .regex(/[A-Za-z]/, "Пароль должен содержать латинскую букву")
  .regex(/\d/, "Пароль должен содержать цифру");

export const passwordResetEmailSchema = z.object({
  email: emailField,
});

export const passwordResetCompleteSchema = z
  .object({
    email: emailField,
    verification_code: z
      .string()
      .trim()
      .min(1, "Введите код из письма")
      .regex(/^\d{6}$/, "Код — 6 цифр"),
    password: passwordField,
    password_confirm: z.string().min(1, "Подтвердите пароль"),
  })
  .refine((data) => data.password === data.password_confirm, {
    message: "Пароли не совпадают",
    path: ["password_confirm"],
  });

export type PasswordResetFormValues = z.infer<typeof passwordResetCompleteSchema>;

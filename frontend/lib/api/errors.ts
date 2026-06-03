import { ApiError } from "@/lib/api/auth";

export function isPresentationNotFoundError(error: unknown) {
  return (
    error instanceof ApiError &&
    error.status === 404 &&
    error.message.trim().toLowerCase() === "презентация не найдена"
  );
}

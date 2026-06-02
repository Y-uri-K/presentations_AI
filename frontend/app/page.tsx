import Link from "next/link";
import { Logo } from "@/components/Logo";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-[var(--accent-light)] to-[var(--background)] px-6">
      <div className="text-center max-w-lg">
        <Link href="/" className="inline-block mx-auto mb-8">
          <Logo className="h-32 sm:h-40 w-auto max-w-[560px]" />
        </Link>
        <p className="text-[var(--muted)]">Генерация презентаций с помощью искусственного интеллекта</p>
        <div className="mt-10 flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            href="/login"
            className="inline-flex items-center justify-center rounded-xl bg-[var(--primary)] px-6 py-3 text-sm font-semibold text-[var(--on-primary)] shadow-md shadow-[color:var(--primary)]/20 transition-colors hover:bg-[var(--primary-dark)]"
          >
            Войти
          </Link>
          <Link
            href="/register"
            className="inline-flex items-center justify-center rounded-xl border border-[var(--border)] bg-[var(--surface)] px-6 py-3 text-sm font-semibold text-[var(--primary)] transition-colors hover:border-[var(--primary)] hover:bg-[var(--surface-muted)]"
          >
            Регистрация
          </Link>
        </div>
      </div>
    </div>
  );
}

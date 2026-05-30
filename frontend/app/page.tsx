import Link from "next/link";
import { Logo } from "@/components/Logo";

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6 bg-gradient-to-b from-sky-50 to-white">
      <div className="text-center max-w-lg">
        <Link href="/" className="inline-block mx-auto mb-8">
          <Logo className="h-32 sm:h-40 w-auto max-w-[560px]" />
        </Link>
        <p className="text-slate-600">Генерация презентаций с помощью искусственного интеллекта</p>
        <div className="mt-10 flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            href="/login"
            className="inline-flex items-center justify-center rounded-xl bg-[var(--primary)] px-6 py-3 text-sm font-semibold text-white shadow-md shadow-blue-500/20 hover:bg-[var(--primary-dark)] transition-colors"
          >
            Войти
          </Link>
          <Link
            href="/register"
            className="inline-flex items-center justify-center rounded-xl border border-sky-200 bg-white px-6 py-3 text-sm font-semibold text-[var(--primary)] hover:bg-sky-50 transition-colors"
          >
            Регистрация
          </Link>
        </div>
      </div>
    </div>
  );
}

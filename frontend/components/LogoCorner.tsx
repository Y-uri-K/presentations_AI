import Link from "next/link";
import { Logo } from "@/components/Logo";

type LogoCornerProps = {
  className?: string;
  onDark?: boolean;
};

export function LogoCorner({
  className = "h-14 sm:h-16 w-auto max-w-[200px] sm:max-w-[240px]",
  onDark = false,
}: LogoCornerProps) {
  return (
    <Link
      href="/"
      className="fixed bottom-6 right-6 z-20 transition-opacity hover:opacity-90"
      aria-label="На главную"
    >
      <Logo onDark={onDark} className={className} />
    </Link>
  );
}

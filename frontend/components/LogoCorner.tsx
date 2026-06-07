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
      className="fixed bottom-4 right-4 z-20 hidden transition-opacity hover:opacity-90 sm:bottom-6 sm:right-6 sm:block"
      style={{
        paddingBottom: "env(safe-area-inset-bottom, 0px)",
        paddingRight: "env(safe-area-inset-right, 0px)",
      }}
      aria-label="На главную"
    >
      <Logo onDark={onDark} className={className} />
    </Link>
  );
}

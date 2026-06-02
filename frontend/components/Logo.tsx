import Image from "next/image";
import logoSrc from "@/src/logo_DeckAI.svg";

type LogoProps = {
  className?: string;
  onDark?: boolean;
};

export function Logo({ className = "h-[5.5rem] w-auto max-w-[360px]", onDark = false }: LogoProps) {
  const src = typeof logoSrc === "string" ? logoSrc : logoSrc.src;

  const image = (
    <Image
      src={src}
      alt="AIDeck"
      width={560}
      height={180}
      unoptimized
      className={className}
      priority
    />
  );

  if (onDark) {
    return (
      <span className="inline-flex rounded-2xl bg-[var(--surface)] px-8 py-5 shadow-lg shadow-[color:var(--primary)]/20 ring-1 ring-[var(--border)]">
        {image}
      </span>
    );
  }

  return image;
}

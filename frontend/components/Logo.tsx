import logoSrc from "@/src/logo_DeckAI.svg";

type LogoProps = {
  className?: string;
  onDark?: boolean;
};

export function Logo({ className = "h-[5.5rem] w-auto max-w-[360px]", onDark = false }: LogoProps) {
  const src = typeof logoSrc === "string" ? logoSrc : logoSrc.src;

  const image = (
    <img src={src} alt="AIDeck" className={className} />
  );

  if (onDark) {
    return (
      <span className="inline-flex rounded-2xl bg-white px-8 py-5 shadow-lg shadow-blue-950/20">
        {image}
      </span>
    );
  }

  return image;
}

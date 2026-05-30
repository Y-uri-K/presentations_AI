import logoSrc from "@/src/logo_DeckAI.svg";

type LogoProps = {
  className?: string;
  /** На тёмном/синем фоне — логотип на белой подложке */
  onDark?: boolean;
};

export function Logo({ className = "h-[5.5rem] w-auto max-w-[360px]", onDark = false }: LogoProps) {
  const src = typeof logoSrc === "string" ? logoSrc : logoSrc.src;

  const image = (
    // eslint-disable-next-line @next/next/no-img-element
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

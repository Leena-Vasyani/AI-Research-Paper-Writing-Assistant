import Link from "next/link";

type ProjectLogoVariant = "compact" | "full" | "hero";

export default function ProjectLogo({
  variant = "full",
  className = "",
  showTagline = false,
}: {
  variant?: ProjectLogoVariant;
  className?: string;
  showTagline?: boolean;
}) {
  const svgSize = variant === "hero" ? 56 : variant === "compact" ? 34 : 42;
  const titleSize =
    variant === "hero"
      ? "text-2xl md:text-3xl"
      : variant === "compact"
        ? "text-sm"
        : "text-lg";

  return (
    <Link
      href="/"
      aria-label="Go to ResearchGen home"
      className={`rg-logo group inline-flex items-center gap-2 rounded-xl px-1 py-1 outline-none transition hover:bg-zinc-800/30 focus-visible:ring-2 focus-visible:ring-indigo-300/70 ${className}`}
    >
      <svg
        width={svgSize}
        height={svgSize}
        viewBox="0 0 64 64"
        role="img"
        aria-hidden="true"
        className="shrink-0"
      >
        <title>ResearchGen logo mark</title>

        <rect
          x="14"
          y="10"
          width="36"
          height="44"
          rx="9"
          className="rg-logo-doc"
        />

        <path d="M22 22h20" className="rg-logo-line" />
        <path d="M22 29h16" className="rg-logo-line" />
        <path d="M22 36h18" className="rg-logo-line" />

        <path
          d="M8 31c3-5 3-11 0-16"
          className="rg-logo-spark rg-logo-spark-left"
        />
        <path
          d="M56 31c-3-5-3-11 0-16"
          className="rg-logo-spark rg-logo-spark-right"
        />

        <circle
          cx="32"
          cy="45"
          r="2.7"
          className="rg-logo-node rg-logo-node-a"
        />
        <circle cx="26" cy="49" r="2" className="rg-logo-node rg-logo-node-b" />
        <circle cx="38" cy="49" r="2" className="rg-logo-node rg-logo-node-c" />
      </svg>

      {variant !== "compact" && (
        <span className="flex flex-col leading-tight">
          <span
            className={`${titleSize} font-semibold tracking-tight text-zinc-100`}
          >
            ResearchGen
          </span>
          {showTagline && (
            <span className="text-[11px] text-zinc-400">
              Multi-agent research studio
            </span>
          )}
        </span>
      )}
    </Link>
  );
}

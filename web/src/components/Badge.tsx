import type { ReactNode } from "react";

export default function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "success" | "warning" | "danger" | "info";
}) {
  const toneClass = {
    neutral: "border-zinc-700/70 bg-zinc-800/50 text-zinc-200",
    success: "border-emerald-400/40 bg-emerald-500/15 text-emerald-200",
    warning: "border-amber-400/40 bg-amber-500/15 text-amber-200",
    danger: "border-rose-400/40 bg-rose-500/15 text-rose-200",
    info: "border-indigo-400/40 bg-indigo-500/15 text-indigo-200",
  }[tone];

  return (
    <span
      className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium backdrop-blur-sm ${toneClass}`}
    >
      {children}
    </span>
  );
}

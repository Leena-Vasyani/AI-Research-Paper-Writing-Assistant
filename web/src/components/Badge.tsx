import type { ReactNode } from "react";

export default function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "success" | "warning" | "danger" | "info";
}) {
  const toneClass = {
    neutral: "bg-zinc-800 text-zinc-200",
    success: "bg-emerald-500/20 text-emerald-300",
    warning: "bg-amber-500/20 text-amber-300",
    danger: "bg-rose-500/20 text-rose-300",
    info: "bg-indigo-500/20 text-indigo-300",
  }[tone];

  return (
    <span className={`rounded-full px-3 py-1 text-xs ${toneClass}`}>
      {children}
    </span>
  );
}

import type { ReactNode } from "react";

export default function PageHeader({
  title,
  subtitle,
  actions,
  eyebrow,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  eyebrow?: string;
}) {
  return (
    <header className="relative overflow-hidden rounded-2xl border border-zinc-800/80 bg-zinc-900/60 px-5 py-4 shadow-[0_14px_35px_rgba(0,0,0,0.35)] backdrop-blur-xl md:px-6 md:py-5">
      <div className="pointer-events-none absolute -right-14 -top-12 h-28 w-28 rounded-full bg-indigo-500/12 blur-3xl" />
      <div className="relative flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="space-y-1">
          {eyebrow && (
            <div className="text-[11px] uppercase tracking-[0.2em] text-indigo-300/90">
              {eyebrow}
            </div>
          )}
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-100 md:text-3xl">
            {title}
          </h1>
          {subtitle && (
            <p className="max-w-3xl text-sm leading-relaxed text-zinc-400">
              {subtitle}
            </p>
          )}
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
    </header>
  );
}

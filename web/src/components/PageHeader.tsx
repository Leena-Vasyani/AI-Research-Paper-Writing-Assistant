import type { ReactNode } from "react";

export default function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-col gap-2 rounded-xl bg-zinc-900/70 px-4 py-3 shadow md:flex-row md:items-center md:justify-between">
      <div>
        <h1 className="text-xl font-semibold md:text-2xl">{title}</h1>
        {subtitle && <p className="text-xs text-zinc-400">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </header>
  );
}

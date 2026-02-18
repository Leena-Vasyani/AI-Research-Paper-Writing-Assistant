import type { ReactNode } from "react";

export default function SectionCard({
  title,
  description,
  children,
  actions,
  footer,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  actions?: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <section className="group relative overflow-hidden rounded-[2rem] bg-zinc-900/45 p-6 shadow-[0_16px_35px_rgba(0,0,0,0.35)] ring-1 ring-zinc-800/60 backdrop-blur-xl transition duration-300 hover:-translate-y-0.5 hover:ring-indigo-300/25">
      <div className="pointer-events-none absolute -right-20 -top-16 h-44 w-44 rounded-full bg-indigo-500/12 blur-3xl" />
      <div className="pointer-events-none absolute -left-16 bottom-0 h-28 w-28 rounded-full bg-fuchsia-500/10 blur-3xl" />
      <div className="relative flex items-start justify-between gap-3">
        <div className="space-y-1">
          <h2 className="text-base font-semibold tracking-tight text-zinc-100">
            {title}
          </h2>
          {description && (
            <p className="text-xs leading-relaxed text-zinc-400">
              {description}
            </p>
          )}
        </div>
        {actions}
      </div>
      <div className="relative mt-4 overflow-x-hidden text-zinc-200">
        {children}
      </div>
      {footer && (
        <div className="relative mt-4 border-t border-zinc-800/70 pt-4">
          {footer}
        </div>
      )}
    </section>
  );
}

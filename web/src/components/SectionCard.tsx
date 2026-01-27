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
    <section className="rounded-xl bg-zinc-900 p-4 shadow overflow-hidden">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">{title}</h2>
          {description && (
            <p className="text-xs text-zinc-400">{description}</p>
          )}
        </div>
        {actions}
      </div>
      <div className="mt-3 overflow-x-hidden">{children}</div>
      {footer && (
        <div className="mt-4 border-t border-zinc-800 pt-4">{footer}</div>
      )}
    </section>
  );
}

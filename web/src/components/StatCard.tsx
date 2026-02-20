export default function StatCard({
  label,
  value,
  caption,
}: {
  label: string;
  value: string | number;
  caption?: string;
}) {
  return (
    <div className="relative overflow-hidden rounded-[1.75rem] bg-zinc-900/50 p-5 shadow-[0_12px_28px_rgba(0,0,0,0.35)] ring-1 ring-zinc-800/60 backdrop-blur-xl transition duration-300 hover:ring-indigo-300/20">
      <div className="pointer-events-none absolute -right-10 -top-10 h-24 w-24 rounded-full bg-indigo-500/15 blur-2xl" />
      <div className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">
        {label}
      </div>
      <div className="mt-2 text-3xl font-semibold tracking-tight text-zinc-100">
        {value}
      </div>
      {caption && <div className="mt-1 text-xs text-zinc-400">{caption}</div>}
    </div>
  );
}

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
    <div className="rounded-2xl bg-zinc-900 p-5 shadow">
      <div className="text-xs uppercase text-zinc-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold">{value}</div>
      {caption && <div className="text-xs text-zinc-400">{caption}</div>}
    </div>
  );
}

import PageHeader from "@/components/PageHeader";
import SectionCard from "@/components/SectionCard";

const team = [
  { name: "Namit Gandhi", role: "AI and backend " },
  { name: "Leena Vasyani", role: "AI, backend and UX" },
  { name: "Varun Vishe", role: "Frontend Engineer" },
  { name: "Abhishek Goud", role: "AI and Backend Engineer" },
];

export default function AboutPage() {
  return (
    <div className="space-y-8 px-2 pb-2 md:px-4">
      <PageHeader
        eyebrow="About"
        title="About ResearchGen"
        subtitle="Why we built it, what values guide it, and who is driving the platform forward."
      />

      <section className="grid gap-6 lg:grid-cols-2">
        <SectionCard
          title="Our mission"
          description="Accelerate research workflows without sacrificing academic rigor."
        >
          <p className="text-sm text-zinc-300">
            ResearchGen exists to reduce the cognitive load of literature
            synthesis. We built a multi-agent workflow so every step is
            traceable, grounded, and export-ready.
          </p>
        </SectionCard>
        <SectionCard
          title="Why it matters"
          description="Researchers need clarity, traceability, and faster execution."
        >
          <p className="text-sm text-zinc-300">
            Paper writing should focus on insight, not repetitive formatting.
            ResearchGen automates the heavy lifting so you can concentrate on
            analysis and original contributions.
          </p>
        </SectionCard>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold tracking-tight">The team</h2>
        <div className="rounded-[2rem] bg-zinc-900/35 p-3 ring-1 ring-zinc-800/70 backdrop-blur-xl">
          {team.map((member) => (
            <div
              key={member.name}
              className="flex items-center gap-4 rounded-2xl px-3 py-3 transition hover:bg-zinc-800/40"
            >
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-indigo-500/20 text-sm font-semibold text-indigo-100 ring-1 ring-indigo-300/25">
                {member.name
                  .split(" ")
                  .map((part) => part[0])
                  .join("")}
              </div>
              <div>
                <div className="text-sm font-semibold tracking-tight text-zinc-100">
                  {member.name}
                </div>
                <div className="text-xs text-zinc-400">{member.role}</div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

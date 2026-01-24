import PageHeader from "@/components/PageHeader";
import SectionCard from "@/components/SectionCard";

const team = [
  { name: "Aarav Mehta", role: "AI Research Lead" },
  { name: "Leena Vasyani", role: "Product & UX" },
  { name: "Sana Qureshi", role: "Frontend Engineer" },
  { name: "Karan Patel", role: "Backend Engineer" },
];

export default function AboutPage() {
  return (
    <div className="space-y-8 px-2 md:px-4">
      <PageHeader
        title="About ResearchGen"
        subtitle="Why we built it and who maintains it."
      />

      <section className="grid gap-6 lg:grid-cols-2">
        <SectionCard
          title="Our mission"
          description="Accelerate research without losing rigor."
        >
          <p className="text-sm text-zinc-300">
            ResearchGen exists to reduce the cognitive load of literature
            synthesis. We built a multi-agent workflow so every step is
            traceable, grounded, and export-ready.
          </p>
        </SectionCard>
        <SectionCard
          title="Why it matters"
          description="Students and researchers deserve better tools."
        >
          <p className="text-sm text-zinc-300">
            Paper writing should focus on insight, not repetitive formatting.
            ResearchGen automates the heavy lifting so you can concentrate on
            analysis and original contributions.
          </p>
        </SectionCard>
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold">The team</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {team.map((member) => (
            <div
              key={member.name}
              className="rounded-2xl bg-zinc-900 p-5 text-center shadow"
            >
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-indigo-500/30 text-lg font-semibold">
                {member.name
                  .split(" ")
                  .map((part) => part[0])
                  .join("")}
              </div>
              <div className="mt-3 text-sm font-semibold">{member.name}</div>
              <div className="text-xs text-zinc-400">{member.role}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

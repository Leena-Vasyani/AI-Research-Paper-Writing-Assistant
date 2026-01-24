import Link from "next/link";
import Badge from "@/components/Badge";
import PageHeader from "@/components/PageHeader";
import SectionCard from "@/components/SectionCard";
import StatCard from "@/components/StatCard";

export default function Home() {
  return (
    <div className="space-y-8 px-2 md:px-4">
      <PageHeader
        title="ResearchGen"
        subtitle="A multi-agent research assistant that turns topics into draft-ready papers."
        actions={
          <Link
            href="/workflow"
            className="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-400"
          >
            Start workflow
          </Link>
        }
      />

      <section className="grid gap-6 lg:grid-cols-3">
        <StatCard
          label="Agents"
          value={5}
          caption="Query → Retrieval → Summary → Draft → Plagiarism"
        />
        <StatCard label="Tools" value={1} caption="Smart Drafter workspace" />
        <StatCard
          label="Outputs"
          value="3+"
          caption="Summary, draft, plagiarism report"
        />
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <SectionCard
          title="How it works"
          description="Each agent unlocks the next step, so your workflow stays focused."
          actions={<Badge tone="info">Structured</Badge>}
          footer={
            <Link
              href="/how-it-works"
              className="text-sm text-indigo-300 hover:underline"
            >
              Learn how the agents collaborate →
            </Link>
          }
        >
          <ol className="space-y-3 text-sm text-zinc-300">
            <li>1. Topic agent extracts precise keywords and scope.</li>
            <li>2. Retrieval agent pulls high-relevance arXiv papers.</li>
            <li>3. Summarization agent produces grounded synthesis.</li>
            <li>4. Drafting agent turns insights into academic sections.</li>
            <li>5. Plagiarism agent verifies originality and flags risks.</li>
          </ol>
        </SectionCard>

        <SectionCard
          title="Why ResearchGen exists"
          description="Students and researchers waste time stitching sources by hand."
          actions={<Badge tone="success">Time saver</Badge>}
          footer={
            <Link
              href="/about"
              className="text-sm text-indigo-300 hover:underline"
            >
              Meet the team behind the system →
            </Link>
          }
        >
          <p className="text-sm text-zinc-300">
            ResearchGen accelerates literature synthesis without sacrificing
            rigor. It keeps sources transparent, structures every step, and
            delivers export-ready drafts you can refine with confidence.
          </p>
        </SectionCard>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <SectionCard
          title="Smart Drafter"
          description="A block-based writing space built for research papers."
          actions={<Badge tone="info">New Tool</Badge>}
          footer={
            <Link
              href="/how-it-works"
              className="text-sm text-indigo-300 hover:underline"
            >
              See Smart Drafter details →
            </Link>
          }
        >
          <ul className="space-y-2 text-sm text-zinc-300">
            <li>• Drag-and-drop sections like a Notion-style editor.</li>
            <li>• Expand rough notes into academic paragraphs.</li>
            <li>• Clickable citations with context previews.</li>
            <li>• Export to LaTeX or Word instantly.</li>
          </ul>
        </SectionCard>
        <SectionCard
          title="Quality constraints"
          description="Real-time checks keep writing within academic limits."
          actions={<Badge tone="success">Guardrails</Badge>}
        >
          <ul className="space-y-2 text-sm text-zinc-300">
            <li>• Abstract word limit checks.</li>
            <li>• Passive voice warnings.</li>
            <li>• Section completeness status.</li>
          </ul>
        </SectionCard>
      </section>

      <section className="rounded-3xl bg-gradient-to-br from-indigo-500/20 via-zinc-900 to-zinc-950 p-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-xl font-semibold">
              Ready to generate your paper?
            </h2>
            <p className="text-sm text-zinc-300">
              Jump into the workflow and complete each agent step with clarity.
            </p>
          </div>
          <Link
            href="/workflow"
            className="rounded-lg bg-white px-5 py-2 text-sm font-semibold text-zinc-900 hover:bg-zinc-200"
          >
            Launch workflow
          </Link>
        </div>
      </section>
    </div>
  );
}

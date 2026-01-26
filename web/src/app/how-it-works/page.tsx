import Badge from "@/components/Badge";
import PageHeader from "@/components/PageHeader";
import SectionCard from "@/components/SectionCard";

const agents = [
  {
    title: "Query Agent",
    purpose:
      "Extracts precise keywords and subtopics from your research topic.",
    output: "Keyword list + complexity analysis",
  },
  {
    title: "Retrieval Agent",
    purpose: "Pulls high-relevance, recent papers from arXiv.",
    output: "Curated paper list",
  },
  {
    title: "Summarization Agent",
    purpose: "Builds grounded, section-wise synthesis across all papers.",
    output: "Comprehensive summary",
  },
  {
    title: "Drafting Agent",
    purpose: "Turns the synthesis into academic draft sections.",
    output: "Abstract, Introduction, Related Work",
  },
  {
    title: "Plagiarism Agent",
    purpose: "Checks similarity against sources and flags risks.",
    output: "Plagiarism report",
  },
  {
    title: "Diagram Agent",
    purpose:
      "Converts natural language descriptions into editable technical diagrams using Mermaid.js.",
    output: "Interactive diagrams (flowcharts, sequence, ER, etc.)",
  },
  {
    title: "Pseudocode Agent",
    purpose:
      "Transforms implementation code into professional LaTeX pseudocode for academic papers.",
    output: "LaTeX algorithm2e formatted pseudocode",
  },
];

const tools = [
  {
    title: "Smart Drafter",
    description:
      "A block-based writing workspace for assembling research papers with AI-assisted refinement.",
    features: [
      "Block-based editing with drag-and-drop sections",
      "AI expand & refine for rough notes",
      "Interactive citation chips with quick context",
      "One-click LaTeX/Word export",
      "Live quality constraints (word limits, voice checks)",
    ],
  },
  {
    title: "Text to Diagram",
    description:
      "Generate professional technical diagrams from plain text descriptions using AI-powered Mermaid.js code generation.",
    features: [
      "Natural language to diagram conversion",
      "Support for 8+ diagram types (flowcharts, sequence, class, ER, Gantt, etc.)",
      "Live editable Mermaid code with instant preview",
      "Export diagrams as SVG or PNG",
      "Dark theme optimized for presentations",
      "Perfect for system architectures, workflows, and data models",
    ],
  },
  {
    title: "Code to Pseudocode",
    description:
      "Convert implementation code into publication-ready LaTeX pseudocode using algorithm2e formatting.",
    features: [
      "Mathematical notation and IEEE/ACM formatting",
      "Algorithm2e \For, \If, \While structure support",
      "Ignores boilerplate to focus on core logic",
      "Copy-ready LaTeX output for papers",
    ],
  },
];

export default function HowItWorksPage() {
  return (
    <div className="space-y-8 px-2 md:px-4">
      <PageHeader
        title="How ResearchGen works"
        subtitle="A structured, agent-by-agent pipeline that keeps your research process transparent."
      />

      <section className="grid gap-6 lg:grid-cols-2">
        <SectionCard
          title="Pipeline overview"
          description="Each step unlocks the next to keep the flow clean and reliable."
          actions={<Badge tone="info">Sequential</Badge>}
        >
          <ol className="space-y-3 text-sm text-zinc-300">
            <li>1. Define your topic and extract keywords.</li>
            <li>2. Retrieve high-quality papers with relevance scoring.</li>
            <li>3. Summarize with evidence-backed synthesis.</li>
            <li>4. Draft academic sections with tuned prompts.</li>
            <li>5. Verify originality with plagiarism checks.</li>
            <li>6. Visualize concepts with AI-generated diagrams.</li>
            <li>7. Convert code into LaTeX pseudocode.</li>
          </ol>
        </SectionCard>

        <SectionCard
          title="Why this matters"
          description="Save time while preserving academic rigor."
          actions={<Badge tone="success">Efficiency</Badge>}
        >
          <p className="text-sm text-zinc-300">
            ResearchGen keeps your literature workflow focused and repeatable.
            Every output is grounded in retrieved sources, so you can review,
            edit, and cite with confidence.
          </p>
        </SectionCard>
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Meet the agents</h2>
        <div className="grid gap-4 md:grid-cols-2">
          {agents.map((agent) => (
            <div
              key={agent.title}
              className="rounded-2xl bg-zinc-900 p-5 shadow"
            >
              <div className="text-sm font-semibold">{agent.title}</div>
              <p className="mt-2 text-sm text-zinc-400">{agent.purpose}</p>
              <div className="mt-3 text-xs text-zinc-500">
                Output: {agent.output}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Tools</h2>
        <div className="grid gap-4">
          {tools.map((tool) => (
            <div
              key={tool.title}
              className="rounded-2xl bg-zinc-900 p-5 shadow"
            >
              <div className="flex items-center justify-between">
                <div className="text-sm font-semibold">{tool.title}</div>
                {tool.title === "Text to Diagram" && (
                  <Badge tone="success">New</Badge>
                )}
                {tool.title === "Smart Drafter" && (
                  <Badge tone="info">Featured</Badge>
                )}
              </div>
              <p className="mt-2 text-sm text-zinc-400">{tool.description}</p>
              <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-zinc-300">
                {tool.features.map((feature) => (
                  <li key={feature}>{feature}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

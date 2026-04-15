import Link from "next/link";
import ProjectLogo from "@/components/ProjectLogo";
import SplineScene from "@/components/SplineScene";

export default function Home() {
  return (
    <div className="space-y-12 px-0 pb-6 md:px-4">
      <section className="relative overflow-hidden rounded-none md:rounded-[2.25rem]">
        <div className="pointer-events-none absolute -left-24 -top-16 z-10 h-48 w-48 rounded-full bg-indigo-500/20 blur-3xl" />
        <div className="pointer-events-none absolute right-0 top-10 z-10 h-56 w-56 rounded-full bg-violet-500/10 blur-3xl" />

        <SplineScene
          title="ResearchGen cinematic 3D scene"
          className="h-[620px] w-full rounded-none md:h-[700px] md:rounded-2xl lg:h-[760px]"
        />

        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(105deg,rgba(5,6,16,0.92)_6%,rgba(5,6,16,0.8)_36%,rgba(5,6,16,0.42)_62%,rgba(5,6,16,0.18)_100%)]" />
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-zinc-950/95 via-zinc-950/20 to-transparent" />

        <div className="absolute inset-x-0 bottom-0 z-20 p-6 md:p-10">
          <div className="max-w-3xl space-y-6">
            <ProjectLogo variant="hero" className="px-0 py-0" />
            <div className="text-[11px] uppercase tracking-[0.22em] text-zinc-400">
              Research intelligence, reimagined
            </div>
            <h1 className="text-4xl font-semibold leading-tight tracking-tight text-zinc-100 md:text-6xl">
              Build your paper in one fluid arc—from idea signal to publication
              draft.
            </h1>
            <p className="max-w-2xl text-base leading-relaxed text-zinc-300 md:text-lg">
              ResearchGen feels less like a tool and more like a guided research
              environment: discover evidence, synthesize meaning, shape
              sections, and export with confidence.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link
                href="/workflow"
                className="rounded-xl border border-indigo-300/45 bg-indigo-500/85 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-400"
              >
                Enter workflow
              </Link>
              <Link
                href="/how-it-works"
                className="rounded-xl border border-zinc-600/80 bg-zinc-900/40 px-5 py-2.5 text-sm font-medium text-zinc-100 transition hover:border-zinc-400"
              >
                Explore methodology
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="overflow-hidden py-2">
        <div className="rg-marquee">
          <div className="rg-marquee-track text-xs uppercase tracking-[0.22em] text-zinc-400">
            <span>Query Intelligence</span>
            <span>Retrieval Grounding</span>
            <span>Section Synthesis</span>
            <span>Draft Orchestration</span>
            <span>Originality Guardrails</span>
            <span>Diagram Intelligence</span>
            <span>Pseudocode Publishing</span>
            <span>Query Intelligence</span>
            <span>Retrieval Grounding</span>
            <span>Section Synthesis</span>
            <span>Draft Orchestration</span>
            <span>Originality Guardrails</span>
            <span>Diagram Intelligence</span>
            <span>Pseudocode Publishing</span>
          </div>
        </div>
      </section>

      <section className="grid gap-10 lg:grid-cols-[1.25fr_0.75fr]">
        <div className="space-y-6">
          <h2 className="text-3xl font-semibold tracking-tight text-zinc-100">
            The research flow, represented as momentum—not menus.
          </h2>
          <div className="space-y-5">
            {[
              "Topic decoding",
              "Evidence retrieval",
              "Synthesis shaping",
              "Draft assembly",
              "Integrity validation",
            ].map((step, index) => (
              <div
                key={step}
                className="group flex items-start gap-4 border-b border-zinc-800/70 pb-4 last:border-b-0"
              >
                <div className="text-2xl font-semibold tracking-tight text-zinc-600 transition group-hover:text-indigo-200">
                  0{index + 1}
                </div>
                <div>
                  <div className="text-lg font-medium text-zinc-100">
                    {step}
                  </div>
                  <div className="mt-1 text-sm text-zinc-400">
                    {index === 0 &&
                      "Converts broad intent into precise, searchable vectors."}
                    {index === 1 &&
                      "Finds high-signal papers and surfaces the strongest evidence."}
                    {index === 2 &&
                      "Compresses sources into coherent, citation-aware understanding."}
                    {index === 3 &&
                      "Transforms insights into structured academic language."}
                    {index === 4 &&
                      "Checks overlap risk and protects originality at delivery time."}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-6 border-l border-zinc-800/70 pl-0 lg:pl-8">
          <div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-zinc-500">
              Live stats
            </div>
            <div className="mt-2 text-5xl font-semibold tracking-tight text-zinc-100">
              7
            </div>
            <p className="mt-1 text-sm text-zinc-400">
              Core agents in active chain
            </p>
          </div>
          <div>
            <div className="text-5xl font-semibold tracking-tight text-zinc-100">
              6
            </div>
            <p className="mt-1 text-sm text-zinc-400">
              Dedicated creative workspaces
            </p>
          </div>
          <div>
            <div className="text-5xl font-semibold tracking-tight text-zinc-100">
              3+
            </div>
            <p className="mt-1 text-sm text-zinc-400">
              Draft-ready deliverables per run
            </p>
          </div>
        </div>
      </section>

      <section className="grid gap-8 py-8 lg:grid-cols-2">
        <div className="space-y-4">
          <h3 className="text-2xl font-semibold tracking-tight text-zinc-100">
            Why this feels different
          </h3>
          <p className="text-sm leading-relaxed text-zinc-300">
            Most research stacks force context switching. ResearchGen removes
            friction by connecting retrieval, reasoning, writing, and quality
            checks into one continuous loop.
          </p>
          <p className="text-sm leading-relaxed text-zinc-400">
            The result is a calmer workflow with faster first drafts and
            stronger source transparency.
          </p>
          <Link
            href="/about"
            className="inline-block text-sm text-indigo-300 hover:underline"
          >
            Meet the team and vision →
          </Link>
        </div>
        <div className="space-y-3">
          <h3 className="text-2xl font-semibold tracking-tight text-zinc-100  ">
            Craft layer
          </h3>
          <ul className="space-y-2 text-sm text-zinc-300">
            <li>• Smart Drafter for section-first writing.</li>
            <li>• Universal Formatter for publication layout control.</li>
            <li>• Text-to-Diagram for fast visual communication.</li>
            <li>• Code-to-Pseudocode for conference-ready algorithms.</li>
            <li>• GitHub→IEEE for repository-to-paper generation.</li>
            <li>• DocChat for RAG-powered document Q&A.</li>
          </ul>
          <Link
            href="/how-it-works"
            className="inline-block text-sm text-indigo-300 hover:underline"
          >
            See full architecture →
          </Link>
        </div>
      </section>

      <section className="space-y-3 py-2">
        <h2 className="text-3xl font-semibold tracking-tight text-zinc-100">
          Ready to ship your next paper draft?
        </h2>
        <p className="text-sm text-zinc-300">
          Start the guided flow and let every agent contribute exactly where it
          should.
        </p>
        <Link
          href="/workflow"
          className="inline-block rounded-xl bg-white px-6 py-2.5 text-sm font-semibold text-zinc-900 transition hover:bg-zinc-200"
        >
          Launch ResearchGen
        </Link>
      </section>
    </div>
  );
}

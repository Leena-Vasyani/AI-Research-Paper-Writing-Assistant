"use client";

import React, { useState, useRef } from "react";
import PageHeader from "@/components/PageHeader";
import SectionCard from "@/components/SectionCard";
import { api } from "@/lib/api";
import Mermaid, { type MermaidRef } from "@/components/Mermaid";

const DIAGRAM_TYPES = [
  { value: "auto", label: "Auto (Let AI decide)" },
  { value: "flowchart", label: "Flowchart" },
  { value: "sequence", label: "Sequence Diagram" },
  { value: "class", label: "Class Diagram" },
  { value: "state", label: "State Diagram" },
  { value: "er", label: "Entity Relationship" },
  { value: "gantt", label: "Gantt Chart" },
  { value: "pie", label: "Pie Chart" },
  { value: "architecture", label: "System Architecture" },
];

export default function DiagramGenerator() {
  const [description, setDescription] = useState("");
  const [diagramType, setDiagramType] = useState("auto");
  const [mermaidCode, setMermaidCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mermaidRef = useRef<MermaidRef>(null);

  const handleGenerate = async () => {
    if (!description.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const result = await api.generateDiagram({
        description,
        diagram_type: diagramType,
      });

      if (result.success) {
        setMermaidCode(result.mermaid_code);
      } else {
        setError(result.error || "Failed to generate diagram.");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "An error occurred.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 md:p-8">
      <PageHeader
        title="Text to Diagram"
        subtitle="Generate editable system architectures, flowcharts, and technical diagrams from natural language."
      />

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Left Column: Input & Controls */}
        <div className="flex flex-col gap-6">
          <SectionCard title="Describe your diagram">
            <div className="flex flex-col gap-4">
              <div>
                <label className="mb-2 block text-sm text-zinc-400">
                  What should the diagram show?
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g., A microservices architecture with a gateway, auth service, and paper repository..."
                  className="h-40 w-full rounded-xl border border-zinc-800 bg-zinc-950 p-4 text-sm text-zinc-200 outline-none focus:ring-2 focus:ring-indigo-500/50"
                />
              </div>

              <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
                <div className="flex-1">
                  <label className="mb-2 block text-sm text-zinc-400">
                    Type Hint
                  </label>
                  <select
                    value={diagramType}
                    onChange={(e) => setDiagramType(e.target.value)}
                    className="w-full rounded-xl border border-zinc-800 bg-zinc-950 p-3 text-sm text-zinc-200 outline-none focus:ring-2 focus:ring-indigo-500/50"
                  >
                    {DIAGRAM_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  onClick={handleGenerate}
                  disabled={loading || !description.trim()}
                  className="h-12 whitespace-nowrap rounded-xl bg-indigo-600 px-6 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:bg-zinc-800 disabled:text-zinc-500 disabled:cursor-not-allowed"
                >
                  {loading ? "Generating..." : "Generate Diagram"}
                </button>
              </div>

              {error && (
                <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-3">
                  <p className="text-xs text-red-400">{error}</p>
                </div>
              )}
            </div>
          </SectionCard>

          {mermaidCode && (
            <SectionCard title="Mermaid Code Editor">
              <div className="flex flex-col gap-3">
                <p className="text-xs text-zinc-500">
                  Edit the code below to live-update the diagram:
                </p>
                <textarea
                  value={mermaidCode}
                  onChange={(e) => setMermaidCode(e.target.value)}
                  className="h-64 w-full rounded-xl border border-zinc-800 bg-zinc-950 p-4 font-mono text-xs text-indigo-300 outline-none focus:ring-2 focus:ring-indigo-500/50"
                  spellCheck={false}
                />
                <div className="flex items-center justify-between">
                  <span className="text-xs text-zinc-600">
                    {mermaidCode.split("\n").length} lines
                  </span>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(mermaidCode);
                      alert("Code copied to clipboard!");
                    }}
                    className="rounded-lg bg-zinc-800 px-3 py-1.5 text-xs text-zinc-300 transition hover:bg-zinc-700"
                  >
                    Copy Code
                  </button>
                </div>
              </div>
            </SectionCard>
          )}
        </div>

        {/* Right Column: Preview */}
        <div className="flex flex-col gap-6">
          <SectionCard title="Preview">
            {mermaidCode ? (
              <div className="min-h-[500px]">
                <Mermaid ref={mermaidRef} chart={mermaidCode} />
                <div className="mt-4 flex items-center justify-end gap-2">
                  <button
                    onClick={() => mermaidRef.current?.downloadSVG()}
                    className="flex items-center gap-2 rounded-lg bg-zinc-800 px-4 py-2 text-xs text-zinc-300 transition hover:bg-zinc-700"
                  >
                    <svg
                      className="h-4 w-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                      />
                    </svg>
                    Download SVG
                  </button>
                  <button
                    onClick={() => mermaidRef.current?.downloadPNG()}
                    className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-xs text-white transition hover:bg-indigo-500"
                  >
                    <svg
                      className="h-4 w-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                      />
                    </svg>
                    Download PNG
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex h-[500px] items-center justify-center rounded-xl border-2 border-dashed border-zinc-800 bg-zinc-950/20">
                <div className="text-center">
                  <svg
                    className="mx-auto mb-4 h-16 w-16 text-zinc-700"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"
                    />
                  </svg>
                  <p className="text-sm text-zinc-500">
                    Generate a diagram to see the preview here
                  </p>
                  <p className="mt-1 text-xs text-zinc-600">
                    Describe your diagram and click Generate
                  </p>
                </div>
              </div>
            )}
          </SectionCard>
        </div>
      </div>
    </div>
  );
}

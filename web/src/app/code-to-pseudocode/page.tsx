"use client";

import React, { useState } from "react";
import PageHeader from "@/components/PageHeader";
import SectionCard from "@/components/SectionCard";
import { api } from "@/lib/api";

const EXAMPLE_CODES = [
  {
    name: "Binary Search",
    code: `def binary_search(arr, target):
    left = 0
    right = len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1`,
  },
  {
    name: "Bubble Sort",
    code: `def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr`,
  },
];

export default function CodeToPseudocodePage() {
  const [code, setCode] = useState("");
  const [algorithmName, setAlgorithmName] = useState("");
  const [latexCode, setLatexCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConvert = async () => {
    if (!code.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const result = await api.convertToPseudocode({
        code,
        algorithm_name: algorithmName,
      });

      if (result.success) {
        setLatexCode(result.latex_code);
      } else {
        setError(result.error || "Failed to convert code.");
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message || "An error occurred.");
      } else {
        setError("An error occurred.");
      }
    } finally {
      setLoading(false);
    }
  };

  const loadExample = (example: (typeof EXAMPLE_CODES)[0]) => {
    setCode(example.code);
    setAlgorithmName(example.name);
    setLatexCode("");
  };

  return (
    <div className="p-6 md:p-8">
      <PageHeader
        title="Code to Pseudocode"
        subtitle="Convert implementation code into professional LaTeX pseudocode for academic papers (IEEE/ACM standard)."
      />

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="flex flex-col gap-6">
          <SectionCard title="Source Code">
            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <label className="text-sm text-zinc-400">
                  Paste your implementation code (Python, C++, Java, etc.)
                </label>
                <div className="flex gap-2">
                  {EXAMPLE_CODES.map((ex) => (
                    <button
                      key={ex.name}
                      onClick={() => loadExample(ex)}
                      className="rounded-lg bg-zinc-800 px-3 py-1 text-xs text-zinc-300 transition hover:bg-zinc-700"
                    >
                      Load {ex.name}
                    </button>
                  ))}
                </div>
              </div>

              <textarea
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="def bubble_sort(arr):&#10;    n = len(arr)&#10;    for i in range(n):&#10;        ..."
                className="h-64 w-full rounded-xl border border-zinc-800 bg-zinc-950 p-4 font-mono text-sm text-zinc-200 outline-none focus:ring-2 focus:ring-indigo-500/50"
                spellCheck={false}
              />

              <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
                <div className="flex-1">
                  <label className="mb-2 block text-sm text-zinc-400">
                    Algorithm Name (Optional)
                  </label>
                  <input
                    type="text"
                    value={algorithmName}
                    onChange={(e) => setAlgorithmName(e.target.value)}
                    placeholder="e.g., Bubble Sort"
                    className="w-full rounded-xl border border-zinc-800 bg-zinc-950 p-3 text-sm text-zinc-200 outline-none focus:ring-2 focus:ring-indigo-500/50"
                  />
                </div>
                <button
                  onClick={handleConvert}
                  disabled={loading || !code.trim()}
                  className="h-12 whitespace-nowrap rounded-xl bg-indigo-600 px-6 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-zinc-800 disabled:text-zinc-500"
                >
                  {loading ? "Converting..." : "Convert to Pseudocode"}
                </button>
              </div>

              {error && (
                <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-3">
                  <p className="text-xs text-red-400">{error}</p>
                </div>
              )}
            </div>
          </SectionCard>
        </div>

        <div className="flex flex-col gap-6">
          <SectionCard title="LaTeX Pseudocode">
            {latexCode ? (
              <div className="flex flex-col gap-3">
                <p className="text-xs text-zinc-500">
                  Copy the LaTeX code below for use in your paper:
                </p>
                <textarea
                  value={latexCode}
                  readOnly
                  className="h-96 w-full rounded-xl border border-zinc-800 bg-zinc-950 p-4 font-mono text-xs text-green-300 outline-none focus:ring-2 focus:ring-indigo-500/50"
                  spellCheck={false}
                />
                <div className="flex items-center justify-between">
                  <span className="text-xs text-zinc-600">
                    {latexCode.split("\n").length} lines
                  </span>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(latexCode);
                      alert("LaTeX code copied to clipboard!");
                    }}
                    className="rounded-lg bg-indigo-600 px-4 py-2 text-xs text-white transition hover:bg-indigo-500"
                  >
                    Copy LaTeX Code
                  </button>
                </div>

                <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
                  <p className="mb-2 text-xs font-semibold text-zinc-400">
                    Usage in LaTeX:
                  </p>
                  <pre className="overflow-x-auto text-xs text-zinc-500">
                    {`\\usepackage[ruled,vlined]{algorithm2e}
...
${latexCode.split("\n").slice(0, 3).join("\n")}
...`}
                  </pre>
                </div>
              </div>
            ) : (
              <div className="flex h-96 items-center justify-center rounded-xl border-2 border-dashed border-zinc-800 bg-zinc-950/20">
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
                      d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"
                    />
                  </svg>
                  <p className="text-sm text-zinc-500">
                    Convert your code to see LaTeX pseudocode here
                  </p>
                  <p className="mt-1 text-xs text-zinc-600">
                    Paste code and click Convert
                  </p>
                </div>
              </div>
            )}
          </SectionCard>
        </div>
      </div>

      <div className="mt-6">
        <SectionCard title="Features">
          <div className="grid gap-4 text-sm text-zinc-300 md:grid-cols-2">
            <div>
              <h4 className="mb-2 font-semibold text-zinc-200">
                ✓ Mathematical Notation
              </h4>
              <p className="text-xs text-zinc-400">
                Converts assignments to ← symbols, comparisons to mathematical
                equivalents (=, ≠), and uses proper variable notation.
              </p>
            </div>
            <div>
              <h4 className="mb-2 font-semibold text-zinc-200">
                ✓ Algorithm2e Format
              </h4>
              <p className="text-xs text-zinc-400">
                Generates LaTeX code using the algorithm2e package with proper
                \For, \If, \While structures.
              </p>
            </div>
            <div>
              <h4 className="mb-2 font-semibold text-zinc-200">
                ✓ Smart Logic Analysis
              </h4>
              <p className="text-xs text-zinc-400">
                Focuses on core algorithm logic while ignoring boilerplate code
                like imports, logging, and error handling.
              </p>
            </div>
            <div>
              <h4 className="mb-2 font-semibold text-zinc-200">
                ✓ Publication Ready
              </h4>
              <p className="text-xs text-zinc-400">
                Produces IEEE/ACM standard pseudocode suitable for research
                papers and academic publications.
              </p>
            </div>
          </div>
        </SectionCard>
      </div>
    </div>
  );
}

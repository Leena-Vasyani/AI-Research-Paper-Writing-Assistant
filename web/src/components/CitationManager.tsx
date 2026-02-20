import React, { useState } from "react";
import type { CitationCandidate } from "@/lib/types";

export type Citation = {
  id: string;
  title: string;
  authors: string;
  year: string;
  venue: string;
  note: string;
};

interface CitationManagerProps {
  citations: Citation[];
  onAdd: () => void;
  onUpdate: (id: string, patch: Partial<Citation>) => void;
  onDelete: (id: string) => void;
  onInsert: (id: string) => void;
  onSuggestClaim?: (claimText: string) => void;
  onApplySuggestion?: (candidate: CitationCandidate) => void;
  suggestions?: CitationCandidate[];
  isSuggesting?: boolean;
  suggestionStatus?: string | null;
}

export default function CitationManager({
  citations,
  onAdd,
  onUpdate,
  onDelete,
  onInsert,
  onSuggestClaim,
  onApplySuggestion,
  suggestions = [],
  isSuggesting = false,
  suggestionStatus,
}: CitationManagerProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [claimInput, setClaimInput] = useState("");

  const formatCitation = (citation: Citation, index: number): string => {
    // IEEE format: [1] A. Author, "Title," Venue, Year.
    const parts: string[] = [];
    if (citation.authors) parts.push(citation.authors);
    if (citation.title) parts.push(`"${citation.title}"`);
    if (citation.venue) parts.push(citation.venue);
    if (citation.year) parts.push(citation.year + ".");
    return `[${index + 1}] ${parts.join(", ")}`;
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-xs uppercase text-zinc-500">
          Citations ({citations.length})
        </div>
        <button
          onClick={onAdd}
          className="rounded-lg border border-zinc-800 px-3 py-1 text-xs text-zinc-300 hover:bg-zinc-800"
        >
          + Add Citation
        </button>
      </div>

      {onSuggestClaim && (
        <div className="space-y-2 rounded-lg border border-cyan-900/60 bg-cyan-950/20 p-3">
          <div className="text-[11px] uppercase text-cyan-300">
            AI Citation Suggestions
          </div>
          <div className="flex gap-2">
            <input
              value={claimInput}
              onChange={(e) => setClaimInput(e.target.value)}
              placeholder="Enter claim text (or paste sentence)"
              className="flex-1 rounded-md border border-zinc-800 bg-zinc-900 px-2 py-1 text-xs text-zinc-100"
            />
            <button
              onClick={() => onSuggestClaim(claimInput.trim())}
              disabled={isSuggesting || !claimInput.trim()}
              className="rounded-md border border-cyan-700 px-3 py-1 text-xs text-cyan-200 hover:bg-cyan-900/30 disabled:opacity-50"
            >
              {isSuggesting ? "Searching..." : "Suggest"}
            </button>
          </div>
          {suggestionStatus && (
            <div className="text-[11px] text-cyan-200">{suggestionStatus}</div>
          )}
          {!!suggestions.length && (
            <div className="space-y-2">
              {suggestions.map((candidate, idx) => (
                <div
                  key={`${candidate.title}-${idx}`}
                  className="rounded-md border border-zinc-800 bg-zinc-900/50 p-2"
                >
                  <div className="text-xs text-zinc-200">
                    [{idx + 1}] {candidate.title || "Untitled"}
                  </div>
                  <div className="mt-1 text-[11px] text-zinc-400">
                    {candidate.authors || "Unknown authors"} •{" "}
                    {candidate.year || "n.d."} •{" "}
                    {Math.round((candidate.relevance_score || 0) * 100)}%
                  </div>
                  <div className="mt-1 text-[11px] text-zinc-500 break-all">
                    {candidate.reference}
                  </div>
                  {onApplySuggestion && (
                    <div className="mt-2">
                      <button
                        onClick={() => onApplySuggestion(candidate)}
                        className="rounded border border-zinc-700 px-2 py-1 text-[10px] text-zinc-200 hover:bg-zinc-800"
                      >
                        Use this citation
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {citations.length === 0 ? (
        <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4 text-center text-xs text-zinc-500">
          No citations yet. Click &quot;Add Citation&quot; to get started.
        </div>
      ) : (
        <div className="space-y-2">
          {citations.map((citation, index) => (
            <div
              key={citation.id}
              className="rounded-lg border border-zinc-800 bg-zinc-950 p-3"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1">
                  <div className="mb-1 text-xs font-medium text-zinc-300">
                    [{index + 1}] {citation.title || "Untitled"}
                  </div>
                  {expandedId === citation.id ? (
                    <div className="mt-2 space-y-2">
                      <input
                        value={citation.title}
                        onChange={(e) =>
                          onUpdate(citation.id, { title: e.target.value })
                        }
                        placeholder="Paper title"
                        className="w-full rounded-md border border-zinc-800 bg-zinc-900 px-2 py-1 text-xs text-zinc-100"
                      />
                      <input
                        value={citation.authors}
                        onChange={(e) =>
                          onUpdate(citation.id, { authors: e.target.value })
                        }
                        placeholder="Authors (e.g., J. Smith, A. Doe)"
                        className="w-full rounded-md border border-zinc-800 bg-zinc-900 px-2 py-1 text-xs text-zinc-100"
                      />
                      <div className="grid grid-cols-2 gap-2">
                        <input
                          value={citation.venue}
                          onChange={(e) =>
                            onUpdate(citation.id, { venue: e.target.value })
                          }
                          placeholder="Venue/Journal"
                          className="w-full rounded-md border border-zinc-800 bg-zinc-900 px-2 py-1 text-xs text-zinc-100"
                        />
                        <input
                          value={citation.year}
                          onChange={(e) =>
                            onUpdate(citation.id, { year: e.target.value })
                          }
                          placeholder="Year"
                          className="w-full rounded-md border border-zinc-800 bg-zinc-900 px-2 py-1 text-xs text-zinc-100"
                        />
                      </div>
                      <textarea
                        value={citation.note}
                        onChange={(e) =>
                          onUpdate(citation.id, { note: e.target.value })
                        }
                        placeholder="Additional notes (optional)"
                        className="w-full rounded-md border border-zinc-800 bg-zinc-900 px-2 py-1 text-xs text-zinc-100"
                        rows={2}
                      />
                      <div className="rounded border border-zinc-800 bg-zinc-900/50 p-2 text-xs text-zinc-400">
                        <div className="mb-1 text-[10px] uppercase text-zinc-600">
                          IEEE Format Preview:
                        </div>
                        {formatCitation(citation, index)}
                      </div>
                    </div>
                  ) : (
                    <div className="text-[11px] text-zinc-500">
                      {citation.authors || "No authors"} •{" "}
                      {citation.year || "No year"}
                    </div>
                  )}
                </div>
                <div className="flex gap-1">
                  <button
                    onClick={() =>
                      setExpandedId(
                        expandedId === citation.id ? null : citation.id,
                      )
                    }
                    className="rounded border border-zinc-800 px-2 py-1 text-[10px] text-zinc-400 hover:bg-zinc-800"
                    title={expandedId === citation.id ? "Collapse" : "Edit"}
                  >
                    {expandedId === citation.id ? "−" : "✎"}
                  </button>
                  <button
                    onClick={() => onInsert(citation.id)}
                    className="rounded border border-zinc-800 px-2 py-1 text-[10px] text-zinc-400 hover:bg-zinc-800"
                    title="Insert citation"
                  >
                    [↑]
                  </button>
                  <button
                    onClick={() => onDelete(citation.id)}
                    className="rounded border border-zinc-800 px-2 py-1 text-[10px] text-rose-400 hover:bg-zinc-800"
                    title="Delete"
                  >
                    ×
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

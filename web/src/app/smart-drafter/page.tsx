"use client";

import { useEffect, useMemo, useState } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import { Extension } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import { api } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import SectionCard from "@/components/SectionCard";
import TableInsertDialog from "@/components/TableInsertDialog";
import EquationEditor from "@/components/EquationEditor";
import CitationManager, { Citation } from "@/components/CitationManager";
import { Document, Packer, Paragraph } from "docx";
import wordList from "word-list-json";
import { Plugin } from "prosemirror-state";
import { Decoration, DecorationSet } from "prosemirror-view";
import "katex/dist/katex.min.css";
import "./smart-drafter.css";

const defaultCitations: Citation[] = [];

export default function SmartDrafterPage() {
  const [citations, setCitations] = useState<Citation[]>(defaultCitations);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [liveText, setLiveText] = useState<string>("");
  const [autocomplete, setAutocomplete] = useState<string[]>([]);
  const [misspellings, setMisspellings] = useState<
    { word: string; suggestions: string[] }[]
  >([]);
  const [showTableDialog, setShowTableDialog] = useState(false);
  const [showEquationEditor, setShowEquationEditor] = useState(false);
  const [showGrammarPanel, setShowGrammarPanel] = useState(true);

  const wordSet = useMemo(() => new Set(wordList), []);
  const wordIndex = useMemo(() => buildWordIndex(wordList), []);

  const SpellcheckExtension = useMemo(
    () =>
      Extension.create({
        name: "spellcheck",
        addProseMirrorPlugins() {
          return [
            new Plugin({
              props: {
                decorations: (state) =>
                  buildSpellDecorations(state.doc, wordSet),
              },
            }),
          ];
        },
      }),
    [wordSet],
  );

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: { levels: [1, 2, 3] },
      }),
      Placeholder.configure({
        placeholder: "Start drafting your research paper...",
      }),
      SpellcheckExtension,
    ],
    immediatelyRender: false,
    editorProps: {
      attributes: {
        spellcheck: "true",
        class: "smart-drafter-editor",
      },
    },
    content: "<h1>Title</h1><p>Start drafting your research paper...</p>",
  });

  const draftText = useMemo(() => editor?.getText() ?? "", [editor]);

  useEffect(() => {
    if (!editor) return;
    const update = () => {
      const text = editor.getText() ?? "";
      setLiveText(text);
      setAutocomplete(getAutocomplete(text));
    };
    update();
    editor.on("update", update);
    return () => {
      editor.off("update", update);
    };
  }, [editor]);

  useEffect(() => {
    const words = Array.from(
      new Set(
        (liveText.match(/[a-zA-Z']+/g) || [])
          .map((w) => w.toLowerCase())
          .filter((w) => w.length > 2),
      ),
    );
    const issues = words
      .filter((word) => !wordSet.has(word))
      .slice(0, 12)
      .map((word) => ({
        word,
        suggestions: suggestWords(word, wordIndex).slice(0, 5),
      }));
    setMisspellings(issues);
  }, [liveText, wordSet, wordIndex]);

  const addCitation = () => {
    setCitations((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        title: "",
        authors: "",
        year: "",
        venue: "",
        note: "",
      },
    ]);
  };

  const updateCitation = (citationId: string, patch: Partial<Citation>) => {
    setCitations((prev) =>
      prev.map((c) => (c.id === citationId ? { ...c, ...patch } : c)),
    );
  };

  const deleteCitation = (citationId: string) => {
    setCitations((prev) => prev.filter((c) => c.id !== citationId));
  };

  const insertCitation = (citationId: string) => {
    if (!editor) return;
    const index = citations.findIndex((c) => c.id === citationId);
    if (index === -1) return;
    editor.chain().focus().insertContent(`[${index + 1}]`).run();
  };

  const insertTable = (rows: number, cols: number, withHeader: boolean) => {
    if (!editor) return;

    // Build simple HTML table
    let tableHTML = '<table class="ieee-table"><thead>';

    if (withHeader) {
      tableHTML += '<tr>';
      for (let i = 0; i < cols; i++) {
        tableHTML += `<th>Header ${i + 1}</th>`;
      }
      tableHTML += '</tr></thead><tbody>';
      rows--;
    } else {
      tableHTML += '</thead><tbody>';
    }

    for (let i = 0; i < rows; i++) {
      tableHTML += '<tr>';
      for (let j = 0; j < cols; j++) {
        tableHTML += `<td>Cell</td>`;
      }
      tableHTML += '</tr>';
    }

    tableHTML += '</tbody></table>';
    editor.chain().focus().insertContent(tableHTML).run();
  };

  const insertEquation = (latex: string, isBlock: boolean) => {
    if (!editor) return;
    const content = isBlock
      ? `<p><em class="equation-block">${latex}</em></p>`
      : `<em class="equation-inline">${latex}</em>`;
    editor.chain().focus().insertContent(content).run();
  };

  const refineSelection = async (mode: "expand" | "academic" | "refine") => {
    if (!editor) return;
    const selectedText = editor.state.doc.textBetween(
      editor.state.selection.from,
      editor.state.selection.to,
      " ",
    );
    const text = selectedText.trim() || editor.getText().trim();
    if (!text) return;
    setStatus(`Refining (${mode})...`);
    setError(null);
    try {
      const result = await api.refineBlock({ text, mode });
      if (selectedText.trim()) {
        editor.commands.insertContent(result.refined_text);
      } else {
        editor.commands.setContent(
          result.refined_text.replace(/\n/g, "<br />"),
        );
      }
      setStatus(`Refined with ${result.provider}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Refine failed");
    } finally {
      setTimeout(() => setStatus(null), 1500);
    }
  };

  const exportJson = () => {
    const payload = {
      content: editor?.getJSON() ?? {},
      citations,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "smart_drafter.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportTxt = () => {
    const blob = new Blob([draftText], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "smart_drafter.txt";
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportLatex = () => {
    const lines = (editor?.getText() ?? "").split("\n").filter(Boolean);
    const latex = [
      "\\documentclass{article}",
      "\\begin{document}",
      ...lines,
      "\\end{document}",
    ].join("\n\n");
    const blob = new Blob([latex], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "smart_drafter.tex";
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportDocx = async () => {
    const paragraphs = (editor?.getText() ?? "")
      .split("\n")
      .filter((line) => line.trim())
      .map((line) => new Paragraph(line));

    const doc = new Document({
      sections: [
        {
          children: paragraphs.length ? paragraphs : [new Paragraph(" ")],
        },
      ],
    });

    const blob = await Packer.toBlob(doc);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "smart_drafter.docx";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6 px-2 md:px-4">
      <PageHeader
        title="Smart Drafter"
        subtitle="Block-based editor with AI expand/refine and multi-format export."
        actions={
          <div className="flex flex-wrap gap-2">
            <button
              onClick={exportJson}
              className="rounded-lg border border-zinc-800 px-3 py-2 text-xs text-zinc-200 hover:bg-zinc-800"
            >
              Export JSON
            </button>
            <button
              onClick={exportTxt}
              className="rounded-lg border border-zinc-800 px-3 py-2 text-xs text-zinc-200 hover:bg-zinc-800"
            >
              Export TXT
            </button>
            <button
              onClick={exportLatex}
              className="rounded-lg border border-zinc-800 px-3 py-2 text-xs text-zinc-200 hover:bg-zinc-800"
            >
              Export LaTeX
            </button>
            <button
              onClick={exportDocx}
              className="rounded-lg border border-zinc-800 px-3 py-2 text-xs text-zinc-200 hover:bg-zinc-800"
            >
              Export DOCX
            </button>
          </div>
        }
      />

      <div className="flex flex-wrap gap-3">
        <button
          onClick={() =>
            editor?.chain().focus().toggleHeading({ level: 1 }).run()
          }
          className="rounded-lg bg-indigo-500 px-4 py-2 text-xs font-medium text-white hover:bg-indigo-400"
        >
          H1
        </button>
        <button
          onClick={() =>
            editor?.chain().focus().toggleHeading({ level: 2 }).run()
          }
          className="rounded-lg bg-indigo-500 px-4 py-2 text-xs font-medium text-white hover:bg-indigo-400"
        >
          H2
        </button>
        <button
          onClick={() => editor?.chain().focus().toggleBulletList().run()}
          className="rounded-lg bg-indigo-500 px-4 py-2 text-xs font-medium text-white hover:bg-indigo-400"
        >
          Bullet list
        </button>
        <button
          onClick={() => editor?.chain().focus().toggleBlockquote().run()}
          className="rounded-lg bg-indigo-500 px-4 py-2 text-xs font-medium text-white hover:bg-indigo-400"
        >
          Quote
        </button>
        <button
          onClick={() => setShowTableDialog(true)}
          className="rounded-lg bg-emerald-500 px-4 py-2 text-xs font-medium text-white hover:bg-emerald-400"
        >
          📊 Insert Table
        </button>
        <button
          onClick={() => setShowEquationEditor(true)}
          className="rounded-lg bg-purple-500 px-4 py-2 text-xs font-medium text-white hover:bg-purple-400"
        >
          ∑ Insert Equation
        </button>
      </div>

      {status && <div className="text-xs text-emerald-300">{status}</div>}
      {error && <div className="text-xs text-rose-400">{error}</div>}

      <SectionCard
        title="Smart Drafter"
        description="Rich-text blocks with TipTap."
      >
        <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-4">
          {editor ? (
            <EditorContent
              editor={editor}
              className="prose prose-invert max-w-none"
            />
          ) : (
            <div className="text-sm text-zinc-400">Loading editor...</div>
          )}
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            onClick={() => refineSelection("expand")}
            className="rounded-lg border border-zinc-800 px-3 py-1 text-xs text-zinc-200 hover:bg-zinc-800"
          >
            Expand
          </button>
          <button
            onClick={() => refineSelection("academic")}
            className="rounded-lg border border-zinc-800 px-3 py-1 text-xs text-zinc-200 hover:bg-zinc-800"
          >
            Make Academic
          </button>
          <button
            onClick={() => refineSelection("refine")}
            className="rounded-lg border border-zinc-800 px-3 py-1 text-xs text-zinc-200 hover:bg-zinc-800"
          >
            Refine
          </button>
        </div>
      </SectionCard>

      <SectionCard
        title="Grammar & recommendations"
        description="Live checks and suggestions."
      >
        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-4 text-xs text-zinc-300">
            <div className="text-[11px] uppercase text-zinc-500">
              Issues detected
            </div>
            <ul className="mt-2 space-y-2">
              {getIssues(liveText).map((issue) => (
                <li
                  key={issue.id}
                  className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-2"
                >
                  <div className="text-xs font-semibold">{issue.title}</div>
                  <div className="text-[11px] text-zinc-400">
                    {issue.detail}
                  </div>
                  {issue.apply && editor && (
                    <button
                      onClick={() => issue.apply?.(editor)}
                      className="mt-2 rounded-lg border border-zinc-800 px-2 py-1 text-[11px] text-zinc-200 hover:bg-zinc-800"
                    >
                      Apply fix
                    </button>
                  )}
                </li>
              ))}
              {!getIssues(liveText).length && (
                <li className="text-[11px] text-zinc-500">
                  No issues detected.
                </li>
              )}
            </ul>
          </div>
          <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-4 text-xs text-zinc-300">
            <div className="text-[11px] uppercase text-zinc-500">
              Recommendations
            </div>
            <ul className="mt-2 space-y-2">
              {getRecommendations(liveText).map((rec) => (
                <li
                  key={rec}
                  className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-2"
                >
                  {rec}
                </li>
              ))}
              {!getRecommendations(liveText).length && (
                <li className="text-[11px] text-zinc-500">
                  No recommendations yet.
                </li>
              )}
            </ul>
          </div>
        </div>
      </SectionCard>

      <SectionCard
        title="Spelling"
        description="Misspellings with quick suggestions."
      >
        <div className="space-y-2 text-xs text-zinc-300">
          {misspellings.map((issue) => (
            <div
              key={issue.word}
              className="rounded-lg border border-zinc-800 bg-zinc-950 p-3"
            >
              <div className="text-[11px] uppercase text-zinc-500">
                {issue.word}
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {issue.suggestions.length ? (
                  issue.suggestions.map((s) => (
                    <button
                      key={s}
                      onClick={() =>
                        editor?.chain().focus().insertContent(` ${s}`).run()
                      }
                      className="rounded-full border border-zinc-800 px-3 py-1 text-[11px] text-zinc-200 hover:bg-zinc-800"
                    >
                      {s}
                    </button>
                  ))
                ) : (
                  <span className="text-[11px] text-zinc-500">
                    No suggestions
                  </span>
                )}
              </div>
            </div>
          ))}
          {!misspellings.length && (
            <div className="text-[11px] text-zinc-500">
              No misspellings detected.
            </div>
          )}
        </div>
      </SectionCard>

      <SectionCard
        title="Autocomplete"
        description="Quick academic completions."
      >
        <div className="flex flex-wrap gap-2">
          {autocomplete.length ? (
            autocomplete.map((item) => (
              <button
                key={item}
                onClick={() =>
                  editor?.chain().focus().insertContent(` ${item}`).run()
                }
                className="rounded-full border border-zinc-800 px-3 py-1 text-xs text-zinc-200 hover:bg-zinc-800"
              >
                {item}
              </button>
            ))
          ) : (
            <span className="text-xs text-zinc-500">No suggestions yet.</span>
          )}
        </div>
      </SectionCard>

      <SectionCard title="Citations" description="IEEE-formatted citations.">
        <CitationManager
          citations={citations}
          onAdd={addCitation}
          onUpdate={updateCitation}
          onDelete={deleteCitation}
          onInsert={insertCitation}
        />
      </SectionCard>

      <SectionCard
        title="Live quality constraints"
        description="Quick checks for academic compliance."
      >
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-3 text-xs text-zinc-300">
            Abstract length: {draftText.split(/\s+/).filter(Boolean).length}{" "}
            words
          </div>
          <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-3 text-xs text-zinc-300">
            Passive voice check:{" "}
            {draftText.match(/\bwas\b|\bwere\b/gi)?.length ?? 0} flags
          </div>
          <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-3 text-xs text-zinc-300">
            Sections: {editor?.getJSON()?.content?.length ?? 0}
          </div>
        </div>
      </SectionCard>

      {/* Dialog Components */}
      <TableInsertDialog
        isOpen={showTableDialog}
        onClose={() => setShowTableDialog(false)}
        onInsert={insertTable}
      />
      <EquationEditor
        isOpen={showEquationEditor}
        onClose={() => setShowEquationEditor(false)}
        onInsert={insertEquation}
      />
    </div>
  );
}

type Issue = {
  id: string;
  title: string;
  detail: string;
  apply?: (editor: import("@tiptap/react").Editor) => void;
};

const getIssues = (text: string): Issue[] => {
  const issues: Issue[] = [];
  if (!text.trim()) return issues;

  if (/\s{2,}/.test(text)) {
    issues.push({
      id: "double-spaces",
      title: "Extra spaces",
      detail: "Multiple consecutive spaces detected.",
      apply: (editor) => {
        const cleaned = editor.getText().replace(/\s{2,}/g, " ");
        editor.commands.setContent(cleaned.replace(/\n/g, "<br />"));
      },
    });
  }

  const longSentences = text
    .split(/(?<=[.!?])\s+/)
    .filter((s) => s.split(/\s+/).length > 28);
  if (longSentences.length) {
    issues.push({
      id: "long-sentences",
      title: "Long sentences",
      detail: `${longSentences.length} sentence(s) exceed 28 words. Consider splitting.`,
    });
  }

  const passive = (text.match(/\bwas\b|\bwere\b|\bbeen\b/gi) || []).length;
  if (passive > 6) {
    issues.push({
      id: "passive-voice",
      title: "Passive voice",
      detail: `Passive-voice markers found (${passive}). Consider active voice.`,
    });
  }

  if (/(\b\w+\b) \1\b/i.test(text)) {
    issues.push({
      id: "repeated-word",
      title: "Repeated word",
      detail: "Adjacent repeated words detected.",
    });
  }

  return issues;
};

const getRecommendations = (text: string): string[] => {
  if (!text.trim()) return [];
  const recs: string[] = [];
  if (text.length < 200)
    recs.push("Add a brief context sentence to frame the section.");
  if (!/\btherefore\b|\bthus\b|\bconsequently\b/i.test(text)) {
    recs.push("Add a transitional phrase to improve flow.");
  }
  if (!/\bhowever\b|\balthough\b|\bdespite\b/i.test(text)) {
    recs.push("Introduce contrast to improve argument balance.");
  }
  return recs;
};

const getAutocomplete = (text: string): string[] => {
  const tail = text.trim().split(/\s+/).slice(-3).join(" ").toLowerCase();
  const suggestions = [
    "This study demonstrates that",
    "The results indicate that",
    "In conclusion,",
    "A key contribution is",
    "Future work should",
    "The proposed method",
    "These findings suggest",
  ];

  if (!tail) return suggestions.slice(0, 3);
  if (tail.includes("this"))
    return [
      "This study demonstrates that",
      "This approach improves",
      "This work highlights",
    ];
  if (tail.includes("the"))
    return [
      "The results indicate that",
      "The proposed method",
      "The analysis shows",
    ];
  return suggestions.slice(0, 3);
};

const buildWordIndex = (words: string[]) => {
  const index = new Map<string, string[]>();
  words.forEach((word) => {
    const key = word[0]?.toLowerCase() || "";
    if (!index.has(key)) index.set(key, []);
    index.get(key)?.push(word);
  });
  return index;
};

const levenshtein = (a: string, b: string): number => {
  const dp = Array.from({ length: a.length + 1 }, () =>
    new Array(b.length + 1).fill(0),
  );
  for (let i = 0; i <= a.length; i += 1) dp[i][0] = i;
  for (let j = 0; j <= b.length; j += 1) dp[0][j] = j;
  for (let i = 1; i <= a.length; i += 1) {
    for (let j = 1; j <= b.length; j += 1) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      dp[i][j] = Math.min(
        dp[i - 1][j] + 1,
        dp[i][j - 1] + 1,
        dp[i - 1][j - 1] + cost,
      );
    }
  }
  return dp[a.length][b.length];
};

const suggestWords = (word: string, index: Map<string, string[]>) => {
  const key = word[0]?.toLowerCase() || "";
  const candidates = index.get(key) ?? [];
  const filtered = candidates.filter(
    (w) => Math.abs(w.length - word.length) <= 2,
  );
  return filtered
    .map((w) => ({ w, score: levenshtein(word, w) }))
    .sort((a, b) => a.score - b.score)
    .slice(0, 8)
    .map((item) => item.w);
};

const buildSpellDecorations = (
  doc: any,
  wordSet: Set<string>,
): DecorationSet => {
  const decorations: Decoration[] = [];
  doc.descendants((node: any, pos: number) => {
    if (!node.isText) return;
    const text = node.text || "";
    const regex = /[a-zA-Z']+/g;
    let match: RegExpExecArray | null;
    while ((match = regex.exec(text)) !== null) {
      const word = match[0].toLowerCase();
      if (word.length <= 2) continue;
      if (!wordSet.has(word)) {
        const from = pos + match.index;
        const to = from + match[0].length;
        decorations.push(
          Decoration.inline(from, to, { class: "spell-underline" }),
        );
      }
    }
  });
  return DecorationSet.create(doc, decorations);
};

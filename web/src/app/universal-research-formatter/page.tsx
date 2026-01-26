"use client";

import type { CSSProperties } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import { InputRule, Node, mergeAttributes } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import Document from "@tiptap/extension-document";
import { parse } from "latex.js";
import katex from "katex";
import "katex/dist/katex.min.css";
import PageHeader from "@/components/PageHeader";
import SectionCard from "@/components/SectionCard";
import Badge from "@/components/Badge";
import { api } from "@/lib/api";

type PaperSettings = {
  colCount: 1 | 2;
  colGap: string;
  fontSize: string;
  marginX: string;
  marginY: string;
};

const defaultSettings: PaperSettings = {
  colCount: 2,
  colGap: "0.25in",
  fontSize: "10pt",
  marginX: "0.75in",
  marginY: "1in",
};

const MathInline = Node.create({
  name: "mathInline",
  group: "inline",
  inline: true,
  atom: true,
  selectable: true,
  addAttributes() {
    return {
      latex: {
        default: "",
      },
    };
  },
  parseHTML() {
    return [
      {
        tag: "span[data-math-inline]",
        getAttrs: (node) => ({
          latex: decodeURIComponent(
            (node as HTMLElement).getAttribute("data-math-inline") ?? "",
          ),
        }),
      },
    ];
  },
  renderHTML({ HTMLAttributes }) {
    const latex = encodeURIComponent(HTMLAttributes.latex ?? "");
    return [
      "span",
      mergeAttributes(HTMLAttributes, {
        "data-math-inline": latex,
        class: "math-inline",
      }),
      `$${HTMLAttributes.latex ?? ""}$`,
    ];
  },
  addNodeView() {
    return ({ node }) => {
      const span = document.createElement("span");
      span.className = "math-inline";
      span.dataset.mathInline = encodeURIComponent(node.attrs.latex ?? "");
      try {
        span.innerHTML = katex.renderToString(node.attrs.latex ?? "", {
          throwOnError: false,
        });
      } catch {
        span.textContent = `$${node.attrs.latex ?? ""}$`;
      }
      return { dom: span };
    };
  },
  addInputRules() {
    return [
      new InputRule({
        find: /\$([^$\n]+)\$/,
        handler: ({ range, match, chain }) => {
          const latex = match[1]?.trim();
          if (!latex) return;
          chain()
            .insertContentAt(range, {
              type: "mathInline",
              attrs: { latex },
            })
            .run();
        },
      }),
    ];
  },
});

const PageBreak = Node.create({
  name: "pageBreak",
  group: "block",
  atom: true,
  selectable: false,
  parseHTML() {
    return [{ tag: "div[data-page-break]" }];
  },
  renderHTML() {
    return [
      "div",
      {
        "data-page-break": "true",
        class: "page-break",
      },
    ];
  },
});

const Page = Node.create({
  name: "page",
  group: "block",
  content: "block+",
  defining: true,
  isolating: true,
  parseHTML() {
    return [{ tag: "div[data-page]" }];
  },
  renderHTML() {
    return ["div", { "data-page": "true", class: "paper-page" }, 0];
  },
});

const CustomDocument = Document.extend({
  content: "page+",
});

export default function UniversalResearchFormatterPage() {
  const [settings, setSettings] = useState<PaperSettings>(defaultSettings);
  const [quickFixPrompt, setQuickFixPrompt] = useState<string>("");
  const [quickFixStatus, setQuickFixStatus] = useState<string | null>(null);
  const [quickFixError, setQuickFixError] = useState<string | null>(null);
  const [quickFixLoading, setQuickFixLoading] = useState<boolean>(false);
  const [exportStatus, setExportStatus] = useState<string | null>(null);
  const [rawInput, setRawInput] = useState<string>("");
  const [titleInput, setTitleInput] = useState<string>("");
  const [headingInput, setHeadingInput] = useState<string>("");
  const [pageCount, setPageCount] = useState<number>(1);
  const [pageHeightPx, setPageHeightPx] = useState<number>(1122);
  const [marginYPx, setMarginYPx] = useState<number>(96);
  const columnsRef = useRef<HTMLDivElement | null>(null);
  const paginatingRef = useRef<boolean>(false);

  const editor = useEditor({
    extensions: [
      CustomDocument,
      Page,
      StarterKit.configure({
        document: false,
        heading: { levels: [1, 2, 3] },
      }),
      Placeholder.configure({
        placeholder: "Start writing your research paper...",
      }),
      MathInline,
      PageBreak,
    ],
    immediatelyRender: false,
    content:
      '<div data-page="true"><h1>Paper Title</h1><p>Add your abstract and sections inside the live A4 preview.</p></div>',
  });

  const paperStyle = useMemo(
    () =>
      ({
        "--col-count": String(settings.colCount),
        "--col-gap": settings.colGap,
        "--font-size": settings.fontSize,
        "--margin-x": settings.marginX,
        "--margin-y": settings.marginY,
        "--page-width": "8.27in",
        "--page-height": "11.69in",
        "--page-height-px": `${pageHeightPx}px`,
        "--margin-y-px": `${marginYPx}px`,
        "--page-count": String(pageCount),
      }) as CSSProperties,
    [settings, pageCount, pageHeightPx, marginYPx],
  );

  const toPx = (value: string, fallback: number) => {
    const raw = value.trim().toLowerCase();
    if (!raw) return fallback;
    const match = raw.match(/^([\d.]+)\s*(in|pt|cm|mm|px)?$/);
    if (!match) return fallback;
    const amount = Number(match[1]);
    const unit = match[2] ?? "in";
    if (!Number.isFinite(amount)) return fallback;
    if (unit === "px") return amount;
    if (unit === "pt") return (amount * 96) / 72;
    if (unit === "cm") return (amount * 96) / 2.54;
    if (unit === "mm") return (amount * 96) / 25.4;
    return amount * 96;
  };

  useEffect(() => {
    const computePages = () => {
      const heightPx = 11.69 * 96;
      const marginPx = toPx(settings.marginY, 96);
      let count = 0;
      editor?.state.doc.descendants((node) => {
        if (node.type.name === "page") count += 1;
      });
      setPageHeightPx(heightPx);
      setMarginYPx(marginPx);
      setPageCount(Math.max(1, count));
    };

    computePages();
    const handleResize = () => computePages();
    window.addEventListener("resize", handleResize);
    if (editor) {
      editor.on("update", computePages);
    }
    return () => {
      window.removeEventListener("resize", handleResize);
      if (editor) {
        editor.off("update", computePages);
      }
    };
  }, [
    editor,
    settings.marginY,
    settings.colCount,
    settings.colGap,
    settings.fontSize,
  ]);

  useEffect(() => {
    if (!editor) return;
    const view = editor.view;

    const rebalancePages = () => {
      if (paginatingRef.current) return;
      paginatingRef.current = true;

      requestAnimationFrame(() => {
        const findPagePos = (doc: typeof view.state.doc, index: number) => {
          let found: number | null = null;
          let current = -1;
          doc.descendants((node, pos) => {
            if (node.type.name === "page") {
              current += 1;
              if (current === index) {
                found = pos;
                return false;
              }
            }
            return true;
          });
          return found;
        };

        const findOverflowOffset = (
          pagePos: number,
          pageNode: any,
          pageDom: HTMLElement,
        ) => {
          const pageRect = pageDom.getBoundingClientRect();
          let overflowOffset: number | null = null;

          pageNode.content.forEach((child: any, offset: number) => {
            if (overflowOffset !== null) return;
            const childPos = pagePos + 1 + offset;
            const childDom = view.nodeDOM(childPos) as HTMLElement | null;
            if (!childDom) return;
            const childRect = childDom.getBoundingClientRect();
            // Check if element bottom is past the visual page bottom
            if (childRect.bottom > pageRect.bottom - 1) {
              overflowOffset = offset;
            }
          });

          return overflowOffset;
        };

        try {
          const pages: { pos: number; node: any; dom: HTMLElement | null }[] =
            [];
          view.state.doc.descendants((node, pos) => {
            if (node.type.name === "page") {
              pages.push({
                pos,
                node,
                dom: view.nodeDOM(pos) as HTMLElement | null,
              });
            }
          });

          for (let i = 0; i < pages.length; i += 1) {
            const page = pages[i];
            const dom = page.dom;
            if (!dom) continue;
            const overflowOffset = findOverflowOffset(page.pos, page.node, dom);
            if (overflowOffset === null) continue;
            const overflowContent = page.node.content.cut(overflowOffset);

            let tr = view.state.tr;
            if (i === pages.length - 1) {
              const emptyParagraph = view.state.schema.nodes.paragraph.create();
              const newPage = view.state.schema.nodes.page.create(
                null,
                emptyParagraph,
              );
              tr = tr.insert(tr.doc.content.size + 1, newPage);
            }

            const from = tr.mapping.map(page.pos + 1 + overflowOffset);
            const to = tr.mapping.map(page.pos + page.node.nodeSize - 1);
            tr = tr.delete(from, to);

            const targetIndex = i + 1;
            const targetPos = findPagePos(tr.doc, targetIndex);
            if (targetPos !== null) {
              const targetNode = tr.doc.nodeAt(targetPos);
              const insertPos = targetNode
                ? targetPos + targetNode.nodeSize - 1
                : tr.doc.content.size;
              tr = tr.insert(insertPos, overflowContent);
            }
            view.dispatch(tr);
            paginatingRef.current = false;
            return;
          }
        } catch {
          paginatingRef.current = false;
          return;
        }

        paginatingRef.current = false;
      });
    };

    rebalancePages();
    editor.on("update", rebalancePages);
    return () => {
      editor.off("update", rebalancePages);
    };
  }, [editor, pageHeightPx, marginYPx]);

  const applyCssUpdates = (updates: Record<string, unknown>) => {
    const mapping: Record<string, keyof PaperSettings> = {
      "--col-count": "colCount",
      "--col-gap": "colGap",
      "--font-size": "fontSize",
      "--margin-x": "marginX",
      "--margin-y": "marginY",
    };

    const normalizeUnit = (value: unknown, unit: string) => {
      if (value === null || value === undefined) return "";
      const raw = String(value).trim();
      if (!raw) return "";
      if (/^[\d.]+$/.test(raw)) return `${raw}${unit}`;
      return raw;
    };

    setSettings((prev) => {
      const next = { ...prev };
      Object.entries(updates).forEach(([key, value]) => {
        const target = mapping[key];
        if (!target) return;
        if (target === "colCount") {
          const parsed = Number(value);
          next.colCount = parsed === 2 ? 2 : 1;
          return;
        }
        if (target === "fontSize") {
          next[target] = normalizeUnit(value, "pt") || prev.fontSize;
          return;
        }
        next[target] = normalizeUnit(value, "in") || prev[target];
      });
      return next;
    });
  };

  const findSectionRange = (label: string) => {
    if (!editor) return null;
    const lower = label.toLowerCase();
    let markNext = false;
    let range: { from: number; to: number } | null = null;
    editor.state.doc.descendants((node, pos) => {
      if (range) return false;
      if (node.type.name === "heading" || node.type.name === "paragraph") {
        const text = node.textContent.trim().toLowerCase();
        if (text === lower) {
          markNext = true;
          return false;
        }
        if (
          markNext &&
          node.type.name === "paragraph" &&
          node.textContent.trim()
        ) {
          range = { from: pos + 1, to: pos + node.nodeSize - 1 };
          return false;
        }
      }
      return true;
    });
    return range;
  };

  const applyEditorCommands = (
    commands: { target: string; action: string }[],
  ) => {
    if (!editor) return;
    commands.forEach((cmd) => {
      const action = cmd.action.toLowerCase();
      if (cmd.target.toLowerCase() === "abstract") {
        const range = findSectionRange("abstract");
        if (range) {
          editor.commands.setTextSelection(range);
        }
      }

      if (action === "togglebold") {
        editor.chain().focus().toggleBold().run();
      } else if (action === "toggleitalic") {
        editor.chain().focus().toggleItalic().run();
      } else if (action === "toggleheading1") {
        editor.chain().focus().toggleHeading({ level: 1 }).run();
      } else if (action === "toggleheading2") {
        editor.chain().focus().toggleHeading({ level: 2 }).run();
      }
    });
  };

  const submitQuickFix = async () => {
    if (!quickFixPrompt.trim() || quickFixLoading) return;
    setQuickFixStatus("Applying quick fix...");
    setQuickFixError(null);
    setQuickFixLoading(true);
    try {
      const response = await api.formatCommands({
        prompt: quickFixPrompt.trim(),
        settings: {
          "--col-count": settings.colCount,
          "--col-gap": settings.colGap,
          "--font-size": settings.fontSize,
          "--margin-x": settings.marginX,
          "--margin-y": settings.marginY,
        },
        available_targets: ["abstract", "title", "body", "selection"],
      });

      applyCssUpdates(response.cssUpdates ?? {});
      applyEditorCommands(response.editorCommands ?? []);
      setQuickFixStatus(`Applied via ${response.provider}`);
    } catch (error: unknown) {
      setQuickFixError(
        error instanceof Error ? error.message : "Quick fix failed",
      );
    } finally {
      setQuickFixLoading(false);
      setTimeout(() => setQuickFixStatus(null), 2000);
    }
  };

  const escapeLatex = (value: string) =>
    value
      .replace(/\\/g, "\\textbackslash{}")
      .replace(/([{}%&_#])/g, "\\$1")
      .replace(/\^/g, "\\textasciicircum{}")
      .replace(/~/g, "\\textasciitilde{}")
      .replace(/\$/g, "\\$");

  const renderTextNode = (node: any) => {
    const text = escapeLatex(node.text ?? "");
    const marks = node.marks ?? [];
    const isBold = marks.some((mark: any) => mark.type === "bold");
    const isItalic = marks.some((mark: any) => mark.type === "italic");
    if (isBold && isItalic) return `\\textbf{\\textit{${text}}}`;
    if (isBold) return `\\textbf{${text}}`;
    if (isItalic) return `\\textit{${text}}`;
    return text;
  };

  const renderNode = (node: any): string => {
    if (!node) return "";
    if (node.type === "text") return renderTextNode(node);
    if (node.type === "mathInline") return `$${node.attrs?.latex ?? ""}$`;
    if (node.type === "pageBreak") return "\\newpage";
    if (node.type === "hardBreak") return "\\\\";
    if (node.type === "page") {
      return (node.content ?? []).map(renderNode).filter(Boolean).join("\n\n");
    }

    if (node.type === "heading") {
      const level = node.attrs?.level ?? 1;
      const title = (node.content ?? []).map(renderNode).join("");
      if (level === 1) return `\\section{${title}}`;
      if (level === 2) return `\\subsection{${title}}`;
      return `\\subsubsection{${title}}`;
    }

    if (node.type === "paragraph") {
      const text = (node.content ?? []).map(renderNode).join("");
      return text ? `${text}\n` : "";
    }

    if (node.type === "bulletList") {
      const items = (node.content ?? [])
        .map((child: any) => renderNode(child))
        .filter(Boolean)
        .join("\n");
      return `\\begin{itemize}\n${items}\n\\end{itemize}`;
    }

    if (node.type === "orderedList") {
      const items = (node.content ?? [])
        .map((child: any) => renderNode(child))
        .filter(Boolean)
        .join("\n");
      return `\\begin{enumerate}\n${items}\n\\end{enumerate}`;
    }

    if (node.type === "listItem") {
      const content = (node.content ?? [])
        .map((child: any) => renderNode(child))
        .filter(Boolean)
        .join(" ")
        .trim();
      return content ? `\\item ${content}` : "";
    }

    return (node.content ?? []).map(renderNode).join("");
  };

  const buildLatex = () => {
    const doc = editor?.getJSON();
    const body = (doc?.content ?? [])
      .map(renderNode)
      .filter(Boolean)
      .join("\n\n");
    return [
      "\\documentclass[conference]{IEEEtran}",
      "\\usepackage{amsmath}",
      "\\usepackage{graphicx}",
      "\\begin{document}",
      body || "",
      "\\end{document}",
    ].join("\n\n");
  };

  const exportLatex = () => {
    if (!editor) return;
    setExportStatus(null);
    const latex = buildLatex();
    try {
      parse(latex);
      setExportStatus("LaTeX validated with latex.js");
    } catch {
      setExportStatus("LaTeX generated (validation skipped)");
    }

    const blob = new Blob([latex], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "universal_research_formatter.tex";
    a.click();
    URL.revokeObjectURL(url);
  };

  const importRawText = () => {
    if (!editor || !rawInput.trim()) return;
    const normalizeBlock = (block: string) => {
      const trimmed = block.trim();
      const match = trimmed.match(
        /^(TITLE|AUTHORS|PUBLICATION DATE|JOURNAL|ABSTRACT|KEYWORDS|INTRODUCTION|CONCLUSION|REFERENCES)\s*:\s*(.*)$/i,
      );
      if (match) {
        const label = match[1].toUpperCase();
        const rest = match[2]?.trim();
        const sectionAttr =
          label === "ABSTRACT"
            ? ' data-section="abstract"'
            : label === "KEYWORDS"
              ? ' data-section="keywords"'
              : "";
        const heading = `<h2${sectionAttr}>${label}</h2>`;
        if (rest) {
          return `${heading}<p>${rest}</p>`;
        }
        return heading;
      }

      const withMath = trimmed.replace(/\$([^$\n]+)\$/g, (_m, latex) => {
        const encoded = encodeURIComponent(latex.trim());
        return `<span data-math-inline="${encoded}"></span>`;
      });
      return `<p>${withMath.replace(/\n/g, "<br />")}</p>`;
    };

    const html = rawInput
      .trim()
      .split(/\n\s*\n/)
      .map(normalizeBlock)
      .join("");
    editor.commands.setContent(`<div data-page=\"true\">${html}</div>`);
  };

  const getFirstPagePos = () => {
    if (!editor) return null;
    let pagePos: number | null = null;
    editor.state.doc.descendants((node, pos) => {
      if (node.type.name === "page") {
        pagePos = pos;
        return false;
      }
      return true;
    });
    return pagePos;
  };

  const insertTitle = () => {
    if (!editor || !titleInput.trim()) return;
    const pagePos = getFirstPagePos();
    if (pagePos === null) return;
    editor.commands.insertContentAt(pagePos + 1, {
      type: "heading",
      attrs: { level: 1 },
      content: [{ type: "text", text: titleInput.trim() }],
    });
  };

  const insertHeading = () => {
    if (!editor || !headingInput.trim()) return;
    editor
      .chain()
      .focus()
      .insertContent({
        type: "heading",
        attrs: { level: 2 },
        content: [{ type: "text", text: headingInput.trim() }],
      })
      .run();
  };

  const applyIeeeHeadings = () => {
    if (!editor) return;
    const headings = new Set(
      [
        "abstract",
        "keywords",
        "introduction",
        "related work",
        "methodology",
        "methods",
        "results",
        "discussion",
        "conclusion",
        "references",
        "acknowledgment",
        "acknowledgement",
      ].map((item) => item.toLowerCase()),
    );

    const normalizeHeading = (text: string) => {
      const trimmed = text.trim();
      const withoutNumbering = trimmed.replace(/^\s*\d+(?:\.\d+)*\s+/, "");
      return withoutNumbering.replace(/[:.\s]+$/g, "").toLowerCase();
    };

    const looksLikeHeading = (text: string) => {
      const cleaned = text.trim();
      if (!cleaned) return false;
      if (headings.has(normalizeHeading(cleaned))) return true;
      if (/^\s*\d+(?:\.\d+)*\s+\w+/.test(cleaned)) return true;
      if (cleaned.length <= 40 && cleaned === cleaned.toUpperCase())
        return true;
      return /:$/.test(cleaned) && cleaned.length <= 45;
    };

    const transformNode = (node: any): any => {
      if (!node) return node;
      if (node.type === "paragraph") {
        const text = (node.content ?? [])
          .map((child: any) => child.text ?? "")
          .join("")
          .trim();
        if (looksLikeHeading(text)) {
          const normalized = normalizeHeading(text);
          const display = normalized
            ? normalized.replace(/\b\w/g, (m) => m.toUpperCase())
            : text.trim();
          return {
            type: "heading",
            attrs: { level: 2 },
            content: [{ type: "text", text: display }],
          };
        }
      }

      if (node.content) {
        return {
          ...node,
          content: node.content.map(transformNode),
        };
      }
      return node;
    };

    const doc = editor.getJSON();
    const updated = transformNode(doc);
    editor.commands.setContent(updated);
  };

  const applyIeeePreset = () => {
    setSettings({
      colCount: 2,
      colGap: "0.25in",
      fontSize: "10pt",
      marginX: "0.75in",
      marginY: "1in",
    });
  };

  return (
    <div className="space-y-6 px-2 md:px-4">
      <PageHeader
        title="Universal Research Formatter"
        subtitle="Live A4 preview editor with IEEE-style layout controls and AI quick fixes."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={exportLatex}
              className="rounded-lg border border-zinc-800 px-3 py-2 text-xs text-zinc-200 hover:bg-zinc-800"
            >
              Export LaTeX
            </button>
            <Badge tone="info">Phase 4</Badge>
          </div>
        }
      />

      <SectionCard
        title="Paste raw text"
        description="Paste your draft here to populate the live paper editor."
      >
        <div className="grid gap-3 md:grid-cols-[1fr_auto]">
          <textarea
            value={rawInput}
            onChange={(event) => setRawInput(event.target.value)}
            placeholder="Paste or type your raw draft text here..."
            className="min-h-[140px] w-full rounded-xl border border-zinc-800 bg-zinc-950 p-3 text-xs text-zinc-100"
          />
          <div className="flex flex-col gap-2">
            <button
              onClick={importRawText}
              className="rounded-lg bg-indigo-500 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-400"
            >
              Import into editor
            </button>
            <button
              onClick={() => {
                setRawInput("");
                editor?.commands.clearContent();
              }}
              className="rounded-lg border border-zinc-800 px-3 py-2 text-xs text-zinc-200 hover:bg-zinc-800"
            >
              Clear
            </button>
          </div>
        </div>
      </SectionCard>

      <SectionCard
        title="Title & headings"
        description="Insert a bold IEEE-style title or section heading."
      >
        <div className="grid gap-4 md:grid-cols-2">
          <label className="text-xs text-zinc-400">
            Paper title
            <div className="mt-2 flex gap-2">
              <input
                value={titleInput}
                onChange={(event) => setTitleInput(event.target.value)}
                placeholder="Enter paper title"
                className="flex-1 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
              />
              <button
                onClick={insertTitle}
                className="rounded-lg bg-indigo-500 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-400"
              >
                Insert title
              </button>
            </div>
          </label>
          <label className="text-xs text-zinc-400">
            Section heading
            <div className="mt-2 flex gap-2">
              <input
                value={headingInput}
                onChange={(event) => setHeadingInput(event.target.value)}
                placeholder="Enter section heading"
                className="flex-1 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
              />
              <button
                onClick={insertHeading}
                className="rounded-lg border border-zinc-800 px-3 py-2 text-xs text-zinc-200 hover:bg-zinc-800"
              >
                Insert heading
              </button>
            </div>
          </label>
        </div>
      </SectionCard>

      <SectionCard
        title="Layout controls"
        description="Adjust column layout, font size, and margins (IEEE-style defaults)."
      >
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <div className="text-xs text-zinc-500">
            Defaults align with IEEE conference layout.
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={applyIeeeHeadings}
              className="rounded-lg border border-zinc-800 px-3 py-1 text-xs text-zinc-200 hover:bg-zinc-800"
            >
              Apply IEEE headings
            </button>
            <button
              onClick={applyIeeePreset}
              className="rounded-lg border border-zinc-800 px-3 py-1 text-xs text-zinc-200 hover:bg-zinc-800"
            >
              Apply IEEE preset
            </button>
            <button
              onClick={() => setSettings(defaultSettings)}
              className="rounded-lg border border-zinc-800 px-3 py-1 text-xs text-zinc-200 hover:bg-zinc-800"
            >
              Reset layout
            </button>
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-5">
          <label className="text-xs text-zinc-400">
            Columns
            <select
              value={settings.colCount}
              onChange={(event) =>
                setSettings((prev) => ({
                  ...prev,
                  colCount: Number(event.target.value) as 1 | 2,
                }))
              }
              className="mt-2 w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
            >
              <option value={1}>1 Column</option>
              <option value={2}>2 Columns</option>
            </select>
          </label>
          <label className="text-xs text-zinc-400">
            Column gap
            <input
              value={settings.colGap}
              onChange={(event) =>
                setSettings((prev) => ({
                  ...prev,
                  colGap: event.target.value,
                }))
              }
              onBlur={(event) =>
                setSettings((prev) => ({
                  ...prev,
                  colGap: /^[\d.]+$/.test(event.target.value)
                    ? `${event.target.value}in`
                    : event.target.value,
                }))
              }
              className="mt-2 w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
              placeholder="0.25in"
            />
          </label>
          <label className="text-xs text-zinc-400">
            Font size
            <input
              value={settings.fontSize}
              onChange={(event) =>
                setSettings((prev) => ({
                  ...prev,
                  fontSize: event.target.value,
                }))
              }
              onBlur={(event) =>
                setSettings((prev) => ({
                  ...prev,
                  fontSize: /^[\d.]+$/.test(event.target.value)
                    ? `${event.target.value}pt`
                    : event.target.value,
                }))
              }
              className="mt-2 w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
              placeholder="11pt"
            />
          </label>
          <label className="text-xs text-zinc-400">
            Side margins
            <input
              value={settings.marginX}
              onChange={(event) =>
                setSettings((prev) => ({
                  ...prev,
                  marginX: event.target.value,
                }))
              }
              onBlur={(event) =>
                setSettings((prev) => ({
                  ...prev,
                  marginX: /^[\d.]+$/.test(event.target.value)
                    ? `${event.target.value}in`
                    : event.target.value,
                }))
              }
              className="mt-2 w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
              placeholder="0.75in"
            />
          </label>
          <label className="text-xs text-zinc-400">
            Top/bottom margins
            <input
              value={settings.marginY}
              onChange={(event) =>
                setSettings((prev) => ({
                  ...prev,
                  marginY: event.target.value,
                }))
              }
              onBlur={(event) =>
                setSettings((prev) => ({
                  ...prev,
                  marginY: /^[\d.]+$/.test(event.target.value)
                    ? `${event.target.value}in`
                    : event.target.value,
                }))
              }
              className="mt-2 w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
              placeholder="0.8in"
            />
          </label>
        </div>
      </SectionCard>

      <SectionCard
        title="Live paper"
        description="A4 preview with column flow. Content edits inside TipTap."
      >
        <div className="rounded-3xl border border-zinc-800 bg-zinc-900/40 p-4">
          <div className="paper-flow-wrapper" style={paperStyle}>
            <div className="paper-flow">
              <div className="paper-columns" ref={columnsRef}>
                {editor ? (
                  <EditorContent editor={editor} />
                ) : (
                  <div className="text-sm text-zinc-500">Loading editor...</div>
                )}
              </div>
            </div>
          </div>
        </div>
      </SectionCard>

      {exportStatus && (
        <div className="text-xs text-emerald-300">{exportStatus}</div>
      )}

      <div className="fixed bottom-6 right-6 z-50 w-[340px] rounded-2xl border border-zinc-800 bg-zinc-950/90 p-4 shadow-xl backdrop-blur">
        <div className="text-xs font-semibold text-zinc-200">Groq Copilot</div>
        <p className="mt-1 text-[11px] text-zinc-500">
          Quick layout fixes (e.g., “Make it 2 columns and bolder abstract.”)
        </p>
        <div className="mt-3 flex gap-2">
          <input
            value={quickFixPrompt}
            onChange={(event) => setQuickFixPrompt(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                submitQuickFix();
              }
            }}
            placeholder="Enter a layout command..."
            className="flex-1 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs text-zinc-100"
          />
          <button
            onClick={submitQuickFix}
            disabled={quickFixLoading || !quickFixPrompt.trim()}
            className="rounded-lg bg-indigo-500 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-400"
          >
            {quickFixLoading ? "Applying" : "Apply"}
          </button>
        </div>
        {quickFixStatus && (
          <div className="mt-2 text-[11px] text-emerald-300">
            {quickFixStatus}
          </div>
        )}
        {quickFixError && (
          <div className="mt-2 text-[11px] text-rose-400">{quickFixError}</div>
        )}
        <div className="mt-2 text-[10px] text-zinc-500">
          Requires GROQ_API_KEY on the backend.
        </div>
      </div>

      <style jsx>{`
        .paper-flow-wrapper {
          width: 100%;
          display: flex;
          justify-content: center;
          background: transparent;
          padding-bottom: 4rem;
        }
        .paper-flow {
          background: transparent;
          /* Width is handled by pages now */
          font-family: "Times New Roman", Times, serif;
        }
        .paper-columns {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 2rem;
        }
        .paper-columns :global(.ProseMirror) {
          outline: none;
          min-height: 100%;
          width: 100%;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 32px;
        }
        .paper-flow :global(.paper-page) {
          background: white;
          color: #0b0b0b;
          width: var(--page-width);
          height: var(--page-height-px);
          padding: var(--margin-y) var(--margin-x);
          box-shadow:
            0 4px 6px -1px rgba(0, 0, 0, 0.1),
            0 2px 4px -1px rgba(0, 0, 0, 0.06);
          border: 1px solid #e4e4e7;
          overflow: hidden;
          position: relative;

          /* Column logic applied inside the page */
          column-count: var(--col-count) !important;
          column-gap: var(--col-gap) !important;
          column-fill: auto;
        }
        .paper-flow :global(.paper-page p) {
          margin: 0 0 0.6em;
          line-height: 1.4;
          text-align: justify;
        }
        .paper-flow :global(.paper-page h1),
        .paper-flow :global(.paper-page h2),
        .paper-flow :global(.paper-page h3) {
          font-weight: 700;
          text-transform: uppercase;
          font-family: "Times New Roman", Times, serif;
          break-after: avoid;
        }
        .paper-flow :global(.paper-page h1) {
          font-size: 24pt;
          margin: 0 0 0.5em;
          text-align: center;
          column-span: all;
        }
        .paper-flow :global(.paper-page h1 + p),
        .paper-flow :global(.paper-page h1 + p + p) {
          text-align: center;
          font-size: 10pt;
          margin: 0 0 0.5em;
          column-span: all;
        }
        .paper-flow :global(.paper-page h2) {
          font-size: 12pt;
          margin: 1.2em 0 0.6em;
          text-align: center;
          border-bottom: 1px solid #000;
          padding-bottom: 2px;
        }
        .paper-flow :global(.paper-page h2[data-section="abstract"]),
        .paper-flow :global(.paper-page h2[data-section="keywords"]) {
          column-span: all;
          text-align: left;
          margin-top: 1em;
          font-style: italic;
          border: none;
        }
        .paper-flow :global(.paper-page .math-inline .katex) {
          font-size: 1em;
        }
        .paper-flow :global(.page-break) {
          break-after: page;
          height: 0;
          width: 0;
        }
      `}</style>
    </div>
  );
}

"use client";

import type { CSSProperties } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import Underline from "@tiptap/extension-underline";
import Subscript from "@tiptap/extension-subscript";
import Superscript from "@tiptap/extension-superscript";
import TextAlign from "@tiptap/extension-text-align";
import { Table } from "@tiptap/extension-table";
import { TableRow } from "@tiptap/extension-table-row";
import { TableCell } from "@tiptap/extension-table-cell";
import { TableHeader } from "@tiptap/extension-table-header";
import PageHeader from "@/components/PageHeader";
import SectionCard from "@/components/SectionCard";
import Badge from "@/components/Badge";
import { api } from "@/lib/api";
import { formatToIEEE, estimatePageCount } from "@/lib/ieee-formatter";

// IEEE Format Presets
type IEEEFormat = "conference" | "journal" | "transactions";

type FormatPreset = {
  name: string;
  description: string;
  colCount: 1 | 2;
  colGap: string;
  fontSize: string;
  marginX: string;
  marginY: string;
  titleSize: string;
  abstractStyle: "italic" | "normal";
};

const IEEE_PRESETS: Record<IEEEFormat, FormatPreset> = {
  conference: {
    name: "IEEE Conference",
    description:
      "Two-column format for conference papers (CVPR, NeurIPS, etc.)",
    colCount: 2,
    colGap: "0.25in",
    fontSize: "10pt",
    marginX: "0.75in",
    marginY: "0.75in",
    titleSize: "24pt",
    abstractStyle: "italic",
  },
  journal: {
    name: "IEEE Journal",
    description: "Two-column format for journal submissions",
    colCount: 2,
    colGap: "0.2in",
    fontSize: "10pt",
    marginX: "0.625in",
    marginY: "0.875in",
    titleSize: "22pt",
    abstractStyle: "normal",
  },
  transactions: {
    name: "IEEE Transactions",
    description: "Single-column for IEEE Transactions on...",
    colCount: 1,
    colGap: "0in",
    fontSize: "11pt",
    marginX: "1in",
    marginY: "1in",
    titleSize: "20pt",
    abstractStyle: "italic",
  },
};

type PaperSettings = {
  format: IEEEFormat;
  colCount: 1 | 2;
  colGap: string;
  fontSize: string;
  marginX: string;
  marginY: string;
  titleSize: string;
  abstractStyle: "italic" | "normal";
};

// Context Menu State
type ContextMenuState = {
  visible: boolean;
  x: number;
  y: number;
};

export default function UniversalResearchFormatterPage() {
  const [settings, setSettings] = useState<PaperSettings>({
    format: "conference",
    ...IEEE_PRESETS.conference,
  });
  const [rawInput, setRawInput] = useState<string>("");
  const [isFormatting, setIsFormatting] = useState(false);
  const [formatStatus, setFormatStatus] = useState<string | null>(null);
  const [formatError, setFormatError] = useState<string | null>(null);
  const [exportStatus, setExportStatus] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [pageCount, setPageCount] = useState(1);
  const [contextMenu, setContextMenu] = useState<ContextMenuState>({
    visible: false,
    x: 0,
    y: 0,
  });

  // Live preview state
  const [livePreviewHtml, setLivePreviewHtml] = useState<string>("");
  const [isPreviewUpdating, setIsPreviewUpdating] = useState(false);
  const previewDebounceRef = useRef<NodeJS.Timeout | null>(null);

  const editorRef = useRef<HTMLDivElement>(null);
  const pagesContainerRef = useRef<HTMLDivElement>(null);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: { levels: [1, 2, 3, 4] },
      }),
      Placeholder.configure({
        placeholder:
          "Paste your raw text and click 'Format with AI' to auto-structure to IEEE format...",
      }),
      Underline,
      Subscript,
      Superscript,
      TextAlign.configure({
        types: ["heading", "paragraph"],
      }),
      Table.configure({
        resizable: true,
      }),
      TableRow,
      TableCell,
      TableHeader,
    ],
    immediatelyRender: false,
    content: "",
  });

  // Apply format preset
  const applyPreset = (format: IEEEFormat) => {
    const preset = IEEE_PRESETS[format];
    setSettings({
      format,
      ...preset,
    });
  };

  // Paper styles
  const paperStyle = useMemo(
    () =>
      ({
        "--col-count": String(settings.colCount),
        "--col-gap": settings.colGap,
        "--font-size": settings.fontSize,
        "--margin-x": settings.marginX,
        "--margin-y": settings.marginY,
        "--title-size": settings.titleSize,
      }) as CSSProperties,
    [settings],
  );

  // Context Menu Handler
  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setContextMenu({
      visible: true,
      x: e.clientX,
      y: e.clientY,
    });
  }, []);

  // Close context menu on click elsewhere
  useEffect(() => {
    const handleClick = () =>
      setContextMenu((prev) => ({ ...prev, visible: false }));
    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, []);

  // Live preview: Update IEEE-formatted preview when editor content changes (debounced)
  useEffect(() => {
    if (!editor) return;

    const updatePreview = () => {
      // Clear any existing timeout
      if (previewDebounceRef.current) {
        clearTimeout(previewDebounceRef.current);
      }

      setIsPreviewUpdating(true);

      // Debounce: Wait 1.5 seconds after user stops typing
      previewDebounceRef.current = setTimeout(() => {
        const html = editor.getHTML();
        setLivePreviewHtml(html);
        setIsPreviewUpdating(false);

        // Also update page count estimate
        const text = editor.getText();
        const estimated = estimatePageCount(text, settings.colCount);
        setPageCount(estimated);
      }, 1500);
    };

    // Listen to editor updates
    editor.on("update", updatePreview);

    // Initial preview
    const initialHtml = editor.getHTML();
    if (initialHtml && initialHtml !== "<p></p>") {
      setLivePreviewHtml(initialHtml);
    }

    return () => {
      editor.off("update", updatePreview);
      if (previewDebounceRef.current) {
        clearTimeout(previewDebounceRef.current);
      }
    };
  }, [editor, settings.colCount]);

  // Context menu actions
  const contextMenuActions = [
    {
      label: "Bold",
      shortcut: "Ctrl+B",
      action: () => editor?.chain().focus().toggleBold().run(),
    },
    {
      label: "Italic",
      shortcut: "Ctrl+I",
      action: () => editor?.chain().focus().toggleItalic().run(),
    },
    {
      label: "Underline",
      shortcut: "Ctrl+U",
      action: () => editor?.chain().focus().toggleUnderline().run(),
    },
    { type: "divider" as const },
    {
      label: "Heading 1 (Section)",
      shortcut: "Ctrl+1",
      action: () => editor?.chain().focus().toggleHeading({ level: 1 }).run(),
    },
    {
      label: "Heading 2 (Subsection)",
      shortcut: "Ctrl+2",
      action: () => editor?.chain().focus().toggleHeading({ level: 2 }).run(),
    },
    {
      label: "Heading 3",
      shortcut: "Ctrl+3",
      action: () => editor?.chain().focus().toggleHeading({ level: 3 }).run(),
    },
    { type: "divider" as const },
    {
      label: "Subscript",
      shortcut: "",
      action: () => editor?.chain().focus().toggleSubscript().run(),
    },
    {
      label: "Superscript",
      shortcut: "",
      action: () => editor?.chain().focus().toggleSuperscript().run(),
    },
    { type: "divider" as const },
    {
      label: "Align Left",
      shortcut: "",
      action: () => editor?.chain().focus().setTextAlign("left").run(),
    },
    {
      label: "Align Center",
      shortcut: "",
      action: () => editor?.chain().focus().setTextAlign("center").run(),
    },
    {
      label: "Align Justify",
      shortcut: "",
      action: () => editor?.chain().focus().setTextAlign("justify").run(),
    },
  ];

  // Deterministic Format Handler (consistent every time)
  const handleFormat = () => {
    if (!rawInput.trim() || isFormatting) return;

    setIsFormatting(true);
    setFormatStatus("Formatting to IEEE standard...");
    setFormatError(null);

    try {
      // Use deterministic local formatter
      const result = formatToIEEE(rawInput.trim());

      console.log("Format result:", {
        sectionCount: result.sectionCount,
        tableCount: result.tableCount,
        equationCount: result.equationCount,
      });

      if (result.html) {
        editor?.commands.setContent(result.html);

        // Auto-calculate page count based on content
        const estimatedPages = estimatePageCount(
          result.html,
          settings.colCount,
        );
        setPageCount(estimatedPages);

        setFormatStatus(
          `Formatted: ${result.sectionCount} sections, ${result.tableCount} tables, ${result.equationCount} equations → ${estimatedPages} page(s)`,
        );
        setRawInput(""); // Clear input after successful format
      } else {
        throw new Error("No content generated");
      }
    } catch (error) {
      console.error("Format error:", error);
      setFormatError(
        error instanceof Error ? error.message : "Formatting failed",
      );
      // Fallback: basic import
      const html = rawInput
        .trim()
        .split(/\n\s*\n/)
        .map((block) => `<p>${block.replace(/\n/g, "<br />")}</p>`)
        .join("");
      editor?.commands.setContent(html);
      setFormatStatus("Used basic formatting");
    } finally {
      setIsFormatting(false);
      setTimeout(() => setFormatStatus(null), 5000);
    }
  };

  // Optional: AI-enhanced formatting (for users who want AI suggestions)
  const handleAIFormat = async () => {
    if (!rawInput.trim() || isFormatting) return;

    setIsFormatting(true);
    setFormatStatus("Enhancing with AI...");
    setFormatError(null);

    try {
      const response = await api.formatIEEE({
        raw_text: rawInput.trim(),
        format_type: settings.format,
        detect_equations: true,
        detect_references: true,
      });

      if (response.success && response.formatted_html) {
        editor?.commands.setContent(response.formatted_html);
        const estimatedPages = estimatePageCount(
          response.formatted_html,
          settings.colCount,
        );
        setPageCount(estimatedPages);
        setFormatStatus(
          `AI formatted (${response.sections_detected} sections) → ${estimatedPages} page(s)`,
        );
        setRawInput("");
      } else {
        throw new Error(response.error || "AI formatting failed");
      }
    } catch (error) {
      console.error("AI Format error:", error);
      // Fall back to deterministic formatter
      handleFormat();
    } finally {
      setIsFormatting(false);
      setTimeout(() => setFormatStatus(null), 5000);
    }
  };

  // LaTeX Builder
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
    const isSubscript = marks.some((mark: any) => mark.type === "subscript");
    const isSuperscript = marks.some(
      (mark: any) => mark.type === "superscript",
    );
    const isUnderline = marks.some((mark: any) => mark.type === "underline");

    let result = text;
    if (isSubscript) result = `\\textsubscript{${result}}`;
    if (isSuperscript) result = `\\textsuperscript{${result}}`;
    if (isUnderline) result = `\\underline{${result}}`;
    if (isBold && isItalic) return `\\textbf{\\textit{${result}}}`;
    if (isBold) return `\\textbf{${result}}`;
    if (isItalic) return `\\textit{${result}}`;
    return result;
  };

  const renderNode = (node: any): string => {
    if (!node) return "";
    if (node.type === "text") return renderTextNode(node);
    if (node.type === "hardBreak") return "\\\\";

    if (node.type === "heading") {
      const level = node.attrs?.level ?? 1;
      const title = (node.content ?? []).map(renderNode).join("");
      if (level === 1) return `\\section{${title}}`;
      if (level === 2) return `\\subsection{${title}}`;
      if (level === 3) return `\\subsubsection{${title}}`;
      return `\\paragraph{${title}}`;
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

  const getDocumentClass = () => {
    switch (settings.format) {
      case "conference":
        return "\\documentclass[conference]{IEEEtran}";
      case "journal":
        return "\\documentclass[journal]{IEEEtran}";
      case "transactions":
        return "\\documentclass[10pt,journal,compsoc]{IEEEtran}";
      default:
        return "\\documentclass[conference]{IEEEtran}";
    }
  };

  const buildLatex = () => {
    const doc = editor?.getJSON();
    const body = (doc?.content ?? [])
      .map(renderNode)
      .filter(Boolean)
      .join("\n\n");

    return [
      getDocumentClass(),
      "\\usepackage{amsmath,amssymb,amsfonts}",
      "\\usepackage{algorithmic}",
      "\\usepackage{graphicx}",
      "\\usepackage{textcomp}",
      "\\usepackage{xcolor}",
      "\\usepackage{cite}",
      "\\usepackage{hyperref}",
      "",
      "\\begin{document}",
      "",
      body || "",
      "",
      "\\end{document}",
    ].join("\n");
  };

  // Export LaTeX
  const exportLatex = () => {
    if (!editor) return;
    const latex = buildLatex();

    const blob = new Blob([latex], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `research_paper_${settings.format}.tex`;
    a.click();
    URL.revokeObjectURL(url);
    setExportStatus("LaTeX exported successfully!");
    setTimeout(() => setExportStatus(null), 3000);
  };

  // Export PDF via server-side compilation (with browser fallback)
  const exportPDF = async () => {
    if (!editor || isExporting) return;

    setIsExporting(true);
    setExportStatus("Compiling PDF with LaTeX...");

    try {
      const latex = buildLatex();
      const response = await api.compilePDF({ latex_code: latex });

      if (response.success && response.pdf_base64) {
        // Decode base64 and download
        const byteCharacters = atob(response.pdf_base64);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
          byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        const blob = new Blob([byteArray], { type: "application/pdf" });

        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `research_paper_${settings.format}.pdf`;
        a.click();
        URL.revokeObjectURL(url);

        setExportStatus("PDF exported successfully!");
      } else {
        // Fallback: Use browser print if pdflatex not available
        if (response.error?.includes("pdflatex not found")) {
          setExportStatus("pdflatex not found. Opening browser print dialog...");
          setTimeout(() => {
            exportPDFViaBrowser();
          }, 1000);
        } else {
          throw new Error(response.error || "PDF compilation failed");
        }
      }
    } catch (error) {
      setExportStatus(
        `PDF export failed: ${error instanceof Error ? error.message : "Unknown error"}. Using browser print as fallback...`,
      );
      // Fallback to browser print
      setTimeout(() => {
        exportPDFViaBrowser();
      }, 1500);
    } finally {
      setIsExporting(false);
      setTimeout(() => setExportStatus(null), 5000);
    }
  };

  // Browser-based PDF export fallback
  const exportPDFViaBrowser = () => {
    if (!editor) return;

    const content = editor.getHTML();

    // Create a new window for printing
    const printWindow = window.open("", "_blank");
    if (!printWindow) {
      setExportStatus("Pop-up blocked. Please allow pop-ups for PDF export.");
      return;
    }

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>Research Paper - IEEE Format</title>
        <style>
          @page {
            size: A4;
            margin: 19mm 17mm 25mm 17mm;
          }
          body {
            font-family: "Times New Roman", Times, serif;
            font-size: 10pt;
            line-height: 1.4;
            column-count: 2;
            column-gap: 6mm;
            text-align: justify;
            hyphens: auto;
            margin: 0;
            padding: 0;
          }
          h1 {
            column-span: all;
            text-align: center;
            font-size: 24pt;
            font-weight: normal;
            margin-bottom: 1em;
          }
          h2 {
            font-size: 10pt;
            font-weight: bold;
            text-transform: uppercase;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
          }
          h3 {
            font-size: 10pt;
            font-style: italic;
            font-weight: normal;
            margin-top: 1em;
            margin-bottom: 0.5em;
          }
          p {
            text-indent: 0.5em;
            margin: 0.5em 0;
          }
          p:first-of-type {
            text-indent: 0;
          }
          table {
            width: 100%;
            border-collapse: collapse;
            font-size: 9pt;
            margin: 1em 0;
          }
          th, td {
            border: 1px solid #333;
            padding: 4px 8px;
            text-align: left;
          }
          th {
            background: #f0f0f0;
            font-weight: bold;
          }
          sub, sup {
            font-size: 0.75em;
          }
          @media print {
            body {
              -webkit-print-color-adjust: exact;
              print-color-adjust: exact;
            }
          }
        </style>
      </head>
      <body>
        ${content}
      </body>
      </html>
    `);

    printWindow.document.close();

    // Wait for content to load, then trigger print
    setTimeout(() => {
      printWindow.print();
      setExportStatus("Print dialog opened. Save as PDF to complete export.");
    }, 500);
  };

  return (
    <div className="space-y-3 px-2 md:px-4 pb-16">
      <PageHeader
        title="Universal Research Formatter"
        subtitle="AI-powered IEEE formatting with live preview, multiple format presets, and export options."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={exportLatex}
              className="rounded-lg border border-zinc-700 bg-zinc-800/50 px-3 py-2 text-xs text-zinc-200 hover:bg-zinc-700 transition-colors"
            >
              Export LaTeX
            </button>
            <button
              onClick={exportPDF}
              disabled={isExporting}
              className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-500 transition-colors disabled:opacity-50"
            >
              {isExporting ? "Compiling..." : "Export PDF"}
            </button>
            <Badge tone="info">v2.0</Badge>
          </div>
        }
      />

      {/* IEEE Format Selector */}
      <SectionCard
        title="IEEE Format Preset"
        description="Select the IEEE format standard for your paper."
      >
        <div className="grid gap-2 md:grid-cols-3">
          {(Object.entries(IEEE_PRESETS) as [IEEEFormat, FormatPreset][]).map(
            ([key, preset]) => (
              <button
                key={key}
                onClick={() => applyPreset(key)}
                className={`rounded-lg border p-3 text-left transition-all ${settings.format === key
                  ? "border-indigo-500 bg-indigo-500/10 ring-1 ring-indigo-500"
                  : "border-zinc-800 bg-zinc-900/50 hover:border-zinc-700"
                  }`}
              >
                <div className="flex items-center gap-2">
                  <div
                    className={`h-3 w-3 rounded-full ${settings.format === key ? "bg-indigo-500" : "bg-zinc-700"
                      }`}
                  />
                  <span className="font-semibold text-sm text-zinc-100">
                    {preset.name}
                  </span>
                </div>
                <p className="mt-1 text-xs text-zinc-500">
                  {preset.description}
                </p>
                <div className="mt-2 flex gap-2">
                  <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-400">
                    {preset.colCount} col
                  </span>
                  <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-400">
                    {preset.fontSize}
                  </span>
                </div>
              </button>
            ),
          )}
        </div>
      </SectionCard>

      {/* Raw Input + AI Format */}
      <SectionCard
        title="Raw Text Input"
        description="Paste your raw research content. AI will auto-detect sections, equations, and references."
      >
        <div className="space-y-2">
          <textarea
            value={rawInput}
            onChange={(e) => setRawInput(e.target.value)}
            placeholder={`Paste your raw research paper here...

Example:
TITLE: Your Paper Title
AUTHORS: Name1, Name2

ABSTRACT
Your abstract text here...

1. INTRODUCTION
Introduction content...

2. METHODOLOGY
...`}
            className="min-h-[120px] w-full rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-sm text-zinc-100 font-mono placeholder:text-zinc-600 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
          <div className="flex flex-wrap items-center gap-3">
            {/* Primary: Deterministic formatter (consistent) */}
            <button
              onClick={handleFormat}
              disabled={isFormatting || !rawInput.trim()}
              className="rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 px-4 py-2.5 text-sm font-semibold text-white hover:from-emerald-500 hover:to-teal-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isFormatting ? (
                <>
                  <span className="animate-spin">⚙️</span>
                  Formatting...
                </>
              ) : (
                <>📄 Format to IEEE</>
              )}
            </button>
            {/* Secondary: AI formatter (may vary) */}
            <button
              onClick={handleAIFormat}
              disabled={isFormatting || !rawInput.trim()}
              className="rounded-lg border border-indigo-600 bg-indigo-600/10 px-3 py-2 text-xs text-indigo-300 hover:bg-indigo-600/20 transition-colors disabled:opacity-50"
            >
              ✨ AI Enhance
            </button>
            <button
              onClick={() => {
                setRawInput("");
                editor?.commands.clearContent();
                setPageCount(1);
              }}
              className="rounded-lg border border-zinc-800 px-3 py-2 text-xs text-zinc-400 hover:bg-zinc-800 transition-colors"
            >
              Clear All
            </button>
          </div>
          {formatStatus && (
            <div className="text-xs text-emerald-400 flex items-center gap-1">
              <span>✓</span> {formatStatus}
            </div>
          )}
          {formatError && (
            <div className="text-xs text-amber-400 flex items-center gap-1">
              <span>⚠</span> {formatError}
            </div>
          )}
        </div>
      </SectionCard>

      {/* Formatting Toolbar */}
      <SectionCard
        title="Formatting Tools"
        description="Click buttons or right-click in the editor for more options."
      >
        <div className="flex flex-wrap gap-1">
          <button
            onClick={() => editor?.chain().focus().toggleBold().run()}
            className={`rounded px-3 py-1.5 text-xs font-bold transition-colors ${editor?.isActive("bold")
              ? "bg-indigo-600 text-white"
              : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
              }`}
          >
            B
          </button>
          <button
            onClick={() => editor?.chain().focus().toggleItalic().run()}
            className={`rounded px-3 py-1.5 text-xs italic transition-colors ${editor?.isActive("italic")
              ? "bg-indigo-600 text-white"
              : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
              }`}
          >
            I
          </button>
          <button
            onClick={() => editor?.chain().focus().toggleUnderline().run()}
            className={`rounded px-3 py-1.5 text-xs underline transition-colors ${editor?.isActive("underline")
              ? "bg-indigo-600 text-white"
              : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
              }`}
          >
            U
          </button>
          <div className="w-px bg-zinc-700 mx-1" />
          <button
            onClick={() =>
              editor?.chain().focus().toggleHeading({ level: 1 }).run()
            }
            className={`rounded px-2 py-1.5 text-xs transition-colors ${editor?.isActive("heading", { level: 1 })
              ? "bg-indigo-600 text-white"
              : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
              }`}
          >
            H1
          </button>
          <button
            onClick={() =>
              editor?.chain().focus().toggleHeading({ level: 2 }).run()
            }
            className={`rounded px-2 py-1.5 text-xs transition-colors ${editor?.isActive("heading", { level: 2 })
              ? "bg-indigo-600 text-white"
              : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
              }`}
          >
            H2
          </button>
          <button
            onClick={() =>
              editor?.chain().focus().toggleHeading({ level: 3 }).run()
            }
            className={`rounded px-2 py-1.5 text-xs transition-colors ${editor?.isActive("heading", { level: 3 })
              ? "bg-indigo-600 text-white"
              : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
              }`}
          >
            H3
          </button>
          <div className="w-px bg-zinc-700 mx-1" />
          <button
            onClick={() => editor?.chain().focus().toggleBulletList().run()}
            className={`rounded px-2 py-1.5 text-xs transition-colors ${editor?.isActive("bulletList")
              ? "bg-indigo-600 text-white"
              : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
              }`}
          >
            • List
          </button>
          <button
            onClick={() => editor?.chain().focus().toggleOrderedList().run()}
            className={`rounded px-2 py-1.5 text-xs transition-colors ${editor?.isActive("orderedList")
              ? "bg-indigo-600 text-white"
              : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
              }`}
          >
            1. List
          </button>
          <div className="w-px bg-zinc-700 mx-1" />
          <button
            onClick={() => editor?.chain().focus().toggleSubscript().run()}
            className={`rounded px-2 py-1.5 text-xs transition-colors ${editor?.isActive("subscript")
              ? "bg-indigo-600 text-white"
              : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
              }`}
          >
            X₂
          </button>
          <button
            onClick={() => editor?.chain().focus().toggleSuperscript().run()}
            className={`rounded px-2 py-1.5 text-xs transition-colors ${editor?.isActive("superscript")
              ? "bg-indigo-600 text-white"
              : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
              }`}
          >
            X²
          </button>
          <div className="w-px bg-zinc-700 mx-1" />
          <button
            onClick={() => editor?.chain().focus().setTextAlign("left").run()}
            className="rounded px-2 py-1.5 text-xs bg-zinc-800 text-zinc-300 hover:bg-zinc-700 transition-colors"
          >
            ⬅
          </button>
          <button
            onClick={() => editor?.chain().focus().setTextAlign("center").run()}
            className="rounded px-2 py-1.5 text-xs bg-zinc-800 text-zinc-300 hover:bg-zinc-700 transition-colors"
          >
            ⬌
          </button>
          <button
            onClick={() =>
              editor?.chain().focus().setTextAlign("justify").run()
            }
            className="rounded px-2 py-1.5 text-xs bg-zinc-800 text-zinc-300 hover:bg-zinc-700 transition-colors"
          >
            ≡
          </button>
        </div>
      </SectionCard>

      {/* Side-by-Side Preview: HTML Editor + LaTeX/PDF Preview */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Left Panel: Simple Editable HTML Editor */}
        <SectionCard
          title="📝 Content Editor"
          description="Write and edit your research paper content here"
        >
          <div
            ref={pagesContainerRef}
            className="overflow-auto rounded-2xl border border-zinc-800 bg-white"
            style={{ maxHeight: "75vh", minHeight: "500px" }}
          >
            {/* Clean Editor Area */}
            <div
              ref={editorRef}
              onContextMenu={handleContextMenu}
              className="max-w-none p-6"
              style={{
                fontFamily: '"Times New Roman", Times, serif',
                fontSize: "12pt",
                lineHeight: 1.6,
                color: "#1a1a1a",
                fontStyle: "normal",
              }}
            >
              {editor ? (
                <EditorContent editor={editor} className="focus:outline-none editor-content" />
              ) : (
                <div className="text-zinc-500 animate-pulse p-4">
                  Loading editor...
                </div>
              )}
            </div>
          </div>

          {/* Word count indicator */}
          <div className="flex justify-between items-center mt-3 px-2">
            <span className="text-[11px] text-zinc-500">
              {editor?.getText().split(/\s+/).filter(w => w.length > 0).length || 0} words
            </span>
            <span className="text-[11px] text-zinc-400">
              Edit freely • IEEE formatting applies to LaTeX preview →
            </span>
          </div>
        </SectionCard>

        {/* Right Panel: Live IEEE Preview */}
        <SectionCard
          title={`📄 IEEE Preview ${isPreviewUpdating ? "(Updating...)" : ""}`}
          description="A4 · 2-column · Live preview"
        >
          <div
            className="overflow-auto rounded-2xl border border-zinc-800 bg-zinc-900 p-4"
            style={{ maxHeight: "75vh", minHeight: "500px" }}
          >
            {/* Live A4 Page with IEEE format */}
            <div className="flex flex-col items-center gap-4">
              {/* Updating indicator */}
              {isPreviewUpdating && (
                <div className="flex items-center gap-2 text-xs text-amber-400 mb-2">
                  <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></div>
                  <span>Updating preview...</span>
                </div>
              )}

              {/* A4 Page */}
              <div
                className="relative bg-white shadow-[0_4px_25px_rgba(0,0,0,0.4)] transition-all duration-300 rounded"
                style={{
                  width: "100%",
                  maxWidth: "600px",
                }}
              >
                {/* IEEE Content Area */}
                <div
                  className="ieee-preview-content"
                  style={{
                    fontFamily: '"Times New Roman", Times, serif',
                    fontSize: "9pt",
                    lineHeight: 1.4,
                    padding: "20px",
                    columnCount: settings.colCount,
                    columnGap: "20px",
                    columnFill: "balance",
                    textAlign: "justify",
                    hyphens: "auto",
                    wordBreak: "break-word",
                    color: "#000",
                    minHeight: "600px",
                  }}
                >
                  {livePreviewHtml ? (
                    <div
                      dangerouslySetInnerHTML={{ __html: livePreviewHtml }}
                      className="ieee-preview-html"
                    />
                  ) : (
                    <div className="text-zinc-400 text-center py-20 text-[10pt]" style={{ columnSpan: "all" }}>
                      <div className="text-3xl mb-2 opacity-30">📝</div>
                      <p>Start typing in the editor</p>
                      <p className="text-[8pt] mt-1 opacity-70">Preview updates automatically</p>
                    </div>
                  )}
                </div>

                {/* Format badge */}
                <div className="absolute top-2 right-2 bg-blue-600 text-white px-1.5 py-0.5 rounded text-[8px] font-medium shadow-sm">
                  IEEE
                </div>

                {/* Updating overlay */}
                {isPreviewUpdating && (
                  <div className="absolute inset-0 bg-white/50 flex items-center justify-center rounded">
                    <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                  </div>
                )}
              </div>

              {/* Page count indicator */}
              {pageCount > 1 && (
                <div className="text-[10px] text-zinc-400">
                  Estimated: {pageCount} pages
                </div>
              )}
            </div>

            {/* Format specs */}
            <div className="mt-4 p-3 bg-zinc-800/80 rounded-xl border border-zinc-700">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] text-zinc-400 font-medium">IEEE Format Specs</span>
                <div className="flex items-center gap-1">
                  <div className={`w-1.5 h-1.5 rounded-full ${isPreviewUpdating ? "bg-amber-400 animate-pulse" : "bg-emerald-500"}`}></div>
                  <span className="text-[9px] text-zinc-500">
                    {isPreviewUpdating ? "Syncing" : "Live"}
                  </span>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2 text-[9px]">
                <div className="flex items-center gap-1.5">
                  <span className="text-zinc-500">Page:</span>
                  <span className="text-zinc-300">A4</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-zinc-500">Columns:</span>
                  <span className="text-zinc-300">{settings.colCount}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-zinc-500">Font:</span>
                  <span className="text-zinc-300">10pt Times</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-zinc-500">Words:</span>
                  <span className="text-zinc-300">
                    {editor?.getText().split(/\s+/).filter(w => w.length > 0).length || 0}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </SectionCard>
      </div>

      {/* Export Status */}
      {exportStatus && (
        <div
          className={`fixed bottom-20 left-1/2 -translate-x-1/2 rounded-xl px-4 py-2 text-sm font-medium shadow-lg ${exportStatus.includes("failed")
            ? "bg-red-900/90 text-red-100"
            : "bg-emerald-900/90 text-emerald-100"
            }`}
        >
          {exportStatus}
        </div>
      )}

      {/* Context Menu */}
      {contextMenu.visible && (
        <div
          className="fixed z-50 min-w-[180px] rounded-xl border border-zinc-700 bg-zinc-900/95 py-1 shadow-2xl backdrop-blur"
          style={{ left: contextMenu.x, top: contextMenu.y }}
        >
          {contextMenuActions.map((item, index) =>
            item.type === "divider" ? (
              <div key={index} className="my-1 border-t border-zinc-800" />
            ) : (
              <button
                key={index}
                onClick={() => {
                  item.action?.();
                  setContextMenu((prev) => ({ ...prev, visible: false }));
                }}
                className="flex w-full items-center justify-between px-3 py-1.5 text-xs text-zinc-300 hover:bg-zinc-800"
              >
                <span>{item.label}</span>
                {item.shortcut && (
                  <span className="text-[10px] text-zinc-500">
                    {item.shortcut}
                  </span>
                )}
              </button>
            ),
          )}
        </div>
      )}

      {/* Floating AI Assistant */}
      <div className="fixed bottom-6 right-6 z-40 w-[320px] rounded-2xl border border-zinc-800 bg-zinc-950/95 p-4 shadow-2xl backdrop-blur">
        <div className="flex items-center gap-2">
          <span className="text-lg">🤖</span>
          <span className="text-xs font-semibold text-zinc-200">
            AI Copilot
          </span>
        </div>
        <p className="mt-1 text-[11px] text-zinc-500">
          Quick commands: "Add abstract section", "Fix citation format", "Make
          title bold"
        </p>
        <div className="mt-3 flex gap-2">
          <input
            placeholder="Type a command..."
            className="flex-1 rounded-lg border border-zinc-800 bg-zinc-900/50 px-3 py-2 text-xs text-zinc-100 placeholder:text-zinc-600 focus:border-indigo-500 focus:outline-none"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                // TODO: Handle AI command
                console.log("AI command:", e.currentTarget.value);
              }
            }}
          />
          <button className="rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-500 transition-colors">
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

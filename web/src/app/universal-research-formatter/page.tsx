"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import Underline from "@tiptap/extension-underline";
import Subscript from "@tiptap/extension-subscript";
import Superscript from "@tiptap/extension-superscript";
import TextAlign from "@tiptap/extension-text-align";
import Image from "@tiptap/extension-image";
import { Table } from "@tiptap/extension-table";
import { TableRow } from "@tiptap/extension-table-row";
import { TableCell } from "@tiptap/extension-table-cell";
import { TableHeader } from "@tiptap/extension-table-header";
import PageHeader from "@/components/PageHeader";
import SectionCard from "@/components/SectionCard";
import Badge from "@/components/Badge";
import TableInsertDialog from "@/components/TableInsertDialog";
import EquationEditor from "@/components/EquationEditor";
import { api } from "@/lib/api";
import { estimatePageCount } from "@/lib/ieee-formatter";
import { parseDocument } from "@/lib/parser/document-parser";
import { formatToIEEE } from "@/lib/formatters/ieee";
import { formatToACM } from "@/lib/formatters/acm";
import { formatToSpringer } from "@/lib/formatters/springer";
import type { FormatOptions } from "@/lib/formatters/ieee";
import {
  IeeeContainer,
  IeeeHeading,
  IeeeParagraph,
} from "@/lib/tiptap/ieee-nodes";

// Document Format Presets — all supported templates
type DocumentFormat =
  | "conference"
  | "journal"
  | "transactions"
  | "acm-sigconf"
  | "springer-lncs";

type FormatFamily = "ieee" | "acm" | "springer";

type FormatPreset = {
  name: string;
  family: FormatFamily;
  description: string;
  paperSize: "a4" | "letter";
  colCount: 1 | 2;
  colGap: string;
  fontFamily: string;
  fontSize: string;
  titleFontFamily: string;
  titleSize: string;
  titleWeight: "normal" | "bold";
  marginX: string;
  marginTop: string;
  marginBottom: string;
  abstractStyle: "italic" | "normal" | "bold";
  abstractInset: string;
  headingNumbering: "roman" | "arabic";
  bodyLineHeight: string;
  paragraphIndent: string;
  captionSize: string;
  referenceSize: string;
  enabled: boolean;
};

const FORMAT_PRESETS: Record<DocumentFormat, FormatPreset> = {
  conference: {
    name: "IEEE Conference",
    family: "ieee",
    description: "Conference-template-A4: 2-col, 10pt, Roman-numeral headings, 24pt title",
    paperSize: "a4",
    colCount: 2,
    colGap: "0.17in",
    fontFamily: '"Times New Roman", Times, serif',
    fontSize: "10pt",
    titleFontFamily: '"Times New Roman", Times, serif',
    titleSize: "24pt",
    titleWeight: "normal",
    marginX: "0.56in",
    marginTop: "0.75in",
    marginBottom: "1.69in",
    abstractStyle: "normal",
    abstractInset: "0",
    headingNumbering: "roman",
    bodyLineHeight: "1.14",
    paragraphIndent: "14.4pt",
    captionSize: "8pt",
    referenceSize: "8pt",
    enabled: true,
  },
  journal: {
    name: "IEEE Journal",
    family: "ieee",
    description: "US-Letter, 2-col, 26pt title, bold abstract, 0.25in column gap",
    paperSize: "letter",
    colCount: 2,
    colGap: "0.25in",
    fontFamily: '"Times New Roman", Times, serif',
    fontSize: "10pt",
    titleFontFamily: '"Times New Roman", Times, serif',
    titleSize: "26pt",
    titleWeight: "normal",
    marginX: "0.625in",
    marginTop: "0.875in",
    marginBottom: "0.875in",
    abstractStyle: "bold",
    abstractInset: "0",
    headingNumbering: "roman",
    bodyLineHeight: "1.14",
    paragraphIndent: "14.4pt",
    captionSize: "8pt",
    referenceSize: "8pt",
    enabled: true,
  },
  transactions: {
    name: "IEEE Transactions",
    family: "ieee",
    description: "US-Letter, 2-col, 24pt title, bold abstract, ComSoc style",
    paperSize: "letter",
    colCount: 2,
    colGap: "0.25in",
    fontFamily: '"Times New Roman", Times, serif',
    fontSize: "10pt",
    titleFontFamily: '"Times New Roman", Times, serif',
    titleSize: "24pt",
    titleWeight: "normal",
    marginX: "0.625in",
    marginTop: "0.875in",
    marginBottom: "1in",
    abstractStyle: "bold",
    abstractInset: "0",
    headingNumbering: "roman",
    bodyLineHeight: "1.14",
    paragraphIndent: "14.4pt",
    captionSize: "8pt",
    referenceSize: "8pt",
    enabled: true,
  },
  "acm-sigconf": {
    name: "ACM SIGCONF",
    family: "acm",
    description: "US-Letter, 2-col 3.333in each, 9pt body, 18pt bold sans title, Arabic headings",
    paperSize: "letter",
    colCount: 2,
    colGap: "0.333in",
    fontFamily: '"Times New Roman", Times, serif',
    fontSize: "9pt",
    titleFontFamily: 'Helvetica, Arial, sans-serif',
    titleSize: "18pt",
    titleWeight: "bold",
    marginX: "0.75in",
    marginTop: "1in",
    marginBottom: "1in",
    abstractStyle: "normal",
    abstractInset: "0",
    headingNumbering: "arabic",
    bodyLineHeight: "1.2",
    paragraphIndent: "12pt",
    captionSize: "9pt",
    referenceSize: "8pt",
    enabled: true,
  },
  "springer-lncs": {
    name: "Springer LNCS",
    family: "springer",
    description: "Single-col, 10pt body, 14pt bold title, 122×193mm print area, abstract inset 1cm",
    paperSize: "a4",
    colCount: 1,
    colGap: "0in",
    fontFamily: '"Times New Roman", "Computer Modern", Times, serif',
    fontSize: "10pt",
    titleFontFamily: '"Times New Roman", "Computer Modern", Times, serif',
    titleSize: "14pt",
    titleWeight: "bold",
    marginX: "1.73in",
    marginTop: "2.05in",
    marginBottom: "2.05in",
    abstractStyle: "normal",
    abstractInset: "1cm",
    headingNumbering: "arabic",
    bodyLineHeight: "1.2",
    paragraphIndent: "12pt",
    captionSize: "9pt",
    referenceSize: "9pt",
    enabled: true,
  },
};

const FORMAT_FAMILIES: { key: FormatFamily; label: string }[] = [
  { key: "ieee", label: "IEEE" },
  { key: "acm", label: "ACM" },
  { key: "springer", label: "Springer" },
];

type PaperSettings = {
  format: DocumentFormat;
  colCount: 1 | 2;
  colGap: string;
  fontFamily: string;
  fontSize: string;
  titleFontFamily: string;
  titleSize: string;
  titleWeight: "normal" | "bold";
  marginX: string;
  marginTop: string;
  marginBottom: string;
  abstractStyle: "italic" | "normal" | "bold";
  abstractInset: string;
  headingNumbering: "roman" | "arabic";
  bodyLineHeight: string;
  paragraphIndent: string;
  captionSize: string;
  referenceSize: string;
};

const createPaperSettings = (format: DocumentFormat): PaperSettings => {
  const preset = FORMAT_PRESETS[format];
  return {
    format,
    colCount: preset.colCount,
    colGap: preset.colGap,
    fontFamily: preset.fontFamily,
    fontSize: preset.fontSize,
    titleFontFamily: preset.titleFontFamily,
    titleSize: preset.titleSize,
    titleWeight: preset.titleWeight,
    marginX: preset.marginX,
    marginTop: preset.marginTop,
    marginBottom: preset.marginBottom,
    abstractStyle: preset.abstractStyle,
    abstractInset: preset.abstractInset,
    headingNumbering: preset.headingNumbering,
    bodyLineHeight: preset.bodyLineHeight,
    paragraphIndent: preset.paragraphIndent,
    captionSize: preset.captionSize,
    referenceSize: preset.referenceSize,
  };
};

const FORMAL_FONT_OPTIONS = [
  { label: "Times New Roman (IEEE)", value: '"Times New Roman", Times, serif' },
  { label: "Cambria", value: 'Cambria, "Times New Roman", serif' },
  { label: "Georgia", value: 'Georgia, "Times New Roman", serif' },
  { label: "Garamond", value: 'Garamond, "Times New Roman", serif' },
  { label: "Palatino", value: '"Palatino Linotype", Palatino, serif' },
  { label: "Calibri", value: "Calibri, Arial, sans-serif" },
  { label: "Arial", value: "Arial, Helvetica, sans-serif" },
];

const FONT_SIZE_OPTIONS = ["9pt", "10pt", "11pt", "12pt", "13pt", "14pt"];

// Context Menu State
type ContextMenuState = {
  visible: boolean;
  x: number;
  y: number;
};

type ContextMenuItem = {
  label?: string;
  shortcut?: string;
  action?: () => void;
  disabled?: boolean;
  type?: "divider";
};

type ToolButtonProps = {
  label: string;
  onClick: () => void;
  active?: boolean;
  disabled?: boolean;
  title?: string;
  tone?: "default" | "danger";
};

type DocumentMode = "paper" | "thesis";

type EditorMark = {
  type?: string;
};

type EditorNode = {
  type?: string;
  text?: string;
  attrs?: {
    level?: number;
    className?: string;
    ieeeRole?: string;
    src?: string;
    alt?: string;
    title?: string;
    [key: string]: unknown;
  };
  marks?: EditorMark[];
  content?: EditorNode[];
};

export default function UniversalResearchFormatterPage() {
  const [documentMode, setDocumentMode] = useState<DocumentMode>("paper");
  const [activeFamily, setActiveFamily] = useState<FormatFamily>("ieee");
  const [settings, setSettings] = useState<PaperSettings>(
    createPaperSettings("conference"),
  );
  const [rawInput, setRawInput] = useState<string>("");
  const [isFormatting, setIsFormatting] = useState(false);
  const [isAiEnhancing, setIsAiEnhancing] = useState(false);
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

  // Preview state — updated only on explicit "Refresh Preview" click
  const [ieeeHtml, setIeeeHtml] = useState<string>("");
  const [previewStale, setPreviewStale] = useState(false); // true when editor changed since last format/refresh
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isTableDialogOpen, setIsTableDialogOpen] = useState(false);
  const [isEquationDialogOpen, setIsEquationDialogOpen] = useState(false);
  const [aiCommand, setAiCommand] = useState("");
  const [isAiCopilotRunning, setIsAiCopilotRunning] = useState(false);
  const [aiCopilotStatus, setAiCopilotStatus] = useState<string | null>(null);

  const editorRef = useRef<HTMLDivElement>(null);
  const pagesContainerRef = useRef<HTMLDivElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const pendingInsertPosRef = useRef<number | null>(null);
  const isProgrammaticUpdateRef = useRef(false);
  const refreshTimerRef = useRef<number | null>(null);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: false,
        paragraph: false,
      }),
      IeeeHeading.configure({
        levels: [1, 2, 3, 4],
      }),
      IeeeParagraph,
      IeeeContainer,
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
      Image.configure({
        inline: false,
        allowBase64: true,
      }),
    ],
    immediatelyRender: false,
    content: "",
  });

  const getNextFigureNumber = useCallback(() => {
    const doc = editor?.getJSON();
    let count = 0;

    const visit = (node: EditorNode | null | undefined) => {
      if (!node) return;

      if (
        node.type === "paragraph" &&
        node.attrs?.ieeeRole === "figureCaption"
      ) {
        count += 1;
      }

      if (Array.isArray(node.content)) {
        node.content.forEach(visit);
      }
    };

    visit(doc);
    return count + 1;
  }, [editor]);

  const insertFigureAtSelection = useCallback(
    (src: string, caption?: string) => {
      if (!editor || !src) return;

      const figureNumber = getNextFigureNumber();
      const defaultCaption = `Figure ${figureNumber}.`;
      const trimmedCaption = (caption || "").trim();
      const finalCaption = trimmedCaption || defaultCaption;
      const insertPos =
        pendingInsertPosRef.current ?? editor.state.selection.from;

      editor
        .chain()
        .focus()
        .setTextSelection(insertPos)
        .insertContent([
          {
            type: "ieeeContainer",
            attrs: { className: "figure-block" },
            content: [
              {
                type: "image",
                attrs: {
                  src,
                  alt: finalCaption,
                  title: finalCaption,
                },
              },
              {
                type: "paragraph",
                attrs: {
                  ieeeRole: "figureCaption",
                  noIndent: true,
                },
                content: finalCaption
                  ? [{ type: "text", text: finalCaption }]
                  : [],
              },
            ],
          },
          {
            type: "paragraph",
            attrs: { ieeeRole: "none" },
          },
        ])
        .run();

      pendingInsertPosRef.current = null;
      setPreviewStale(true);
    },
    [editor, getNextFigureNumber],
  );

  const openImagePicker = useCallback(() => {
    if (!editor) return;
    pendingInsertPosRef.current = editor.state.selection.from;
    imageInputRef.current?.click();
  }, [editor]);

  const insertImageByUrl = useCallback(() => {
    if (!editor) return;

    pendingInsertPosRef.current = editor.state.selection.from;
    const src = window.prompt("Paste image URL:", "https://");
    if (!src) {
      pendingInsertPosRef.current = null;
      return;
    }

    const caption = window.prompt("Caption (optional):", "") ?? "";
    insertFigureAtSelection(src.trim(), caption);
  }, [editor, insertFigureAtSelection]);

  const handleImageUpload = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      event.target.value = "";
      if (!file || !file.type.startsWith("image/")) return;

      const reader = new FileReader();
      reader.onload = () => {
        const src = typeof reader.result === "string" ? reader.result : "";
        if (!src) return;
        const caption = window.prompt("Caption (optional):", "") ?? "";
        insertFigureAtSelection(src, caption);
      };
      reader.readAsDataURL(file);
    },
    [insertFigureAtSelection],
  );

  // Apply format preset
  const applyPreset = (format: DocumentFormat) => {
    if (!FORMAT_PRESETS[format].enabled) return;
    setSettings(createPaperSettings(format));
    setActiveFamily(FORMAT_PRESETS[format].family);
  };

  const ToolButton = ({
    label,
    onClick,
    active = false,
    disabled = false,
    title,
    tone = "default",
  }: ToolButtonProps) => {
    const base =
      "rounded-lg border px-2.5 py-1.5 text-xs transition-colors disabled:cursor-not-allowed disabled:opacity-40";
    const toneClass =
      tone === "danger"
        ? "border-rose-800 bg-rose-900/20 text-rose-200 hover:bg-rose-800/40"
        : active
          ? "border-indigo-500 bg-indigo-600 text-white"
          : "border-zinc-700 bg-zinc-800 text-zinc-200 hover:bg-zinc-700";
    return (
      <button
        onClick={onClick}
        disabled={disabled}
        title={title}
        className={`${base} ${toneClass}`}
      >
        {label}
      </button>
    );
  };

  // Context Menu Handler
  const handleContextMenu = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();

      const menuWidth = 220;
      const menuHeight = documentMode === "thesis" ? 560 : 340;
      const x = Math.min(e.clientX, window.innerWidth - menuWidth - 8);
      const y = Math.min(e.clientY, window.innerHeight - menuHeight - 8);

      setContextMenu({
        visible: true,
        x,
        y,
      });
    },
    [documentMode],
  );

  const handleInsertTable = useCallback(
    (rows: number, cols: number, withHeader: boolean) => {
      if (!editor) return;
      editor
        .chain()
        .focus()
        .insertTable({ rows, cols, withHeaderRow: withHeader })
        .run();
      setPreviewStale(true);
    },
    [editor],
  );

  const handleInsertEquation = useCallback(
    (latex: string, isBlock: boolean) => {
      if (!editor || !latex.trim()) return;
      const normalized = latex.trim();
      if (isBlock) {
        editor
          .chain()
          .focus()
          .toggleBlockquote()
          .insertContent(`$$${normalized}$$`)
          .toggleBlockquote()
          .insertContent({ type: "paragraph" })
          .run();
      } else {
        editor.chain().focus().insertContent(`$${normalized}$`).run();
      }
      setPreviewStale(true);
    },
    [editor],
  );

  const insertFrontMatterBlock = useCallback(
    (className: string, lines: string[]) => {
      if (!editor) return;

      const paragraphNodes = lines
        .map((line) => line.trim())
        .filter(Boolean)
        .map((line) => ({
          type: "paragraph",
          attrs: {
            ieeeRole: "none",
            noIndent: true,
          },
          content: [{ type: "text", text: line }],
        }));

      if (paragraphNodes.length === 0) return;

      editor
        .chain()
        .focus()
        .insertContent([
          {
            type: "ieeeContainer",
            attrs: { className: `front-matter-page ${className}` },
            content: paragraphNodes,
          },
          {
            type: "ieeeContainer",
            attrs: { className: "front-matter-page-break" },
          },
          {
            type: "paragraph",
            attrs: { ieeeRole: "none" },
          },
        ])
        .run();

      setPreviewStale(true);
      setFormatStatus("Front-matter section inserted.");
      setTimeout(() => setFormatStatus(null), 2500);
    },
    [editor],
  );

  const buildLinesFromCustomTemplate = (customInput: string) =>
    customInput
      .split("||")
      .map((line) => line.trim())
      .filter(Boolean);

  const insertCoverPageBuilder = useCallback(() => {
    const custom =
      window.prompt(
        "Custom cover template (optional). Use || between lines. Leave blank for standard template:",
        "",
      ) ?? "";

    if (custom.trim()) {
      insertFrontMatterBlock(
        "front-matter-cover",
        buildLinesFromCustomTemplate(custom),
      );
      return;
    }

    const paperTitle = window
      .prompt("Paper/Thesis Title:", "Your Thesis Title")
      ?.trim();
    if (!paperTitle) return;
    const candidateName =
      window.prompt("Student Name:", "Your Name")?.trim() || "Your Name";
    const rollNumber =
      window.prompt("Roll Number:", "Roll Number")?.trim() || "Roll Number";
    const department =
      window.prompt("Department:", "Department Name")?.trim() ||
      "Department Name";
    const college =
      window.prompt("College / University:", "College Name")?.trim() ||
      "College Name";
    const monthYear =
      window.prompt("Submission Month & Year:", "Month Year")?.trim() ||
      "Month Year";

    insertFrontMatterBlock("front-matter-cover", [
      paperTitle,
      "",
      "A Project Report Submitted In Partial Fulfilment Of The Requirements",
      "for the award of degree",
      "",
      `Submitted by: ${candidateName}`,
      `Roll No.: ${rollNumber}`,
      "",
      department,
      college,
      monthYear,
    ]);
  }, [insertFrontMatterBlock]);

  const insertCertificateBuilder = useCallback(() => {
    const custom =
      window.prompt(
        "Custom certificate template (optional). Use || between lines. Leave blank for standard template:",
        "",
      ) ?? "";

    if (custom.trim()) {
      insertFrontMatterBlock(
        "front-matter-certificate",
        buildLinesFromCustomTemplate(custom),
      );
      return;
    }

    const candidateName =
      window.prompt("Student Name:", "Your Name")?.trim() || "Your Name";
    const paperTitle =
      window.prompt("Project/Thesis Title:", "Your Thesis Title")?.trim() ||
      "Your Thesis Title";
    const guideName =
      window.prompt("Guide Name:", "Guide Name")?.trim() || "Guide Name";
    const hodName =
      window.prompt("HOD Name:", "HOD Name")?.trim() || "HOD Name";
    const academicYear =
      window.prompt("Academic Year:", "2025-26")?.trim() || "2025-26";

    insertFrontMatterBlock("front-matter-certificate", [
      "CERTIFICATE",
      "",
      `This is to certify that ${candidateName} has successfully completed the project titled \"${paperTitle}\" during the academic year ${academicYear}.`,
      "",
      "This work has been carried out under our supervision and is submitted for evaluation.",
      "",
      `Guide Signature: ____________________ (${guideName})`,
      `HOD Signature: ______________________ (${hodName})`,
    ]);
  }, [insertFrontMatterBlock]);

  const insertDeclarationBuilder = useCallback(() => {
    const custom =
      window.prompt(
        "Custom declaration template (optional). Use || between lines. Leave blank for standard template:",
        "",
      ) ?? "";

    if (custom.trim()) {
      insertFrontMatterBlock(
        "front-matter-declaration",
        buildLinesFromCustomTemplate(custom),
      );
      return;
    }

    const candidateName =
      window.prompt("Student Name:", "Your Name")?.trim() || "Your Name";
    const paperTitle =
      window.prompt("Project/Thesis Title:", "Your Thesis Title")?.trim() ||
      "Your Thesis Title";

    insertFrontMatterBlock("front-matter-declaration", [
      "DECLARATION",
      "",
      `I, ${candidateName}, hereby declare that the project titled \"${paperTitle}\" is my original work and has not been submitted elsewhere for any degree or diploma.`,
      "",
      "I further declare that all sources used are duly acknowledged.",
      "",
      `Signature of Student: ____________________ (${candidateName})`,
    ]);
  }, [insertFrontMatterBlock]);

  const insertAcknowledgementBuilder = useCallback(() => {
    const custom =
      window.prompt(
        "Custom acknowledgement template (optional). Use || between lines. Leave blank for standard template:",
        "",
      ) ?? "";

    if (custom.trim()) {
      insertFrontMatterBlock(
        "front-matter-acknowledgement",
        buildLinesFromCustomTemplate(custom),
      );
      return;
    }

    const guideName =
      window.prompt("Guide Name:", "Guide Name")?.trim() || "Guide Name";
    const college =
      window.prompt("College / Department:", "College Name")?.trim() ||
      "College Name";

    insertFrontMatterBlock("front-matter-acknowledgement", [
      "ACKNOWLEDGEMENT",
      "",
      `I express my sincere gratitude to ${guideName} for continuous guidance and support during this project work.`,
      "",
      `I also thank the faculty members and staff of ${college} for their assistance and encouragement.`,
      "",
      "Finally, I am grateful to my family and friends for their support.",
    ]);
  }, [insertFrontMatterBlock]);

  const insertTocBuilder = useCallback(() => {
    if (!editor) return;

    const doc = editor.getJSON();
    const tocLines: string[] = ["TABLE OF CONTENTS", ""];

    const walk = (node: EditorNode | null | undefined) => {
      if (!node) return;
      if (node.type === "heading") {
        const level = node.attrs?.level ?? 1;
        if (level === 1 || level === 2) {
          const text = (node.content ?? [])
            .map((item: EditorNode) => item?.text ?? "")
            .join("")
            .trim();
          if (
            text &&
            !/^(table of contents|glossary|acknowledgement|declaration|certificate|cover page)$/i.test(
              text,
            )
          ) {
            tocLines.push(level === 1 ? `• ${text}` : `   ◦ ${text}`);
          }
        }
      }

      if (Array.isArray(node.content)) {
        node.content.forEach(walk);
      }
    };

    walk(doc);

    if (tocLines.length <= 2) {
      tocLines.push("• Add section headings (H1/H2) to auto-build TOC");
    }

    insertFrontMatterBlock("front-matter-toc", tocLines);
  }, [editor, insertFrontMatterBlock]);

  const insertGlossaryBuilder = useCallback(() => {
    if (!editor) return;

    const text = editor.getText();
    const detectedTerms = Array.from(
      new Set(text.match(/\b[A-Z][A-Z0-9]{1,}\b/g) ?? []),
    ).slice(0, 12);

    const customEntries =
      window.prompt(
        "Optional custom glossary entries (TERM: Definition). Use || between entries. Leave blank to use auto-suggestions.",
        "",
      ) ?? "";

    const glossaryLines = ["GLOSSARY", ""];

    if (customEntries.trim()) {
      const entries = customEntries
        .split("||")
        .map((item) => item.trim())
        .filter(Boolean);
      glossaryLines.push(...entries);
    } else if (detectedTerms.length > 0) {
      glossaryLines.push(
        ...detectedTerms.map((term) => `${term} — [Add definition]`),
      );
    } else {
      glossaryLines.push("TERM — [Add definition]");
      glossaryLines.push("ACRONYM — [Add definition]");
    }

    insertFrontMatterBlock("front-matter-glossary", glossaryLines);
  }, [editor, insertFrontMatterBlock]);

  // Close context menu on click elsewhere
  useEffect(() => {
    const handleClick = () =>
      setContextMenu((prev) => ({ ...prev, visible: false }));
    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, []);

  // Mark preview as stale whenever the user edits content (not programmatic updates)
  useEffect(() => {
    if (!editor) return;

    const onUpdate = () => {
      if (isProgrammaticUpdateRef.current) {
        isProgrammaticUpdateRef.current = false;
        return;
      }
      // User typed/edited — preview is now outdated
      setPreviewStale(true);
    };

    editor.on("update", onUpdate);
    return () => {
      editor.off("update", onUpdate);
    };
  }, [editor]);

  // Refresh Preview: schema-preserved HTML keeps IEEE semantic classes
  const refreshPreview = useCallback(() => {
    if (!editor) return;
    const plainText = editor.getText().trim();
    if (!plainText) {
      setIeeeHtml("");
      setPreviewStale(false);
      setPageCount(1);
      return;
    }

    setIsRefreshing(true);
    try {
      const html = editor.getHTML();
      setIeeeHtml(html);
      setPreviewStale(false);
      const estimated = estimatePageCount(html, settings.colCount);
      setPageCount(estimated);
    } catch {
      // Fallback: show raw editor HTML
      setIeeeHtml(editor.getHTML());
      setPreviewStale(false);
    } finally {
      setIsRefreshing(false);
    }
  }, [editor, settings.colCount]);

  // Auto-refresh preview shortly after user stops typing
  useEffect(() => {
    if (!previewStale || !editor || isRefreshing) return;

    if (refreshTimerRef.current) {
      window.clearTimeout(refreshTimerRef.current);
    }

    refreshTimerRef.current = window.setTimeout(() => {
      refreshPreview();
    }, 600);

    return () => {
      if (refreshTimerRef.current) {
        window.clearTimeout(refreshTimerRef.current);
      }
    };
  }, [previewStale, editor, isRefreshing, refreshPreview]);

  useEffect(() => {
    if (documentMode !== "thesis") return;
    setSettings((prev) => ({
      ...prev,
      colCount: 1,
      colGap: "0in",
    }));
  }, [documentMode]);

  // Context menu actions
  const isInTable = editor?.isActive("table") ?? false;

  const contextMenuActions: ContextMenuItem[] = [
    {
      label: "Undo",
      shortcut: "Ctrl+Z",
      action: () => editor?.chain().focus().undo().run(),
    },
    {
      label: "Redo",
      shortcut: "Ctrl+Y",
      action: () => editor?.chain().focus().redo().run(),
    },
    { type: "divider" as const },
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
    {
      label: "Heading 4",
      shortcut: "Ctrl+4",
      action: () => editor?.chain().focus().toggleHeading({ level: 4 }).run(),
    },
    {
      label: "Paragraph",
      shortcut: "",
      action: () => editor?.chain().focus().setParagraph().run(),
    },
    {
      label: "Block Quote",
      shortcut: "",
      action: () => editor?.chain().focus().toggleBlockquote().run(),
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
    { type: "divider" as const },
    {
      label: "Insert Table",
      shortcut: "",
      action: () => setIsTableDialogOpen(true),
    },
    {
      label: "Add Row",
      shortcut: "",
      action: () => editor?.chain().focus().addRowAfter().run(),
      disabled: !isInTable,
    },
    {
      label: "Add Column",
      shortcut: "",
      action: () => editor?.chain().focus().addColumnAfter().run(),
      disabled: !isInTable,
    },
    {
      label: "Delete Table",
      shortcut: "",
      action: () => editor?.chain().focus().deleteTable().run(),
      disabled: !isInTable,
    },
    { type: "divider" as const },
    {
      label: "Insert Figure (Upload)",
      shortcut: "",
      action: openImagePicker,
    },
    {
      label: "Insert Figure (URL)",
      shortcut: "",
      action: insertImageByUrl,
    },
    {
      label: "Insert Equation",
      shortcut: "",
      action: () => setIsEquationDialogOpen(true),
    },
    { type: "divider" as const },
    {
      label: "Insert Cover Page",
      shortcut: "",
      action: insertCoverPageBuilder,
      disabled: documentMode !== "thesis",
    },
    {
      label: "Insert Certificate",
      shortcut: "",
      action: insertCertificateBuilder,
      disabled: documentMode !== "thesis",
    },
    {
      label: "Insert Declaration",
      shortcut: "",
      action: insertDeclarationBuilder,
      disabled: documentMode !== "thesis",
    },
    {
      label: "Insert Acknowledgement",
      shortcut: "",
      action: insertAcknowledgementBuilder,
      disabled: documentMode !== "thesis",
    },
    {
      label: "Build TOC",
      shortcut: "",
      action: insertTocBuilder,
      disabled: documentMode !== "thesis",
    },
    {
      label: "Build Glossary",
      shortcut: "",
      action: insertGlossaryBuilder,
      disabled: documentMode !== "thesis",
    },
  ];

  const runDeterministicFormat = useCallback(
    (input: string) => {
      // Build format options based on active template
      const preset = FORMAT_PRESETS[settings.format];
      const parsedDoc = parseDocument(input);
      let result;
      let estimatedPages = 1;

      if (preset.family === "acm") {
        result = formatToACM(parsedDoc, {
          addCCSBlock: true,
          addKeywordsBlock: true,
        });
        estimatedPages = estimatePageCount(result.html, settings.colCount);
      } else if (preset.family === "springer") {
        result = formatToSpringer(parsedDoc, {});
        estimatedPages = estimatePageCount(result.html, settings.colCount);
      } else {
        const formatOpts: FormatOptions = {
          numberingStyle: preset?.headingNumbering ?? "roman",
          useDropCap: settings.format === "journal" || settings.format === "transactions",
          hideCopyright: false,
          authorStyle: "grid",
        };
        result = formatToIEEE(parsedDoc, formatOpts);
        estimatedPages = estimatePageCount(result.html, settings.colCount);
      }

      if (!result.html) {
        throw new Error("No content generated");
      }

      isProgrammaticUpdateRef.current = true;
      editor?.commands.setContent(result.html);
      setIeeeHtml(result.html); // Store IEEE HTML directly (bypasses TipTap stripping)
      setPreviewStale(false);
      setPageCount(estimatedPages);

      return { result, estimatedPages };
    },
    [editor, settings, settings.format, settings.colCount],
  );

  // Smart paste handler: intercept clipboard HTML to preserve table structure
  const handlePaste = useCallback(
    (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
      const html = e.clipboardData.getData("text/html");
      // Only proceed if clipboard HTML actually contains a <table> element
      if (!html || !/<table[\s>]/i.test(html)) {
        return; // No HTML table — let browser handle default paste
      }

      const parser = new DOMParser();
      const doc = parser.parseFromString(html, "text/html");

      // Only process meaningful tables (2+ rows, 2+ columns)
      const meaningfulTables = Array.from(doc.querySelectorAll("table")).filter(
        (table) => {
          const rows = table.querySelectorAll("tr");
          if (rows.length < 2) return false;
          return rows[0].querySelectorAll("th, td").length >= 2;
        },
      );

      if (meaningfulTables.length === 0) {
        return; // No meaningful tables — default paste
      }

      e.preventDefault();

      // ALWAYS use text/plain as the base — it preserves line breaks and structure
      let result = e.clipboardData.getData("text/plain");

      // For each table, convert to pipe-separated and try to replace in plain text
      for (const table of meaningfulTables) {
        const rows = Array.from(table.querySelectorAll("tr"));
        const pipeRows = rows.map((tr) => {
          const cells = Array.from(tr.querySelectorAll("th, td"));
          return cells
            .map((c) => (c.textContent || "").replace(/\s+/g, " ").trim())
            .join(" | ");
        });
        const pipeTable = pipeRows.join("\n");

        // Build the concatenated text per row (how it appears in plain text)
        const rowTexts = rows.map((tr) => {
          const cells = Array.from(tr.querySelectorAll("th, td"));
          return cells
            .map((c) => (c.textContent || "").replace(/\s+/g, " ").trim())
            .join("");
        });

        // Find the table region in plain text by matching first/last row text
        const firstRowText = rowTexts[0];
        const lastRowText = rowTexts[rowTexts.length - 1];
        if (firstRowText && lastRowText && firstRowText.length > 3) {
          const startIdx = result.indexOf(firstRowText);
          if (startIdx !== -1) {
            const searchAfter = result.substring(startIdx);
            const lastIdx = searchAfter.lastIndexOf(lastRowText);
            if (lastIdx !== -1) {
              const absEnd = startIdx + lastIdx + lastRowText.length;
              result =
                result.substring(0, startIdx) +
                pipeTable +
                result.substring(absEnd);
            }
          }
        }
      }

      // Insert at cursor position in the textarea
      const textarea = e.currentTarget;
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const currentValue = rawInput;
      const newValue =
        currentValue.substring(0, start) + result + currentValue.substring(end);
      setRawInput(newValue);

      requestAnimationFrame(() => {
        textarea.selectionStart = start + result.length;
        textarea.selectionEnd = start + result.length;
      });
    },
    [rawInput],
  );

  // Deterministic Format Handler (consistent every time)
  const handleFormat = () => {
    if (!rawInput.trim() || isFormatting) return;

    setIsFormatting(true);
    setFormatStatus("Formatting to IEEE standard...");
    setFormatError(null);

    try {
      const { result, estimatedPages } = runDeterministicFormat(
        rawInput.trim(),
      );

      console.log("Format result:", {
        sectionCount: result.sectionCount,
        tableCount: result.tableCount,
        equationCount: result.equationCount,
        algorithmCount: result.algorithmCount,
        citationCount: result.citationCount,
      });

      setFormatStatus(
        `Formatted: ${result.sectionCount} sections, ${result.tableCount} tables, ${result.equationCount} equations, ${result.algorithmCount} algorithms, ${result.citationCount} citations → ${estimatedPages} page(s)`,
      );
      setRawInput("");
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

  const aiHtmlToDeterministicInput = (html: string) => {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, "text/html");
    const lines: string[] = [];
    let inReferences = false;
    let referenceCounter = 1;

    const pushLine = (value: string) => {
      const clean = value.replace(/\s+/g, " ").trim();
      if (clean) lines.push(clean);
    };

    const getElementText = (el: HTMLElement) =>
      (el.textContent ?? "").replace(/\s+/g, " ").trim();

    Array.from(doc.body.childNodes).forEach((node) => {
      if (node.nodeType === Node.TEXT_NODE) {
        pushLine(node.textContent ?? "");
        return;
      }

      if (!(node instanceof HTMLElement)) {
        return;
      }

      const tag = node.tagName;

      if (["H1", "H2", "H3", "H4", "H5"].includes(tag)) {
        const headingText = getElementText(node);
        if (headingText) {
          pushLine(headingText);
          lines.push("");
        }
        inReferences =
          /^(?:(?:[ivxlcdm]+|\d+)[.)]\s*)?(references|bibliography)\b/i.test(
            headingText,
          );
        return;
      }

      if (node.classList.contains("algorithm-block") || tag === "PRE") {
        const title = getElementText(
          (node.querySelector(".algo-title") as HTMLElement | null) ?? node,
        );

        const algoLineElements = Array.from(
          node.querySelectorAll(".algo-line"),
        );
        const algoLines =
          algoLineElements.length > 0
            ? algoLineElements
              .map((lineEl) => getElementText(lineEl as HTMLElement))
              .filter(Boolean)
            : (node.textContent ?? "")
              .split(/\r?\n/)
              .map((line) => line.trim())
              .filter(Boolean);

        if (/^algorithm\s+\d+/i.test(title)) {
          pushLine(title);
        } else {
          const firstAlgorithmLine = algoLines.find((line) =>
            /^algorithm\s+\d+/i.test(line),
          );
          if (firstAlgorithmLine) pushLine(firstAlgorithmLine);
        }

        algoLines.forEach((line) => {
          if (!line) return;
          if (/^algorithm\s+\d+/i.test(line)) return;
          pushLine(line);
        });
        lines.push("");
        return;
      }

      if (node.classList.contains("table-caption")) {
        pushLine(getElementText(node));
        lines.push("");
        return;
      }

      if (tag === "TABLE") {
        const captionEl = node.querySelector("caption") as HTMLElement | null;
        if (captionEl) {
          const captionText = getElementText(captionEl);
          if (captionText) pushLine(captionText);
        }

        const rows = Array.from(node.querySelectorAll("tr"));
        rows.forEach((row) => {
          const cells = Array.from(row.querySelectorAll("th, td"));
          const parts = cells.map((cell) =>
            getElementText(cell as HTMLElement),
          );
          if (parts.length) pushLine(parts.join(" | "));
        });
        lines.push("");
        return;
      }

      if (tag === "OL" || tag === "UL") {
        const items = Array.from(node.children).filter(
          (child) => child.tagName === "LI",
        ) as HTMLElement[];

        items.forEach((li) => {
          const itemText = getElementText(li);
          if (!itemText) return;

          if (inReferences) {
            if (/^\[\d+\]/.test(itemText)) {
              pushLine(itemText);
              referenceCounter += 1;
            } else {
              const numbered = itemText.match(/^(\d+)[.)]\s*(.*)$/);
              if (numbered) {
                pushLine(`[${numbered[1]}] ${numbered[2]}`);
              } else {
                pushLine(`[${referenceCounter}] ${itemText}`);
              }
              referenceCounter += 1;
            }
          } else {
            pushLine(itemText);
          }
        });
        lines.push("");
        return;
      }

      const text = getElementText(node);
      if (text) {
        if (inReferences) {
          if (/^\[\d+\]/.test(text)) {
            pushLine(text);
            referenceCounter += 1;
          } else {
            const numbered = text.match(/^(\d+)[.)]\s*(.*)$/);
            if (numbered) {
              pushLine(`[${numbered[1]}] ${numbered[2]}`);
            } else {
              pushLine(`[${referenceCounter}] ${text}`);
            }
            referenceCounter += 1;
          }
        } else {
          pushLine(text);
        }
      }

      if (["P", "DIV", "BLOCKQUOTE", "LI"].includes(tag)) {
        lines.push("");
      }
    });

    return lines
      .join("\n")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  };

  const handleAiEnhance = async () => {
    if (!rawInput.trim() || isAiEnhancing || isFormatting) return;

    setIsAiEnhancing(true);
    setFormatError(null);
    setFormatStatus(
      "AI enhancing input: grammar check, section cleanup, table normalization...",
    );

    try {
      // Map non-IEEE formats to "conference" for the AI enhancer API
      const apiFormatType: "conference" | "journal" | "transactions" =
        settings.format === "journal" ? "journal"
          : settings.format === "transactions" ? "transactions"
            : "conference";
      const response = await api.formatIEEE({
        raw_text: rawInput.trim(),
        format_type: apiFormatType,
        detect_equations: true,
        detect_references: true,
      });

      if (!response.success || !response.formatted_html?.trim()) {
        throw new Error(response.error || "AI enhancement failed");
      }

      const normalizedRawInput = aiHtmlToDeterministicInput(
        response.formatted_html,
      );

      const { result, estimatedPages } = runDeterministicFormat(
        normalizedRawInput || rawInput.trim(),
      );

      setFormatStatus(
        `AI enhanced (${response.provider}) + deterministic formatting: ${result.sectionCount} sections, ${result.tableCount} tables, ${result.equationCount} equations → ${estimatedPages} page(s)`,
      );
      setRawInput("");
    } catch (error) {
      console.error("AI enhance error:", error);
      setFormatError(
        error instanceof Error
          ? error.message
          : "AI enhancement failed. Try deterministic formatting.",
      );
    } finally {
      setIsAiEnhancing(false);
      setTimeout(() => setFormatStatus(null), 6000);
    }
  };

  const applyAiCssUpdates = useCallback((updates: Record<string, unknown>) => {
    setSettings((prev) => {
      const next = { ...prev };

      const colCount = updates["--col-count"];
      if (colCount === 1 || colCount === "1") next.colCount = 1;
      if (colCount === 2 || colCount === "2") next.colCount = 2;

      const colGap = updates["--col-gap"];
      if (typeof colGap === "string" && colGap.trim()) next.colGap = colGap;

      const fontSize = updates["--font-size"];
      if (typeof fontSize === "string" && fontSize.trim()) {
        next.fontSize = fontSize;
      }

      const marginX = updates["--margin-x"];
      if (typeof marginX === "string" && marginX.trim()) next.marginX = marginX;

      const marginY = updates["--margin-y"];
      if (typeof marginY === "string" && marginY.trim()) {
        next.marginTop = marginY;
        next.marginBottom = marginY;
      }

      return next;
    });
  }, []);

  const applyAiEditorAction = useCallback(
    (action: string) => {
      if (!editor) return false;

      const chain = editor.chain().focus();
      switch (action) {
        case "toggleBold":
          return chain.toggleBold().run();
        case "toggleItalic":
          return chain.toggleItalic().run();
        case "toggleHeading1":
          return chain.toggleHeading({ level: 1 }).run();
        case "toggleHeading2":
          return chain.toggleHeading({ level: 2 }).run();
        default:
          return false;
      }
    },
    [editor],
  );

  const runAiCopilot = useCallback(async () => {
    if (!editor || !aiCommand.trim() || isAiCopilotRunning) return;

    setIsAiCopilotRunning(true);
    setAiCopilotStatus("Analyzing request...");

    try {
      const response = await api.formatCommands({
        prompt: aiCommand.trim(),
        settings: {
          format: settings.format,
          colCount: settings.colCount,
          colGap: settings.colGap,
          fontSize: settings.fontSize,
          marginX: settings.marginX,
          marginTop: settings.marginTop,
          marginBottom: settings.marginBottom,
        },
        available_targets: [
          "selection",
          "current paragraph",
          "section heading",
          "abstract",
          "references",
          "document",
        ],
      });

      const cssUpdates = response.cssUpdates ?? {};
      const editorCommands = response.editorCommands ?? [];

      applyAiCssUpdates(cssUpdates as Record<string, unknown>);

      let appliedCommands = 0;
      for (const cmd of editorCommands) {
        if (applyAiEditorAction(cmd.action)) {
          appliedCommands += 1;
        }
      }

      if (appliedCommands > 0) {
        setPreviewStale(true);
      }

      setAiCopilotStatus(
        `Applied ${appliedCommands} editor change(s) and ${Object.keys(cssUpdates as Record<string, unknown>).length} layout update(s).`,
      );
      setAiCommand("");
    } catch (error) {
      setAiCopilotStatus(
        error instanceof Error ? error.message : "AI Copilot request failed.",
      );
    } finally {
      setIsAiCopilotRunning(false);
      setTimeout(() => setAiCopilotStatus(null), 5000);
    }
  }, [
    aiCommand,
    applyAiCssUpdates,
    applyAiEditorAction,
    editor,
    isAiCopilotRunning,
    settings.colCount,
    settings.colGap,
    settings.fontSize,
    settings.format,
    settings.marginBottom,
    settings.marginTop,
    settings.marginX,
  ]);

  // LaTeX Builder
  const escapeLatex = (value: string) =>
    value
      .replace(/\\/g, "\\textbackslash{}")
      .replace(/([{}%&_#])/g, "\\$1")
      .replace(/\^/g, "\\textasciicircum{}")
      .replace(/~/g, "\\textasciitilde{}")
      .replace(/\$/g, "\\$");

  const renderTextNode = (node: EditorNode) => {
    const text = escapeLatex(node.text ?? "");
    const marks = node.marks ?? [];
    const isBold = marks.some((mark: EditorMark) => mark.type === "bold");
    const isItalic = marks.some((mark: EditorMark) => mark.type === "italic");
    const isStrike = marks.some((mark: EditorMark) => mark.type === "strike");
    const isCode = marks.some((mark: EditorMark) => mark.type === "code");
    const isSubscript = marks.some(
      (mark: EditorMark) => mark.type === "subscript",
    );
    const isSuperscript = marks.some(
      (mark: EditorMark) => mark.type === "superscript",
    );
    const isUnderline = marks.some(
      (mark: EditorMark) => mark.type === "underline",
    );

    let result = text;
    if (isCode) result = `\\texttt{${result}}`;
    if (isSubscript) result = `\\textsubscript{${result}}`;
    if (isSuperscript) result = `\\textsuperscript{${result}}`;
    if (isUnderline) result = `\\underline{${result}}`;
    if (isStrike) result = `\\sout{${result}}`;
    if (isBold && isItalic) return `\\textbf{\\textit{${result}}}`;
    if (isBold) return `\\textbf{${result}}`;
    if (isItalic) return `\\textit{${result}}`;
    return result;
  };

  const extractPlainTextFromNode = (
    node: EditorNode | null | undefined,
  ): string => {
    if (!node) return "";
    if (node.type === "text") return node.text ?? "";
    return (node.content ?? []).map(extractPlainTextFromNode).join(" ").trim();
  };

  const renderNode = (node: EditorNode | null | undefined): string => {
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

    if (node.type === "ieeeContainer") {
      const className = (node.attrs?.className ?? "") as string;
      if (className.includes("front-matter-page-break")) {
        return "\\newpage";
      }

      return (node.content ?? [])
        .map((child: EditorNode) => renderNode(child))
        .filter(Boolean)
        .join("\n");
    }

    if (node.type === "horizontalRule") {
      return "\\noindent\\rule{\\columnwidth}{0.4pt}";
    }

    if (node.type === "codeBlock") {
      const codeText = escapeLatex(extractPlainTextFromNode(node));
      return `\\begin{verbatim}\n${codeText}\n\\end{verbatim}`;
    }

    if (node.type === "blockquote") {
      const quoteText = (node.content ?? []).map(renderNode).join(" ").trim();
      const equationText = quoteText.replace(/\$\$/g, "").trim();
      return equationText
        ? `\\begin{equation*}\n${equationText}\n\\end{equation*}`
        : "";
    }

    if (node.type === "image") {
      const caption = escapeLatex(node.attrs?.title ?? node.attrs?.alt ?? "");
      return [
        "\\begin{figure}[htbp]",
        "\\centering",
        "\\fbox{\\textit{Image in editor content}}",
        caption ? `\\caption{${caption}}` : "",
        "\\end{figure}",
      ]
        .filter(Boolean)
        .join("\n");
    }

    if (node.type === "bulletList") {
      const items = (node.content ?? [])
        .map((child: EditorNode) => renderNode(child))
        .filter(Boolean)
        .join("\n");
      return `\\begin{itemize}\n${items}\n\\end{itemize}`;
    }

    if (node.type === "orderedList") {
      const items = (node.content ?? [])
        .map((child: EditorNode) => renderNode(child))
        .filter(Boolean)
        .join("\n");
      return `\\begin{enumerate}\n${items}\n\\end{enumerate}`;
    }

    if (node.type === "listItem") {
      const content = (node.content ?? [])
        .map((child: EditorNode) => renderNode(child))
        .filter(Boolean)
        .join(" ")
        .trim();
      return content ? `\\item ${content}` : "";
    }

    if (node.type === "table") {
      const rows = (node.content ?? []).filter(
        (row: EditorNode) => row.type === "tableRow",
      );
      if (!rows.length) return "";

      const parsedRows = rows.map((row: EditorNode) =>
        (row.content ?? [])
          .filter(
            (cell: EditorNode) =>
              cell.type === "tableCell" || cell.type === "tableHeader",
          )
          .map((cell: EditorNode) => {
            const content = (cell.content ?? [])
              .map(renderNode)
              .join(" ")
              .trim();
            return content.replace(/\n+/g, " ");
          }),
      );

      const maxCols = Math.max(1, ...parsedRows.map((r: string[]) => r.length));
      const colSpec = `|${Array.from({ length: maxCols })
        .map(() => "l")
        .join("|")}|`;
      const lines: string[] = [
        "\\begin{table}[htbp]",
        "\\centering",
        `\\begin{tabular}{${colSpec}}`,
        "\\hline",
      ];

      for (const row of parsedRows) {
        const padded = [...row];
        while (padded.length < maxCols) padded.push("");
        lines.push(`${padded.join(" & ")} \\\\ \\hline`);
      }

      lines.push("\\end{tabular}", "\\end{table}");
      return lines.join("\n");
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
      case "acm-sigconf":
        return "\\documentclass[sigconf]{acmart}";
      case "springer-lncs":
        return "\\documentclass{llncs}";
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
      "\\usepackage[normalem]{ulem}",
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
          setExportStatus(
            "pdflatex not found. Opening browser print dialog...",
          );
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

    // Use IEEE preview HTML to preserve semantics/classes after edits.
    const content = ieeeHtml || editor.getHTML();
    const abstractFontStyle =
      settings.abstractStyle === "italic" ? "italic" : "normal";
    const abstractFontWeight =
      settings.abstractStyle === "bold" ? "bold" : "normal";
    const pageSize = FORMAT_PRESETS[settings.format]?.paperSize === "letter" ? "letter" : "A4";
    const isACM = FORMAT_PRESETS[settings.format]?.family === "acm";
    const isLNCS = FORMAT_PRESETS[settings.format]?.family === "springer";
    const isIEEE = FORMAT_PRESETS[settings.format]?.family === "ieee";
    const hasDropCap = settings.format === "journal" || settings.format === "transactions";

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
        <title>Research Paper - ${FORMAT_PRESETS[settings.format]?.name ?? "Paper"}</title>
        <style>
          @page {
            size: ${pageSize};
            margin: ${settings.marginTop} ${settings.marginX} ${settings.marginBottom} ${settings.marginX};
          }
          body {
            font-family: ${settings.fontFamily};
            font-size: ${settings.fontSize};
            line-height: ${settings.bodyLineHeight};
            column-count: ${settings.colCount};
            column-gap: ${settings.colGap};
            text-align: justify;
            hyphens: auto;
            margin: 0;
            padding: 0 0 20pt;
          }
          .paper-title {
            column-span: all;
            text-align: center;
            font-family: ${settings.titleFontFamily};
            font-size: ${settings.titleSize};
            font-weight: ${settings.titleWeight};
            margin: 0 0 6pt;
          }
          .author-grid {
            column-span: all;
            display: grid;
            gap: 8pt 16pt;
            margin: 18pt 0 10pt;
          }
          .author-grid-1 {
            grid-template-columns: 1fr;
          }
          .author-grid-2 {
            grid-template-columns: 1fr 1fr;
          }
          .author-grid-3 {
            grid-template-columns: 1fr 1fr 1fr;
          }
          .author-block {
            text-align: center;
          }
          .author-name {
            margin: 0 0 2pt;
            font-size: 11pt;
            text-indent: 0;
          }
          .author-line {
            margin: 0;
            font-size: 10pt;
            text-indent: 0;
          }
          h1, h1.ieee-heading {
            font-size: ${isACM ? '12pt' : '10pt'};
            font-weight: ${isACM || isLNCS ? 'bold' : 'normal'};
            font-variant: ${isACM || isLNCS ? 'normal' : 'small-caps'};
            text-transform: none;
            text-align: ${isACM || isLNCS ? 'left' : 'center'};
            margin: 10pt 0 4pt;
            break-after: avoid-column;
          }
          h1.paper-title {
            column-span: all;
            font-variant: normal;
            font-family: ${settings.titleFontFamily};
            font-size: ${settings.titleSize};
            font-weight: ${settings.titleWeight};
            text-align: center;
            text-indent: 0;
            margin: 0 0 8pt;
          }
          .paper-authors {
            column-span: all;
            text-align: center;
            font-size: 11pt;
            text-indent: 0;
            margin: 0 0 4pt;
          }
          .author-line {
            column-span: all;
          }
          h2, h2.ieee-subheading {
            font-size: ${isACM ? '12pt' : '10pt'};
            font-style: ${isACM || isLNCS ? 'normal' : 'italic'};
            font-weight: ${isACM || isLNCS ? 'bold' : 'normal'};
            text-transform: none;
            text-align: left;
            margin: 6pt 0 3pt;
            break-after: avoid-column;
          }
          h3 {
            font-size: ${isACM ? '11pt' : '10pt'};
            font-style: italic;
            font-weight: ${isLNCS ? 'bold' : 'normal'};
            margin: 0;
          }
          p {
            text-indent: ${settings.paragraphIndent};
            margin: 0 0 6pt;
          }
          p.no-indent {
            text-indent: 0;
          }
          /* Drop cap — IEEE Journal & Transactions first paragraph of Introduction */
          ${hasDropCap ? `
          p.drop-cap::first-letter {
            font-size: 34pt;
            font-weight: bold;
            float: left;
            line-height: 0.8;
            padding-top: 4pt;
            padding-right: 3pt;
            margin-bottom: -4pt;
          }` : ''}
          .front-matter-page {
            column-span: all;
            break-inside: avoid;
            page-break-inside: avoid;
            text-align: center;
            padding: 8pt 0;
          }
          .front-matter-page p {
            text-indent: 0;
            margin: 0 0 8pt;
          }
          .front-matter-cover p:first-child {
            margin-top: 72pt;
            font-size: 18pt;
            font-weight: bold;
            text-transform: uppercase;
          }
          .front-matter-toc p,
          .front-matter-glossary p {
            text-align: left;
          }
          .front-matter-page-break {
            column-span: all;
            break-after: page;
            page-break-after: always;
            height: 1px;
            margin: 0;
            padding: 0;
          }
          .abstract-text {
            font-size: 9pt;
            line-height: 1.2;
            font-style: ${abstractFontStyle};
            font-weight: ${abstractFontWeight};
            text-indent: 13.6pt;
            margin: 0 0 10pt;
            ${settings.abstractInset !== "0" ? `margin-left: ${settings.abstractInset}; margin-right: ${settings.abstractInset};` : ""}
          }
          .index-terms {
            font-size: 9pt;
            text-indent: 13.7pt;
            margin: 0 0 6pt;
            ${settings.abstractInset !== "0" ? `margin-left: ${settings.abstractInset}; margin-right: ${settings.abstractInset};` : ""}
          }
          .index-terms strong {
            font-style: italic;
            font-weight: bold;
          }
          /* ACM CCS Concepts block */
          .ccs-concepts {
            column-span: all;
            font-size: 9pt;
            margin: 6pt 0 10pt;
            text-indent: 0;
          }
          .ccs-title {
            font-size: 9pt;
            font-weight: bold;
            margin: 0 0 2pt;
            text-indent: 0;
          }
          .ccs-item {
            font-size: 9pt;
            margin: 0 0 2pt;
            text-indent: 0;
          }
          /* ACM Keywords block */
          .acm-keywords {
            column-span: all;
            font-size: 9pt;
            margin: 0 0 10pt;
            text-indent: 0;
          }
          /* ACM stacked authors (1-to-1 author/affiliation) */
          .author-stacked-container {
            column-span: all;
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 8pt 24pt;
            margin: 12pt 0 10pt;
          }
          .author-stacked {
            text-align: center;
            min-width: 120pt;
          }
          .reference-item {
            font-size: ${settings.referenceSize};
            line-height: 1.125;
            text-indent: -18pt;
            padding-left: 18pt;
            margin: 0 0 2.5pt;
          }
          .ieee-copyright {
            ${!isIEEE ? 'display: none;' : ''}
            position: fixed;
            left: ${settings.marginX};
            bottom: -1.3in;
            font-size: 8pt;
            text-indent: 0;
            text-align: left;
            color: #000;
            opacity: 0.6;
            column-span: all;
            z-index: 1000;
            background: transparent;
            margin: 0;
            padding: 0;
            width: auto;
          }
          .ieee-citation {
            color: inherit;
            font-weight: normal;
          }
          .ieee-citation a,
          .ieee-citation-link {
            color: inherit;
            text-decoration: none;
          }
          .reference-backlinks {
            margin-left: 4px;
            white-space: nowrap;
          }
          .reference-backlink {
            color: inherit;
            text-decoration: none;
            opacity: 0.75;
            font-size: 7pt;
          }
          .reference-item:target {
            background: rgba(59, 130, 246, 0.12);
          }
          .table-wrapper {
            break-inside: avoid-column;
            break-inside: avoid;
            page-break-inside: avoid;
            margin: 8pt 0;
          }
          .table-caption {
            text-align: center;
            font-size: ${settings.captionSize};
            font-variant: ${isACM || isLNCS ? 'normal' : 'small-caps'};
            font-weight: bold;
            text-indent: 0;
            margin: 8pt 0 4pt;
          }
          .figure-block {
            break-inside: avoid-column;
            break-inside: avoid;
            page-break-inside: avoid;
            margin: 8pt 0;
            text-align: center;
            width: 100%;
          }
          .figure-block img {
            width: 100% !important;
            max-width: 100% !important;
            height: auto !important;
            max-height: 140pt;
            object-fit: contain;
            display: block;
            margin: 0 auto 4pt;
          }
          .figure-caption {
            text-align: center;
            font-size: ${settings.captionSize};
            font-variant: ${isACM || isLNCS ? 'normal' : 'small-caps'};
            text-indent: 0;
            margin: 0;
          }
          .algorithm-block {
            border: 1px solid #333;
            margin: 10pt 0;
            padding: 6pt 8pt;
            font-size: 9pt;
            page-break-inside: avoid;
          }
          .algo-title {
            text-align: center;
            margin-bottom: 4pt;
            border-bottom: 1px solid #999;
            padding-bottom: 3pt;
          }
          .algo-body {
            font-family: "Courier New", Courier, monospace;
            font-size: 8pt;
            line-height: 1.4;
          }
          .algo-line {
            white-space: pre-wrap;
          }
          blockquote.equation {
            margin: 12pt 0;
            text-align: center;
            font-style: italic;
            page-break-inside: avoid;
          }
          table {
            width: 100%;
            table-layout: fixed;
            border-collapse: collapse;
            font-size: 8pt;
            margin: 4pt 0 6pt;
          }
          th, td {
            border: 1px solid #333;
            padding: 4px 8px;
            text-align: left;
            word-break: break-word;
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
      <input
        ref={imageInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleImageUpload}
      />

      <PageHeader
        title="Universal Research Formatter"
        subtitle={
          documentMode === "thesis"
            ? "Report/Thesis mode with front-matter builders, live preview, and export options."
            : "Conference-template-A4 strict formatting with live preview and export options."
        }
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
            <Badge tone="info">
              {documentMode === "thesis" ? "Thesis Mode" : "Template Lock"}
            </Badge>
          </div>
        }
      />

      <SectionCard
        title="Document Mode"
        description="Switch between Research Paper mode (IEEE / ACM / Springer) and Report/Thesis mode."
      >
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setDocumentMode("paper")}
            className={`rounded-lg border px-3 py-2 text-xs font-semibold transition-colors ${documentMode === "paper"
              ? "border-indigo-500 bg-indigo-600 text-white"
              : "border-zinc-700 bg-zinc-900 text-zinc-300 hover:bg-zinc-800"
              }`}
          >
            Research Paper
          </button>
          <button
            onClick={() => setDocumentMode("thesis")}
            className={`rounded-lg border px-3 py-2 text-xs font-semibold transition-colors ${documentMode === "thesis"
              ? "border-indigo-500 bg-indigo-600 text-white"
              : "border-zinc-700 bg-zinc-900 text-zinc-300 hover:bg-zinc-800"
              }`}
          >
            Report / Thesis
          </button>
        </div>
      </SectionCard>

      {/* Format Template Selector */}
      <SectionCard
        title="Format Template"
        description={
          documentMode === "thesis"
            ? "Format presets are still available, but Thesis mode forces single-column front matter with dedicated builders."
            : `Active: ${FORMAT_PRESETS[settings.format]?.name ?? "Conference"}. Select a family tab then choose a preset.`
        }
      >
        {/* Family Tabs */}
        <div className="mb-3 flex gap-1 rounded-lg border border-zinc-800 bg-zinc-900/80 p-1">
          {FORMAT_FAMILIES.map((fam) => (
            <button
              key={fam.key}
              onClick={() => setActiveFamily(fam.key)}
              className={`flex-1 rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${activeFamily === fam.key
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800"
                }`}
            >
              {fam.label}
            </button>
          ))}
        </div>
        {/* Preset Cards (filtered by active family) */}
        <div className="grid gap-2 md:grid-cols-3">
          {(Object.entries(FORMAT_PRESETS) as [DocumentFormat, FormatPreset][])
            .filter(([, preset]) => preset.family === activeFamily)
            .map(([key, preset]) => {
              const isDisabled = !preset.enabled;
              return (
                <button
                  key={key}
                  onClick={() => applyPreset(key)}
                  disabled={isDisabled}
                  className={`rounded-lg border p-3 text-left transition-all ${settings.format === key
                    ? "border-indigo-500 bg-indigo-500/10 ring-1 ring-indigo-500"
                    : "border-zinc-800 bg-zinc-900/50 hover:border-zinc-700"
                    } ${isDisabled ? "cursor-not-allowed opacity-60 hover:border-zinc-800" : ""}`}
                >
                  <div className="flex items-center gap-2">
                    <div
                      className={`h-3 w-3 rounded-full ${settings.format === key
                        ? "bg-indigo-500"
                        : "bg-zinc-700"
                        }`}
                    />
                    <span className="font-semibold text-sm text-zinc-100">
                      {preset.name}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-zinc-500">
                    {preset.description}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-400">
                      {preset.paperSize.toUpperCase()}
                    </span>
                    <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-400">
                      {preset.colCount} col
                    </span>
                    <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-400">
                      {preset.fontSize}
                    </span>
                    {isDisabled && (
                      <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-amber-300">
                        coming soon
                      </span>
                    )}
                  </div>
                </button>
              );
            })}
        </div>
      </SectionCard>

      {/* Raw Input + AI Format */}
      <SectionCard
        title="Raw Text Input"
        description="Paste raw paper content and apply strict Conference-template-A4 formatting."
      >
        <div className="space-y-2">
          <textarea
            value={rawInput}
            onChange={(e) => setRawInput(e.target.value)}
            onPaste={handlePaste}
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
            <button
              onClick={handleAiEnhance}
              disabled={isAiEnhancing || isFormatting || !rawInput.trim()}
              className="rounded-lg border border-indigo-700 bg-indigo-900/30 px-3 py-2 text-xs text-indigo-100 hover:bg-indigo-800/40 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isAiEnhancing
                ? "AI Enhancing..."
                : "AI Enhance (Grammar + Structure)"}
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
        description="Ribbon tools for quick editing, structure, tables, equations, and figures."
      >
        <div className="space-y-3">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-2">
              <div className="mb-2 text-[10px] uppercase tracking-wide text-zinc-500">
                History
              </div>
              <div className="flex flex-wrap gap-1.5">
                <ToolButton
                  label="↶ Undo"
                  onClick={() => editor?.chain().focus().undo().run()}
                />
                <ToolButton
                  label="↷ Redo"
                  onClick={() => editor?.chain().focus().redo().run()}
                />
              </div>
            </div>

            <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-2">
              <div className="mb-2 text-[10px] uppercase tracking-wide text-zinc-500">
                Text
              </div>
              <div className="flex flex-wrap gap-1.5">
                <ToolButton
                  label="B"
                  onClick={() => editor?.chain().focus().toggleBold().run()}
                  active={editor?.isActive("bold")}
                />
                <ToolButton
                  label="I"
                  onClick={() => editor?.chain().focus().toggleItalic().run()}
                  active={editor?.isActive("italic")}
                />
                <ToolButton
                  label="U"
                  onClick={() =>
                    editor?.chain().focus().toggleUnderline().run()
                  }
                  active={editor?.isActive("underline")}
                />
                <ToolButton
                  label="S"
                  onClick={() => editor?.chain().focus().toggleStrike().run()}
                  active={editor?.isActive("strike")}
                />
                <ToolButton
                  label="Code"
                  onClick={() => editor?.chain().focus().toggleCode().run()}
                  active={editor?.isActive("code")}
                />
                <ToolButton
                  label="X₂"
                  onClick={() =>
                    editor?.chain().focus().toggleSubscript().run()
                  }
                  active={editor?.isActive("subscript")}
                />
                <ToolButton
                  label="X²"
                  onClick={() =>
                    editor?.chain().focus().toggleSuperscript().run()
                  }
                  active={editor?.isActive("superscript")}
                />
              </div>
            </div>

            <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-2">
              <div className="mb-2 text-[10px] uppercase tracking-wide text-zinc-500">
                Headings & Blocks
              </div>
              <div className="flex flex-wrap gap-1.5">
                <ToolButton
                  label="P"
                  onClick={() => editor?.chain().focus().setParagraph().run()}
                />
                <ToolButton
                  label="H1"
                  onClick={() =>
                    editor?.chain().focus().toggleHeading({ level: 1 }).run()
                  }
                  active={editor?.isActive("heading", { level: 1 })}
                />
                <ToolButton
                  label="H2"
                  onClick={() =>
                    editor?.chain().focus().toggleHeading({ level: 2 }).run()
                  }
                  active={editor?.isActive("heading", { level: 2 })}
                />
                <ToolButton
                  label="H3"
                  onClick={() =>
                    editor?.chain().focus().toggleHeading({ level: 3 }).run()
                  }
                  active={editor?.isActive("heading", { level: 3 })}
                />
                <ToolButton
                  label="H4"
                  onClick={() =>
                    editor?.chain().focus().toggleHeading({ level: 4 }).run()
                  }
                  active={editor?.isActive("heading", { level: 4 })}
                />
                <ToolButton
                  label="Quote"
                  onClick={() =>
                    editor?.chain().focus().toggleBlockquote().run()
                  }
                  active={editor?.isActive("blockquote")}
                />
                <ToolButton
                  label="Code Block"
                  onClick={() =>
                    editor?.chain().focus().toggleCodeBlock().run()
                  }
                  active={editor?.isActive("codeBlock")}
                />
                <ToolButton
                  label="Rule"
                  onClick={() =>
                    editor?.chain().focus().setHorizontalRule().run()
                  }
                />
              </div>
            </div>

            <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-2">
              <div className="mb-2 text-[10px] uppercase tracking-wide text-zinc-500">
                Lists & Alignment
              </div>
              <div className="flex flex-wrap gap-1.5">
                <ToolButton
                  label="• List"
                  onClick={() =>
                    editor?.chain().focus().toggleBulletList().run()
                  }
                  active={editor?.isActive("bulletList")}
                />
                <ToolButton
                  label="1. List"
                  onClick={() =>
                    editor?.chain().focus().toggleOrderedList().run()
                  }
                  active={editor?.isActive("orderedList")}
                />
                <ToolButton
                  label="⬅"
                  onClick={() =>
                    editor?.chain().focus().setTextAlign("left").run()
                  }
                />
                <ToolButton
                  label="⬌"
                  onClick={() =>
                    editor?.chain().focus().setTextAlign("center").run()
                  }
                />
                <ToolButton
                  label="≡"
                  onClick={() =>
                    editor?.chain().focus().setTextAlign("justify").run()
                  }
                />
              </div>
            </div>

            <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-2">
              <div className="mb-2 text-[10px] uppercase tracking-wide text-zinc-500">
                Tables
              </div>
              <div className="flex flex-wrap gap-1.5">
                <ToolButton
                  label="Insert"
                  onClick={() => setIsTableDialogOpen(true)}
                />
                <ToolButton
                  label="+ Row"
                  onClick={() => editor?.chain().focus().addRowAfter().run()}
                  disabled={!isInTable}
                />
                <ToolButton
                  label="+ Col"
                  onClick={() => editor?.chain().focus().addColumnAfter().run()}
                  disabled={!isInTable}
                />
                <ToolButton
                  label="- Row"
                  onClick={() => editor?.chain().focus().deleteRow().run()}
                  disabled={!isInTable}
                  tone="danger"
                />
                <ToolButton
                  label="- Col"
                  onClick={() => editor?.chain().focus().deleteColumn().run()}
                  disabled={!isInTable}
                  tone="danger"
                />
                <ToolButton
                  label="Delete"
                  onClick={() => editor?.chain().focus().deleteTable().run()}
                  disabled={!isInTable}
                  tone="danger"
                />
              </div>
            </div>

            <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-2">
              <div className="mb-2 text-[10px] uppercase tracking-wide text-zinc-500">
                Insert
              </div>
              <div className="flex flex-wrap gap-1.5">
                <ToolButton label="🖼 Upload" onClick={openImagePicker} />
                <ToolButton label="🔗 URL" onClick={insertImageByUrl} />
                <ToolButton
                  label="∑ Equation"
                  onClick={() => setIsEquationDialogOpen(true)}
                />
                <ToolButton
                  label="Cover"
                  onClick={insertCoverPageBuilder}
                  disabled={documentMode !== "thesis"}
                />
                <ToolButton
                  label="Certificate"
                  onClick={insertCertificateBuilder}
                  disabled={documentMode !== "thesis"}
                />
                <ToolButton
                  label="Declaration"
                  onClick={insertDeclarationBuilder}
                  disabled={documentMode !== "thesis"}
                />
                <ToolButton
                  label="Acknowledge"
                  onClick={insertAcknowledgementBuilder}
                  disabled={documentMode !== "thesis"}
                />
                <ToolButton
                  label="TOC"
                  onClick={insertTocBuilder}
                  disabled={documentMode !== "thesis"}
                />
                <ToolButton
                  label="Glossary"
                  onClick={insertGlossaryBuilder}
                  disabled={documentMode !== "thesis"}
                />
              </div>
            </div>
          </div>

          <div className="grid gap-2 rounded-lg border border-zinc-800 bg-zinc-950/50 p-3 md:grid-cols-2">
            <label className="space-y-1 text-xs text-zinc-400">
              <span className="block">Formal Font Family</span>
              <select
                value={settings.fontFamily}
                onChange={(e) =>
                  setSettings((prev) => ({
                    ...prev,
                    fontFamily: e.target.value,
                  }))
                }
                className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1.5 text-xs text-zinc-200 focus:border-indigo-500 focus:outline-none"
              >
                {FORMAL_FONT_OPTIONS.map((option) => (
                  <option key={option.label} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-1 text-xs text-zinc-400">
              <span className="block">Body Font Size</span>
              <select
                value={settings.fontSize}
                onChange={(e) =>
                  setSettings((prev) => ({ ...prev, fontSize: e.target.value }))
                }
                className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1.5 text-xs text-zinc-200 focus:border-indigo-500 focus:outline-none"
              >
                {FONT_SIZE_OPTIONS.map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="rounded-lg border border-zinc-800 bg-zinc-950/50 px-3 py-2 text-[11px] text-zinc-400">
            Tip: Right-click inside the editor for quick actions. In Thesis
            mode, front-matter builders create one page per section with
            export-safe mappings.
          </div>
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
                fontFamily: settings.fontFamily,
                fontSize: settings.fontSize,
                lineHeight: 1.6,
                color: "#1a1a1a",
                fontStyle: "normal",
              }}
            >
              {editor ? (
                <EditorContent
                  editor={editor}
                  className="focus:outline-none editor-content"
                />
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
              {editor
                ?.getText()
                .split(/\s+/)
                .filter((w) => w.length > 0).length || 0}{" "}
              words
            </span>
            <span className="text-[11px] text-zinc-400">
              Auto-refreshes while typing (manual refresh optional)
            </span>
          </div>
        </SectionCard>

        {/* Right Panel: IEEE Preview (refreshed on demand) */}
        <SectionCard
          title={
            documentMode === "thesis" ? "Thesis Preview" : "Conference Preview"
          }
          description={
            documentMode === "thesis"
              ? "A4 · Front Matter + Body Layout"
              : "A4 · 2-column · Conference-template-A4"
          }
        >
          {/* Refresh Preview button bar */}
          <div className="flex items-center gap-3 mb-3">
            <button
              onClick={refreshPreview}
              disabled={isRefreshing}
              className={`rounded-lg px-4 py-2 text-sm font-semibold transition-all flex items-center gap-2 ${previewStale
                ? "bg-amber-500 text-white hover:bg-amber-400 ring-2 ring-amber-400/40 animate-pulse-once"
                : "bg-indigo-600 text-white hover:bg-indigo-500"
                } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              {isRefreshing ? (
                <>
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Formatting...
                </>
              ) : (
                <>
                  {previewStale ? "🔄 Refresh Preview" : "🔄 Refresh Preview"}
                </>
              )}
            </button>
            {previewStale && ieeeHtml && (
              <span className="text-[11px] text-amber-400 flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-amber-400 inline-block animate-pulse" />
                Editor changed — click Refresh to update preview
              </span>
            )}
            {!previewStale && ieeeHtml && (
              <span className="text-[11px] text-emerald-400 flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
                Preview up to date
              </span>
            )}
          </div>

          <div
            className="overflow-auto rounded-2xl border border-zinc-800 bg-zinc-900 p-4"
            style={{ maxHeight: "75vh", minHeight: "500px" }}
          >
            <div className="flex flex-col items-center gap-4">
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
                    fontFamily: settings.fontFamily,
                    fontSize: settings.fontSize,
                    lineHeight: 1.14,
                    padding: `${settings.marginTop} ${settings.marginX} ${settings.marginBottom}`,
                    columnCount: settings.colCount,
                    columnGap: settings.colGap,
                    columnFill: "balance",
                    textAlign: "justify",
                    hyphens: "auto",
                    overflowWrap: "break-word",
                    color: "#000",
                    minHeight: "600px",
                  }}
                >
                  {ieeeHtml ? (
                    <div
                      dangerouslySetInnerHTML={{ __html: ieeeHtml }}
                      className="ieee-preview-html"
                    />
                  ) : (
                    <div
                      className="text-zinc-400 text-center py-20 text-[10pt]"
                      style={{ columnSpan: "all" }}
                    >
                      <div className="text-3xl mb-2 opacity-30">📝</div>
                      <p>
                        Format your paper first, then click{" "}
                        <strong>Refresh Preview</strong>
                      </p>
                      <p className="text-[8pt] mt-1 opacity-70">
                        Preview updates when you click the button above
                      </p>
                    </div>
                  )}
                </div>

                {/* Format badge */}
                <div className="absolute top-2 right-2 bg-blue-600 text-white px-1.5 py-0.5 rounded text-[8px] font-medium shadow-sm">
                  {documentMode === "thesis" ? "Thesis" : "Conference A4"}
                </div>

                {/* Stale overlay */}
                {previewStale && ieeeHtml && (
                  <div className="absolute inset-0 bg-white/30 flex items-center justify-center rounded pointer-events-none">
                    <span className="bg-amber-500/90 text-white text-xs font-semibold px-3 py-1.5 rounded-lg shadow pointer-events-auto">
                      Preview outdated — click Refresh
                    </span>
                  </div>
                )}

                {/* Refreshing overlay */}
                {isRefreshing && (
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
                <span className="text-[10px] text-zinc-400 font-medium">
                  IEEE Format Specs
                </span>
                <div className="flex items-center gap-1">
                  <div
                    className={`w-1.5 h-1.5 rounded-full ${previewStale ? "bg-amber-400 animate-pulse" : "bg-emerald-500"}`}
                  ></div>
                  <span className="text-[9px] text-zinc-500">
                    {previewStale ? "Stale" : "Current"}
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
                  <span className="text-zinc-300">
                    {settings.fontSize}{" "}
                    {FORMAL_FONT_OPTIONS.find(
                      (option) => option.value === settings.fontFamily,
                    )?.label.split(" (")[0] ?? "Times New Roman"}
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-zinc-500">Words:</span>
                  <span className="text-zinc-300">
                    {editor
                      ?.getText()
                      .split(/\s+/)
                      .filter((w) => w.length > 0).length || 0}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </SectionCard>
      </div>

      {/* Export Status */}
      <TableInsertDialog
        isOpen={isTableDialogOpen}
        onClose={() => setIsTableDialogOpen(false)}
        onInsert={handleInsertTable}
      />

      <EquationEditor
        isOpen={isEquationDialogOpen}
        onClose={() => setIsEquationDialogOpen(false)}
        onInsert={handleInsertEquation}
      />

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
                  if (item.disabled) return;
                  item.action?.();
                  setContextMenu((prev) => ({ ...prev, visible: false }));
                }}
                disabled={item.disabled}
                className={`flex w-full items-center justify-between px-3 py-1.5 text-xs ${item.disabled
                  ? "cursor-not-allowed text-zinc-600"
                  : "text-zinc-300 hover:bg-zinc-800"
                  }`}
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
            AI Copilot (Beta)
          </span>
          <Badge tone="info">Live</Badge>
        </div>
        <p className="mt-1 text-[11px] text-zinc-500">
          Ask for formatting actions like: “make section headings italic”, “bold
          selected line”, or “set one column”.
        </p>
        <div className="mt-3 flex gap-2">
          <input
            value={aiCommand}
            onChange={(e) => setAiCommand(e.target.value)}
            placeholder="Type a formatting command..."
            disabled={isAiCopilotRunning}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                runAiCopilot();
              }
            }}
            className="flex-1 rounded-lg border border-zinc-800 bg-zinc-900/50 px-3 py-2 text-xs text-zinc-100 placeholder:text-zinc-600 focus:border-indigo-500 focus:outline-none"
          />
          <button
            onClick={runAiCopilot}
            disabled={isAiCopilotRunning || !aiCommand.trim()}
            className="rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
          >
            {isAiCopilotRunning ? "Running..." : "Send"}
          </button>
        </div>
        {aiCopilotStatus && (
          <p className="mt-2 text-[11px] text-emerald-300">{aiCopilotStatus}</p>
        )}
      </div>
    </div>
  );
}

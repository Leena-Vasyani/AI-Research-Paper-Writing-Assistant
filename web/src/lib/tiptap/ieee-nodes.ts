import { mergeAttributes, Node } from "@tiptap/core";
import Heading from "@tiptap/extension-heading";
import Paragraph from "@tiptap/extension-paragraph";

type ParagraphRole =
  | "none"
  | "abstract"
  | "keywords"
  | "reference"
  | "tableCaption"
  | "copyright"
  | "authorName"
  | "authorLine"
  | "algoTitle"
  | "algoLine";

const CONTAINER_CLASS_REGEX =
  /\b(?:author-grid|author-block|table-wrapper|algorithm-block|algo-body)\b/;

export const IeeeContainer = Node.create({
  name: "ieeeContainer",
  group: "block",
  content: "block*",
  defining: true,

  addAttributes() {
    return {
      className: {
        default: null,
        parseHTML: (element: HTMLElement) => {
          const className = (element.getAttribute("class") || "").trim();
          return CONTAINER_CLASS_REGEX.test(className) ? className : null;
        },
      },
    };
  },

  parseHTML() {
    return [
      { tag: "div.author-grid" },
      { tag: "div.author-block" },
      { tag: "div.table-wrapper" },
      { tag: "div.algorithm-block" },
      { tag: "div.algo-body" },
    ];
  },

  renderHTML({ node, HTMLAttributes }) {
    const className = (node.attrs.className as string | null) ?? undefined;
    return [
      "div",
      mergeAttributes(HTMLAttributes, className ? { class: className } : {}),
      0,
    ];
  },
});

export const IeeeHeading = Heading.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      ieeeRole: {
        default: "section",
        parseHTML: (element: HTMLElement) => {
          if (element.classList.contains("paper-title")) return "title";
          return "section";
        },
      },
    };
  },

  renderHTML({ node, HTMLAttributes }) {
    const level = node.attrs.level;
    const classes: string[] = [];

    if (level === 1) {
      classes.push(node.attrs.ieeeRole === "title" ? "paper-title" : "ieee-heading");
    } else if (level === 2) {
      classes.push("ieee-subheading");
    }

    const className = [HTMLAttributes.class, ...classes].filter(Boolean).join(" ");
    return [
      `h${level}`,
      mergeAttributes(HTMLAttributes, className ? { class: className } : {}),
      0,
    ];
  },
});

export const IeeeParagraph = Paragraph.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      ieeeRole: {
        default: "none" as ParagraphRole,
        parseHTML: (element: HTMLElement): ParagraphRole => {
          if (element.classList.contains("abstract-text")) return "abstract";
          if (element.classList.contains("index-terms")) return "keywords";
          if (element.classList.contains("reference-item")) return "reference";
          if (element.classList.contains("table-caption")) return "tableCaption";
          if (element.classList.contains("ieee-copyright")) return "copyright";
          if (element.classList.contains("author-name")) return "authorName";
          if (element.classList.contains("author-line")) return "authorLine";
          if (element.classList.contains("algo-title")) return "algoTitle";
          if (element.classList.contains("algo-line")) return "algoLine";
          return "none";
        },
      },
      noIndent: {
        default: false,
        parseHTML: (element: HTMLElement) => element.classList.contains("no-indent"),
      },
    };
  },

  renderHTML({ node, HTMLAttributes }) {
    const classes: string[] = [];
    const role = node.attrs.ieeeRole as ParagraphRole;

    if (node.attrs.noIndent) classes.push("no-indent");
    if (role === "abstract") classes.push("abstract-text");
    if (role === "keywords") classes.push("index-terms");
    if (role === "reference") classes.push("reference-item");
    if (role === "tableCaption") classes.push("table-caption");
    if (role === "copyright") classes.push("ieee-copyright");
    if (role === "authorName") classes.push("author-name");
    if (role === "authorLine") classes.push("author-line");
    if (role === "algoTitle") classes.push("algo-title");
    if (role === "algoLine") classes.push("algo-line");

    const className = [HTMLAttributes.class, ...classes].filter(Boolean).join(" ");
    return [
      "p",
      mergeAttributes(HTMLAttributes, className ? { class: className } : {}),
      0,
    ];
  },
});

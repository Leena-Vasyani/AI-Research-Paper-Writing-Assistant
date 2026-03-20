/**
 * IEEE Paper Formatter
 * Deterministic formatter used by Universal Research Formatter.
 *
 * Produces HTML that follows the IEEE Conference-template-A4 layout:
 *   - Title: 24pt, centered
 *   - Author grid: centered below title
 *   - Abstract: "Abstract—" prefix, 9pt body
 *   - Keywords / Index Terms: "Keywords—" prefix, 9pt
 *   - Level-1 headings: Roman numeral prefix, SMALL-CAPS, centered, 10pt
 *   - Level-2 headings: Letter prefix, italic, left-aligned, 10pt
 *   - Body: 10pt, justified, first-para-after-heading NOT indented
 *   - Tables: preceded by "TABLE N" caption when detected
 *   - Equations: display & inline math
 *   - Algorithm blocks: bordered box
 *   - Inline citations: [1], [1,2], [1-3] styled
 *   - References: hanging indent, 8pt
 *   - Copyright footer line
 */

export type HeadingKind =
  | "none"
  | "abstract"
  | "references"
  | "appendix"
  | "acknowledgment"
  | "section"
  | "subsection";

export type HeadingDetection = {
  kind: HeadingKind;
  title: string;
};

export type InlineFormatResult = {
  html: string;
  equationCount: number;
};

export type CitationContext = {
  getNextCitationId: () => string;
  registerCitation: (referenceNumber: number, citationId: string) => void;
};

export type TableFormatResult = {
  html: string;
  equationCount: number;
};

export type AuthorBlock = {
  name: string;
  details: string[];
};

const IEEE_COPYRIGHT_FOOTER = "XXX-X-XXXX-XXXX-X/XX/$XX.00 &copy;20XX IEEE";

const TEMPLATE_INSTRUCTION_PATTERNS: RegExp[] = [
  /^paper\s+title\*/i,
  /^\*?note:\s*sub-?titles?\s+are\s+not\s+captured\s+in\s+xplore/i,
  /^line\s*[1-6]\s*:/i,
  /^this\s+electronic\s+document\s+is\s+a\s+[""]?live[""]?\s+template/i,
  /^this\s+template,\s*modified\s+in\s+ms\s+word/i,
  /^all\s+margins,\s*column\s+widths,\s*line\s+spaces/i,
  /^identify\s+applicable\s+funding\s+agency\s+here/i,
  /^first,\s*confirm\s+that\s+you\s+have\s+the\s+correct\s+template/i,
  /^the\s+template\s+is\s+used\s+to\s+format\s+your\s+paper/i,
  /^do\s+not\s+use\s+symbols,\s*special\s+characters,\s*footnotes,\s*or\s+math/i,
  // Code-block language labels that sometimes leak into pasted text
  /^(?:plaintext|python|java|javascript|typescript|c\+\+|ruby|matlab|pseudo-?code|code)$/i,
];

const LATEX_SYMBOLS: Record<string, string> = {
  // Lowercase Greek
  "\\alpha": "&alpha;",
  "\\beta": "&beta;",
  "\\gamma": "&gamma;",
  "\\delta": "&delta;",
  "\\epsilon": "&epsilon;",
  "\\zeta": "&zeta;",
  "\\eta": "&eta;",
  "\\theta": "&theta;",
  "\\iota": "&iota;",
  "\\kappa": "&kappa;",
  "\\lambda": "&lambda;",
  "\\mu": "&mu;",
  "\\nu": "&nu;",
  "\\xi": "&xi;",
  "\\pi": "&pi;",
  "\\rho": "&rho;",
  "\\sigma": "&sigma;",
  "\\tau": "&tau;",
  "\\upsilon": "&upsilon;",
  "\\phi": "&phi;",
  "\\chi": "&chi;",
  "\\psi": "&psi;",
  "\\omega": "&omega;",
  // Uppercase Greek
  "\\Alpha": "&Alpha;",
  "\\Beta": "&Beta;",
  "\\Gamma": "&Gamma;",
  "\\Delta": "&Delta;",
  "\\Epsilon": "&Epsilon;",
  "\\Zeta": "&Zeta;",
  "\\Eta": "&Eta;",
  "\\Theta": "&Theta;",
  "\\Lambda": "&Lambda;",
  "\\Xi": "&Xi;",
  "\\Pi": "&Pi;",
  "\\Sigma": "&Sigma;",
  "\\Phi": "&Phi;",
  "\\Psi": "&Psi;",
  "\\Omega": "&Omega;",
  // Operators and relations
  "\\infty": "&infin;",
  "\\approx": "&asymp;",
  "\\neq": "&ne;",
  "\\leq": "&le;",
  "\\geq": "&ge;",
  "\\pm": "&plusmn;",
  "\\times": "&times;",
  "\\div": "&divide;",
  "\\partial": "&part;",
  "\\nabla": "&nabla;",
  "\\oplus": "&oplus;",
  "\\otimes": "&otimes;",
  "\\cdot": "&middot;",
  "\\sum": "&sum;",
  "\\prod": "&prod;",
  "\\int": "&int;",
  "\\forall": "&forall;",
  "\\exists": "&exist;",
  "\\in": "&isin;",
  "\\notin": "&notin;",
  "\\subset": "&sub;",
  "\\supset": "&sup;",
  "\\cup": "&cup;",
  "\\cap": "&cap;",
  "\\to": "&rarr;",
  "\\rightarrow": "&rarr;",
  "\\leftarrow": "&larr;",
  "\\Rightarrow": "&rArr;",
  "\\Leftarrow": "&lArr;",
  "\\ldots": "&hellip;",
  "\\cdots": "&ctdot;",
  "\\log": "log",
  "\\exp": "exp",
  "\\sin": "sin",
  "\\cos": "cos",
  "\\tan": "tan",
  "\\max": "max",
  "\\min": "min",
  "\\lim": "lim",
};

const MAIN_SECTION_KEYWORDS: Array<{ regex: RegExp; canonical: string }> = [
  { regex: /^introduction$/i, canonical: "Introduction" },
  { regex: /^related\s+work$/i, canonical: "Related Work" },
  { regex: /^background$/i, canonical: "Background" },
  { regex: /^literature\s+review$/i, canonical: "Literature Review" },
  { regex: /^method(?:ology)?$/i, canonical: "Methodology" },
  { regex: /^proposed\s+method$/i, canonical: "Proposed Method" },
  { regex: /^system(?:\s+architecture)?$/i, canonical: "System Architecture" },
  { regex: /^implementation$/i, canonical: "Implementation" },
  { regex: /^experimental\s+setup$/i, canonical: "Experimental Setup" },
  { regex: /^results?\s*(?:and\s+discussion)?$/i, canonical: "Results" },
  { regex: /^evaluation$/i, canonical: "Evaluation" },
  { regex: /^discussion$/i, canonical: "Discussion" },
  { regex: /^conclusions?$/i, canonical: "Conclusion" },
  { regex: /^future\s+work$/i, canonical: "Future Work" },
];

/* ───────── helpers ───────── */

export function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function collapseWhitespace(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

function isTemplateInstructionLine(value: string): boolean {
  const cleaned = collapseWhitespace(value);
  if (!cleaned) return false;
  return TEMPLATE_INSTRUCTION_PATTERNS.some((pattern) => pattern.test(cleaned));
}

function stripHeadingInstructionSuffix(value: string): string {
  return collapseWhitespace(value).replace(/\s*\(heading\s*\d+\)\s*$/i, "");
}

function toTitleCase(value: string): string {
  return collapseWhitespace(value)
    .split(" ")
    .map((word) => {
      if (!word) return word;
      if (/^[A-Z0-9]{2,}$/.test(word)) return word;
      return `${word[0].toUpperCase()}${word.slice(1).toLowerCase()}`;
    })
    .join(" ");
}

export function sanitizeTemplateRestrictedText(value: string): string {
  return collapseWhitespace(
    value
      .replace(/\$\$[\s\S]+?\$\$/g, " ")
      .replace(/\$[^$\n]+\$/g, " ")
      .replace(/\\\[[\s\S]+?\\\]/g, " ")
      .replace(/\\\([^)]+\\\)/g, " ")
      .replace(/\\[A-Za-z]+\{?[^}\s]*\}?/g, " ")
      .replace(/\*?critical\s*:.*$/i, " ")
      .replace(/this\s+template[^.]*\./gi, " ")
      .replace(/this\s+electronic\s+document[^.]*\./gi, " ")
      .replace(/identify\s+applicable\s+funding\s+agency[^.]*\./gi, " ")
      .replace(/all\s+margins,\s*column\s+widths[^.]*\./gi, " ")
      .replace(/do\s+not\s+use\s+symbols[^.]*\./gi, " ")
      .replace(/[*†‡§¶^_~{}]/g, " ")
      .replace(/[^A-Za-z0-9\s,.;:()\-/'"]/g, " "),
  );
}

/* ───────── Roman numerals ───────── */

export function toRoman(num: number): string {
  const map: [number, string][] = [
    [1000, "M"],
    [900, "CM"],
    [500, "D"],
    [400, "CD"],
    [100, "C"],
    [90, "XC"],
    [50, "L"],
    [40, "XL"],
    [10, "X"],
    [9, "IX"],
    [5, "V"],
    [4, "IV"],
    [1, "I"],
  ];
  let result = "";
  let n = num;
  for (const [value, numeral] of map) {
    while (n >= value) {
      result += numeral;
      n -= value;
    }
  }
  return result;
}

export function toLetterLabel(num: number): string {
  // 1 → A, 2 → B, ...
  return String.fromCharCode(64 + num);
}

/* ───────── heading detection ───────── */

function normalizeMainSectionTitle(value: string): string {
  const cleaned = stripHeadingInstructionSuffix(
    value
      .replace(/^section\s+/i, "")
      .replace(/^(?:\d+|[ivxlcdm]+)(?:[.)\-]|\s)\s*/i, "")
      .replace(/[.:]\s*$/, ""),
  );

  for (const candidate of MAIN_SECTION_KEYWORDS) {
    if (candidate.regex.test(cleaned)) {
      return candidate.canonical;
    }
  }

  return toTitleCase(cleaned);
}

function normalizeSubsectionTitle(value: string): string {
  return stripHeadingInstructionSuffix(value).replace(/[.:]\s*$/, "");
}

function looksHeadingLike(value: string): boolean {
  const cleaned = collapseWhitespace(value);
  if (!cleaned || cleaned.length > 90 || cleaned.length < 3) return false;
  if (/[.?!]$/.test(cleaned)) return false;
  // Reject lines starting with digits followed by colon (algorithm pseudocode)
  if (/^\d+\s*:/.test(cleaned)) return false;

  const words = cleaned.split(" ");
  if (words.length > 12) return false;

  const letters = cleaned.replace(/[^A-Za-z]/g, "");
  if (!letters) return false;

  const uppercaseLetters = letters.replace(/[^A-Z]/g, "").length;
  const upperRatio = uppercaseLetters / letters.length;
  const titleCase = words.every((word) => /^[A-Z][A-Za-z0-9-]*$/.test(word));
  return upperRatio >= 0.72 || titleCase;
}

function detectHeading(line: string): HeadingDetection {
  const trimmed = stripHeadingInstructionSuffix(line);
  if (!trimmed) return { kind: "none", title: "" };
  if (isTemplateInstructionLine(trimmed)) return { kind: "none", title: "" };

  if (/^(?:abstract|summary)\s*:?\s*$/i.test(trimmed)) {
    return { kind: "abstract", title: "Abstract" };
  }
  if (/^(?:references|bibliography)\s*:?\s*$/i.test(trimmed)) {
    return { kind: "references", title: "References" };
  }
  if (/^acknowledg?ments?\s*:?\s*$/i.test(trimmed)) {
    return { kind: "acknowledgment", title: "Acknowledgment" };
  }
  if (/^appendix(?:\s+[A-Z])?\s*:?\s*$/i.test(trimmed)) {
    return { kind: "appendix", title: toTitleCase(trimmed) };
  }

  // Subsection: letter-prefixed  e.g.  "A. Data Collection"
  const subsectionLettered = trimmed.match(/^([A-Z])[.)]\s+(.+)$/);
  if (subsectionLettered) {
    const title = normalizeSubsectionTitle(subsectionLettered[2]);
    return { kind: "subsection", title };
  }

  // Subsection: decimal  e.g.  "2.1 Approach"
  const subsectionDecimal = trimmed.match(/^(\d+\.\d+(?:\.\d+)?)\s+(.+)$/);
  if (subsectionDecimal) {
    const title = normalizeSubsectionTitle(subsectionDecimal[2]);
    return { kind: "subsection", title };
  }

  // Numbered main section  e.g.  "1. INTRODUCTION" or "III. RESULTS"
  // Must use period or parenthesis after number (NOT colon — colons indicate pseudocode)
  // Must have heading-length text (≤8 words) to avoid matching list items
  const numberedMain = trimmed.match(
    /^(?:section\s+)?(?:\d+|[ivxlcdm]+)[.)]\s+(.+)$/i,
  );
  if (numberedMain) {
    const afterNumber = numberedMain[1].trim();
    const wordCount = afterNumber.split(/\s+/).length;
    if (wordCount <= 8 && afterNumber.length <= 80) {
      return {
        kind: "section",
        title: normalizeMainSectionTitle(numberedMain[1]),
      };
    }
  }

  // Keyword-only heading  e.g.  "Introduction"
  const keywordOnly = normalizeMainSectionTitle(trimmed);
  for (const candidate of MAIN_SECTION_KEYWORDS) {
    if (candidate.regex.test(keywordOnly)) {
      return { kind: "section", title: candidate.canonical };
    }
  }

  if (looksHeadingLike(trimmed)) {
    return { kind: "section", title: normalizeMainSectionTitle(trimmed) };
  }

  return { kind: "none", title: "" };
}

/* ───────── math conversion ───────── */

function convertMath(mathText: string): string {
  let out = escapeHtml(collapseWhitespace(mathText));

  for (const [latex, htmlEntity] of Object.entries(LATEX_SYMBOLS)) {
    const escapedPattern = latex.replace(/\\/g, "\\\\");
    out = out.replace(new RegExp(escapedPattern, "g"), htmlEntity);
  }

  out = out.replace(
    /([A-Za-z0-9)\]])\_{([^{}]+)}/g,
    (_whole, base: string, sub: string) =>
      `${base}<sub>${escapeHtml(sub)}</sub>`,
  );
  out = out.replace(
    /([A-Za-z0-9)\]])_([A-Za-z0-9])/g,
    (_whole, base: string, sub: string) => `${base}<sub>${sub}</sub>`,
  );
  out = out.replace(
    /([A-Za-z0-9)\]])\^{([^{}]+)}/g,
    (_whole, base: string, sup: string) =>
      `${base}<sup>${escapeHtml(sup)}</sup>`,
  );
  out = out.replace(
    /([A-Za-z0-9)\]])\^([A-Za-z0-9])/g,
    (_whole, base: string, sup: string) => `${base}<sup>${sup}</sup>`,
  );
  out = out.replace(
    /\\frac\s*{([^{}]+)}{([^{}]+)}/g,
    (_whole, numerator: string, denominator: string) =>
      `(${escapeHtml(numerator)})/(${escapeHtml(denominator)})`,
  );
  out = out.replace(/\\sqrt\s*{([^{}]+)}/g, (_whole, inner: string) => {
    return `&radic;(${escapeHtml(inner)})`;
  });
  out = out.replace(/\\text{([^{}]+)}/g, (_whole, inner: string) => {
    return escapeHtml(inner);
  });
  out = out.replace(/\\textbf{([^{}]+)}/g, (_whole, inner: string) => {
    return `<strong>${escapeHtml(inner)}</strong>`;
  });
  out = out.replace(/\\emph{([^{}]+)}/g, (_whole, inner: string) => {
    return `<em>${escapeHtml(inner)}</em>`;
  });
  out = out.replace(/\\[A-Za-z]+/g, "");

  return out;
}

/* ───────── inline content ───────── */

export function processInlineContent(
  text: string,
  citationContext?: CitationContext,
): InlineFormatResult {
  let equationCount = 0;
  let out = text; // work on RAW text — escape HTML only on non-math segments

  // Step 1: Extract math into placeholders (before HTML escaping)
  const placeholders: { key: string; html: string }[] = [];

  // Display math $$...$$
  out = out.replace(/\$\$([\s\S]+?)\$\$/g, (_whole, math: string) => {
    equationCount += 1;
    const key = `__MATH_PH_${placeholders.length}__`;
    placeholders.push({
      key,
      html: `<blockquote class="equation"><em>${convertMath(math)}</em></blockquote>`,
    });
    return key;
  });

  // Display math \[...\]
  out = out.replace(/\\\[([\s\S]+?)\\\]/g, (_whole, math: string) => {
    equationCount += 1;
    const key = `__MATH_PH_${placeholders.length}__`;
    placeholders.push({
      key,
      html: `<blockquote class="equation"><em>${convertMath(math)}</em></blockquote>`,
    });
    return key;
  });

  // Inline math $...$
  out = out.replace(/\$([^$\n]+)\$/g, (_whole, math: string) => {
    equationCount += 1;
    const key = `__MATH_PH_${placeholders.length}__`;
    placeholders.push({
      key,
      html: `<em class="math-inline">${convertMath(math)}</em>`,
    });
    return key;
  });

  // Step 2: NOW escape HTML on the remaining (non-math) text
  out = escapeHtml(out);

  // Step 3: Inline citations: [1], [1,2], [1-3], [1, 2, 3]
  out = out.replace(
    /\[(\d+(?:\s*[,\-–]\s*\d+)*)\]/g,
    (_whole, inner: string) => {
      const linkedInner = inner.replace(/\d+/g, (num) => {
        const referenceNumber = Number.parseInt(num, 10);
        const citationId = citationContext?.getNextCitationId();
        if (
          citationContext &&
          Number.isFinite(referenceNumber) &&
          referenceNumber > 0 &&
          citationId
        ) {
          citationContext.registerCitation(referenceNumber, citationId);
        }
        return `<a${citationId ? ` id="${citationId}"` : ""} class="ieee-citation-link" href="#ref-${num}">[${num}]</a>`;
      });
      return `<span class="ieee-citation">${linkedInner}</span>`;
    },
  );

  // Step 4: Restore math placeholders
  for (const ph of placeholders) {
    out = out.replace(ph.key, ph.html);
  }

  return { html: out, equationCount };
}

/* ───────── table handling ───────── */

function isTableSeparatorLine(value: string): boolean {
  const trimmed = value.trim();
  // Markdown pipe-style: |---|---|
  if (/^\|?[\s:\-]+\|[\s|:\-]+\|?$/.test(trimmed)) return true;
  // ASCII art +----+----+ style
  if (/^\+[\-=+]+\+$/.test(trimmed)) return true;
  return false;
}

function splitTableRow(line: string): string[] {
  const trimmed = line.trim();
  if (!trimmed) return [];

  const pipeCount = (trimmed.match(/\|/g) || []).length;
  if (pipeCount >= 2) {
    const withoutEdges = trimmed.replace(/^\|/, "").replace(/\|$/, "");
    return withoutEdges.split("|").map((cell) => collapseWhitespace(cell));
  }

  if (trimmed.includes("\t")) {
    return trimmed
      .split(/\t+/)
      .map((cell) => collapseWhitespace(cell))
      .filter((cell) => cell.length > 0);
  }

  return [];
}

function isTableLine(line: string): boolean {
  if (isTableSeparatorLine(line)) return true;
  return splitTableRow(line).length >= 2;
}

/**
 * Detect a table caption line like "Table 1: Results" or "TABLE I. Accuracy".
 * Returns the caption text or null.
 */
function parseTableCaption(line: string): string | null {
  const trimmed = collapseWhitespace(line);
  const match = trimmed.match(
    /^(?:TABLE|Table)\s+(?:[IVXLCM]+|\d+)[.:]?\s*(.*)/i,
  );
  if (match) {
    return trimmed; // return the full caption text
  }
  return null;
}

function convertTable(lines: string[], caption?: string): TableFormatResult {
  const rows: string[][] = [];
  let equationCount = 0;

  for (const line of lines) {
    if (isTableSeparatorLine(line)) continue;
    const row = splitTableRow(line);
    if (row.length >= 2) {
      rows.push(row);
    }
  }

  if (!rows.length) return { html: "", equationCount: 0 };

  const columnCount = Math.max(...rows.map((row) => row.length));
  const normalizedRows = rows.map((row) => {
    const padded = [...row];
    while (padded.length < columnCount) padded.push("");
    return padded;
  });

  const [headerRow, ...bodyRows] = normalizedRows;

  let html = "";

  // Table caption above the table (IEEE style: caption goes ABOVE tables)
  if (caption) {
    html += `<p class="table-caption">${escapeHtml(caption)}</p>`;
  }

  html += "<table><thead><tr>";
  for (const headerCell of headerRow) {
    const rendered = processInlineContent(headerCell);
    equationCount += rendered.equationCount;
    html += `<th>${rendered.html}</th>`;
  }
  html += "</tr></thead><tbody>";

  for (const row of bodyRows) {
    html += "<tr>";
    for (const cell of row) {
      const rendered = processInlineContent(cell);
      equationCount += rendered.equationCount;
      html += `<td>${rendered.html}</td>`;
    }
    html += "</tr>";
  }

  html += "</tbody></table>";

  // Wrap in a div to prevent column/page breaks inside the table
  const wrappedHtml = `<div class="table-wrapper">${html}</div>`;
  return { html: wrappedHtml, equationCount };
}

/* ───────── algorithm detection ───────── */

function isAlgorithmStart(line: string): { title: string } | null {
  const trimmed = collapseWhitespace(line);
  const match = trimmed.match(
    /^(?:Algorithm|ALGORITHM)\s+(\d+)\s*[:.]\s*(.*)/i,
  );
  if (match) {
    const num = match[1];
    const name = match[2] ? match[2].replace(/[.:]\s*$/, "") : "";
    return { title: name ? `Algorithm ${num}: ${name}` : `Algorithm ${num}` };
  }
  return null;
}

function isAlgorithmBodyLine(line: string): boolean {
  const trimmed = line.trimStart();
  // Lines that look like pseudocode: "1:", "Input:", "Output:", "for", "while", "if", "end", indented, etc.
  if (/^\d+\s*[:.]/.test(trimmed)) return true;
  if (/^(?:Input|Output|Require|Ensure|Return|Initialize)\s*:/i.test(trimmed))
    return true;
  if (
    /^(?:for|while|if|else|end|repeat|until|do|function|procedure)\b/i.test(
      trimmed,
    )
  )
    return true;
  // Separator lines (dashes, equals, mixed) used in algorithm boxes
  if (/^[-=_]{5,}$/.test(trimmed.replace(/\s/g, ""))) return true;
  // Indented lines (at least 2 spaces) are part of the algorithm body
  if (line.startsWith("  ") || line.startsWith("\t")) return true;
  // Lines that start with common pseudo-operators like FOR, ELSE IF
  if (/^(?:ELSE\s+IF|ELSE|END\s+(?:IF|FOR|WHILE))\b/i.test(trimmed))
    return true;
  return false;
}

function renderAlgorithmBlock(title: string, bodyLines: string[]): string {
  const bodyHtml = bodyLines
    .map((line) => {
      const trimmed = collapseWhitespace(line);
      const escaped = escapeHtml(trimmed);
      // Indent nested lines
      const leadingSpaces = line.match(/^(\s*)/)?.[1]?.length ?? 0;
      const indentLevel = Math.min(Math.floor(leadingSpaces / 2), 4);
      const paddingLeft = indentLevel * 16;
      return `<p class="algo-line" style="margin:0;padding-left:${paddingLeft}px;text-indent:0">${escaped}</p>`;
    })
    .join("");

  return (
    `<div class="algorithm-block">` +
    `<p class="algo-title"><strong>${escapeHtml(title)}</strong></p>` +
    `<div class="algo-body">${bodyHtml}</div>` +
    `</div>`
  );
}

/* ───────── reference parsing ───────── */

function parseReferenceStart(
  line: string,
): { label: string; content: string } | null {
  const trimmed = collapseWhitespace(line);

  const bracketed = trimmed.match(/^\[(\d+)\]\s*(.*)$/);
  if (bracketed) {
    return { label: `[${bracketed[1]}]`, content: bracketed[2] };
  }

  const numbered = trimmed.match(/^(\d+)[.)]\s*(.*)$/);
  if (numbered) {
    return { label: `[${numbered[1]}]`, content: numbered[2] };
  }
  return null;
}

/* ───────── front-matter detection ───────── */

function isFrontMatterBoundaryLine(value: string): boolean {
  const cleaned = collapseWhitespace(value);
  if (!cleaned) return false;
  if (/^abstract\b/i.test(cleaned)) return true;
  if (/^(?:keywords?|index terms?)\b/i.test(cleaned)) return true;
  if (/^(?:references|bibliography)\b/i.test(cleaned)) return true;
  if (/^(?:publication\s+date|journal|conference)\s*:/i.test(cleaned))
    return false;
  if (/^(?:\d+|[IVXLCM]+)[.)]?\s+[A-Za-z]/i.test(cleaned)) return true;
  if (/^[A-Z][.)]\s+\S+/.test(cleaned)) return true;
  return MAIN_SECTION_KEYWORDS.some((item) =>
    item.regex.test(cleaned.replace(/[.:]\s*$/, "")),
  );
}

function looksLikeTitle(value: string): boolean {
  const cleaned = collapseWhitespace(value);
  if (!cleaned || cleaned.length < 8 || cleaned.length > 180) return false;
  if (/^(?:abstract|introduction|references|appendix)$/i.test(cleaned))
    return false;
  if (detectHeading(cleaned).kind !== "none") return false;
  return true;
}

function cleanAuthorLine(value: string): string {
  return collapseWhitespace(
    value
      .replace(/^line\s*\d+\s*:\s*/i, "")
      .replace(/\(\s*of\s+affiliation\s*\)/gi, "")
      .replace(/^(?:authors?|by)\s*:\s*/i, ""),
  );
}

function parseAuthorNamesLine(value: string): string[] {
  const cleaned = cleanAuthorLine(value);
  const parts = cleaned
    .split(/\s*(?:,|;|\band\b)\s*/i)
    .map((part) => collapseWhitespace(part))
    .filter((part) => part.length > 1);

  return parts
    .filter((part) => !isTemplateInstructionLine(part))
    .map((part) => sanitizeTemplateRestrictedText(part))
    .filter((part) => part.length > 1);
}

function parseAuthorBlocks(authorLines: string[]): AuthorBlock[] {
  if (!authorLines.length) return [];

  const taggedLine = authorLines.find((line) =>
    /^(?:authors?|by)\s*:/i.test(line),
  );
  if (taggedLine) {
    return parseAuthorNamesLine(taggedLine).map((name) => ({
      name,
      details: [],
    }));
  }

  const blocks: string[][] = [];
  let current: string[] = [];
  for (const rawLine of authorLines) {
    const trimmed = collapseWhitespace(rawLine);
    if (!trimmed) {
      if (current.length) {
        blocks.push(current);
        current = [];
      }
      continue;
    }
    current.push(trimmed);
  }
  if (current.length) blocks.push(current);

  if (blocks.length === 1 && blocks[0].length === 1) {
    return parseAuthorNamesLine(blocks[0][0]).map((name) => ({
      name,
      details: [],
    }));
  }

  const parsed: AuthorBlock[] = [];
  for (const rawBlock of blocks) {
    const cleanedLines = rawBlock
      .map((line) => cleanAuthorLine(line))
      .filter((line) => line.length > 0)
      .filter((line) => !isTemplateInstructionLine(line))
      .filter(
        (line) =>
          !/^dept\.\s*name\s+of\s+organization$/i.test(line) &&
          !/^name\s+of\s+organization$/i.test(line) &&
          !/^city,\s*country$/i.test(line) &&
          !/^email\s+address(?:\s+or\s+orcid)?$/i.test(line),
      );

    if (!cleanedLines.length) continue;

    if (cleanedLines.length === 1 && /[,;]|\band\b/i.test(cleanedLines[0])) {
      for (const name of parseAuthorNamesLine(cleanedLines[0])) {
        parsed.push({ name, details: [] });
      }
      continue;
    }

    const [nameLine, ...detailLines] = cleanedLines;
    const name = sanitizeTemplateRestrictedText(nameLine);
    if (!name) continue;

    const details = detailLines
      .map((line) => collapseWhitespace(line))
      .filter((line) => line.length > 0)
      .slice(0, 4);

    parsed.push({ name, details });
  }

  return parsed;
}

function extractFrontMatter(lines: string[]): {
  title: string | null;
  authorBlocks: AuthorBlock[];
  startIndex: number;
} {
  let cursor = 0;
  while (
    cursor < lines.length &&
    (() => {
      const trimmed = collapseWhitespace(lines[cursor]);
      return (
        !trimmed ||
        (isTemplateInstructionLine(trimmed) &&
          !/^line\s*\d+\s*:/i.test(trimmed))
      );
    })()
  ) {
    cursor += 1;
  }

  if (cursor >= lines.length) {
    return { title: null, authorBlocks: [], startIndex: lines.length };
  }

  let title: string | null = null;
  const titleTagged = lines[cursor].match(/^title\s*[:\-]\s*(.+)$/i);
  if (titleTagged) {
    title = sanitizeTemplateRestrictedText(titleTagged[1]);
    cursor += 1;
  } else if (looksLikeTitle(lines[cursor])) {
    title = sanitizeTemplateRestrictedText(lines[cursor]);
    cursor += 1;
  }

  while (
    cursor < lines.length &&
    (() => {
      const trimmed = collapseWhitespace(lines[cursor]);
      return (
        !trimmed ||
        (isTemplateInstructionLine(trimmed) &&
          !/^line\s*\d+\s*:/i.test(trimmed))
      );
    })()
  ) {
    cursor += 1;
  }

  const authorLines: string[] = [];
  while (cursor < lines.length) {
    const line = lines[cursor];
    const trimmed = collapseWhitespace(line);
    if (isFrontMatterBoundaryLine(trimmed)) break;

    // Skip metadata lines that aren't author info
    if (
      /^(?:publication\s+date|journal|conference|doi|issn|vol(?:ume)?)\s*:/i.test(
        trimmed,
      )
    ) {
      cursor += 1;
      continue;
    }

    if (!trimmed) {
      authorLines.push("");
    } else if (
      /^line\s*\d+\s*:/i.test(trimmed) ||
      !isTemplateInstructionLine(trimmed)
    ) {
      authorLines.push(trimmed);
    }
    cursor += 1;
  }

  const authorBlocks = parseAuthorBlocks(authorLines);
  return { title, authorBlocks, startIndex: cursor };
}

export interface ASTNode {
  type: 'abstract' | 'keywords' | 'algorithm' | 'table' | 'reference' | 'heading' | 'paragraph';
  text?: string;
  level?: number;
  kind?: HeadingKind;
  title?: string;
  lines?: string[];
  caption?: string | null;
  rows?: string[][];
  label?: string | null;
}

export interface ParsedDocument {
  frontMatter: {
    title: string | null;
    authorBlocks: AuthorBlock[];
  };
  nodes: ASTNode[];
}

export function parseDocument(rawText: string): ParsedDocument {
  const lines = rawText.replace(/\r\n?/g, '\n').split('\n');
  const nodes: ASTNode[] = [];
  const frontMatterResult = extractFrontMatter(lines);

  let paragraphBuffer: string[] = [];
  let tableBuffer: string[] = [];
  let tableCaptionPending: string | null = null;
  let referenceBuffer: string[] = [];
  let referenceLabel: string | null = null;
  
  let inAbstract = false;
  let inReferences = false;

  const flushParagraph = () => {
    if (!paragraphBuffer.length) return;
    const text = collapseWhitespace(paragraphBuffer.join(' '));
    paragraphBuffer = [];
    if (!text) return;
    if (inAbstract) {
      nodes.push({ type: 'abstract', text: sanitizeTemplateRestrictedText(text) });
      return;
    }
    nodes.push({ type: 'paragraph', text });
  };

  const flushTable = () => {
    if (!tableBuffer.length) return;
    const rows: string[][] = [];
    for (const line of tableBuffer) {
      if (isTableSeparatorLine(line)) continue;
      const row = splitTableRow(line);
      if (row.length >= 2) rows.push(row);
    }
    tableBuffer = [];
    const cap = tableCaptionPending;
    tableCaptionPending = null;
    if (!rows.length) return;
    
    const columnCount = Math.max(...rows.map(r => r.length));
    const normalizedRows = rows.map(r => {
      const padded = [...r];
      while (padded.length < columnCount) padded.push('');
      return padded;
    });

    nodes.push({ type: 'table', caption: cap, rows: normalizedRows });
  };

  const flushReference = () => {
    if (!referenceBuffer.length) return;
    const text = collapseWhitespace(referenceBuffer.join(' '));
    referenceBuffer = [];
    if (!text) return;
    nodes.push({ type: 'reference', label: referenceLabel, text });
    referenceLabel = null;
  };

  for (let i = frontMatterResult.startIndex; i < lines.length; i += 1) {
    const line = lines[i];
    const trimmed = collapseWhitespace(line);

    if (!trimmed) {
      flushTable(); flushParagraph(); flushReference();
      continue;
    }
    if (isTemplateInstructionLine(trimmed)) continue;

    const abstractInlineMatch = trimmed.match(/^abstract\b(?:\s*[^\w\s]\s*|\s+)(.+)$/i);
    if (abstractInlineMatch) {
      flushTable(); flushParagraph(); flushReference();
      inAbstract = true;
      inReferences = false;
      nodes.push({ type: 'abstract', text: sanitizeTemplateRestrictedText(abstractInlineMatch[1]) });
      continue;
    }

    const keywordMatch = trimmed.match(/^(?:index terms?|keywords?)\b(?:\s*[^\w\s]\s*|\s+)(.+)$/i);
    if (keywordMatch) {
      flushTable(); flushParagraph(); flushReference();
      nodes.push({ type: 'keywords', text: keywordMatch[1] });
      inAbstract = false;
      continue;
    }

    const algoStart = isAlgorithmStart(trimmed);
    if (algoStart) {
      flushTable(); flushParagraph(); flushReference();
      inAbstract = false;
      const algoBodyLines: string[] = [];
      let j = i + 1;
      while (j < lines.length) {
        const peek = collapseWhitespace(lines[j]);
        if (!peek || isTemplateInstructionLine(peek)) { j++; continue; }
        break;
      }
      while (j < lines.length) {
        const algoLine = lines[j];
        const algoTrimmed = collapseWhitespace(algoLine);
        if (!algoTrimmed) {
          let lookAhead = j + 1;
          while (lookAhead < lines.length) {
            const laText = collapseWhitespace(lines[lookAhead]);
            if (!laText || isTemplateInstructionLine(laText)) { lookAhead++; continue; }
            break;
          }
          if (lookAhead < lines.length && isAlgorithmBodyLine(lines[lookAhead])) {
            algoBodyLines.push(''); j++; continue;
          }
          break;
        }
        if (isTemplateInstructionLine(algoTrimmed)) { j++; continue; }
        if (isAlgorithmBodyLine(algoLine)) {
          algoBodyLines.push(algoLine);
          j++;
        } else {
          break;
        }
      }
      nodes.push({ type: 'algorithm', title: algoStart.title, lines: algoBodyLines });
      i = j - 1;
      continue;
    }

    const tableCaption = parseTableCaption(trimmed);
    if (tableCaption && !inReferences) {
      flushTable(); flushParagraph();
      let nextIdx = i + 1;
      while (nextIdx < lines.length && !collapseWhitespace(lines[nextIdx])) { nextIdx++; }
      if (nextIdx < lines.length && isTableLine(lines[nextIdx])) {
        tableCaptionPending = tableCaption;
        continue;
      }
      nodes.push({ type: 'paragraph', text: tableCaption });
      continue;
    }

    if (isTableLine(line)) {
      flushParagraph(); flushReference();
      tableBuffer.push(line);
      continue;
    }
    flushTable();

    if (inReferences) {
      const breakHeading = detectHeading(trimmed);
      const isBreak = breakHeading.kind === 'appendix' || breakHeading.kind === 'acknowledgment';
      if (isBreak) {
        flushReference();
        inReferences = false;
        nodes.push({ type: 'heading', level: 1, kind: breakHeading.kind, title: breakHeading.title });
        continue;
      }
      const refStart = parseReferenceStart(trimmed);
      if (refStart) {
        flushReference();
        referenceLabel = refStart.label;
        referenceBuffer.push(refStart.content);
      } else if (referenceBuffer.length) {
        referenceBuffer.push(trimmed);
      } else {
        referenceLabel = null;
        referenceBuffer.push(trimmed);
      }
      continue;
    }

    const heading = detectHeading(trimmed);
    if (heading.kind !== 'none') {
      flushParagraph(); flushReference();
      inAbstract = false; inReferences = false;
      if (heading.kind === 'abstract') {
        inAbstract = true;
        continue;
      }
      if (heading.kind === 'references') {
        inReferences = true;
        nodes.push({ type: 'heading', level: 1, kind: heading.kind, title: 'References' });
        continue;
      }
      if (heading.kind === 'subsection') {
        nodes.push({ type: 'heading', level: 2, kind: heading.kind, title: heading.title });
        continue;
      }
      nodes.push({ type: 'heading', level: 1, kind: heading.kind, title: heading.title });
      continue;
    }

    paragraphBuffer.push(trimmed);
  }

  flushTable(); flushParagraph(); flushReference();

  return {
    frontMatter: { title: frontMatterResult.title, authorBlocks: frontMatterResult.authorBlocks },
    nodes
  };
}


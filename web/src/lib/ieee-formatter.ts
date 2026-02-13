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

type HeadingKind =
  | "none"
  | "abstract"
  | "references"
  | "appendix"
  | "acknowledgment"
  | "section"
  | "subsection";

type HeadingDetection = {
  kind: HeadingKind;
  title: string;
};

type InlineFormatResult = {
  html: string;
  equationCount: number;
};

type TableFormatResult = {
  html: string;
  equationCount: number;
};

type AuthorBlock = {
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

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function collapseWhitespace(value: string): string {
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

function sanitizeTemplateRestrictedText(value: string): string {
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

function toRoman(num: number): string {
  const map: [number, string][] = [
    [1000, "M"], [900, "CM"], [500, "D"], [400, "CD"],
    [100, "C"], [90, "XC"], [50, "L"], [40, "XL"],
    [10, "X"], [9, "IX"], [5, "V"], [4, "IV"], [1, "I"],
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

function toLetterLabel(num: number): string {
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
  // Must have at least 2 words after the number to avoid matching
  // algorithm pseudocode lines like "1: Broadcast ..." or list items
  const numberedMain = trimmed.match(
    /^(?:section\s+)?(?:\d+|[ivxlcdm]+)[.):]?\s+(.+)$/i,
  );
  if (numberedMain) {
    const afterNumber = numberedMain[1].trim();
    const wordCount = afterNumber.split(/\s+/).length;
    // Only treat as heading if the text is short (heading-like) 
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

function processInlineContent(text: string): InlineFormatResult {
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
    (_whole, inner: string) => `<span class="ieee-citation">[${inner}]</span>`,
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
  if (/^(?:Input|Output|Require|Ensure|Return|Initialize)\s*:/i.test(trimmed)) return true;
  if (/^(?:for|while|if|else|end|repeat|until|do|function|procedure)\b/i.test(trimmed)) return true;
  // Separator lines (dashes, equals, mixed) used in algorithm boxes
  if (/^[-=_]{5,}$/.test(trimmed.replace(/\s/g, ""))) return true;
  // Indented lines (at least 2 spaces) are part of the algorithm body
  if (line.startsWith("  ") || line.startsWith("\t")) return true;
  // Lines that start with common pseudo-operators like FOR, ELSE IF
  if (/^(?:ELSE\s+IF|ELSE|END\s+(?:IF|FOR|WHILE))\b/i.test(trimmed)) return true;
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
      return `<div class="algo-line" style="padding-left:${paddingLeft}px">${escaped}</div>`;
    })
    .join("");

  return (
    `<div class="algorithm-block">` +
    `<div class="algo-title"><strong>${escapeHtml(title)}</strong></div>` +
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
  if (/^(?:publication\s+date|journal|conference)\s*:/i.test(cleaned)) return false;
  if (/^(?:\d+|[IVXLCM]+)[.)]?\s+[A-Za-z]/i.test(cleaned)) return true;
  if (/^[A-Z][.)]\s+\S+/.test(cleaned)) return true;
  return MAIN_SECTION_KEYWORDS.some((item) =>
    item.regex.test(cleaned.replace(/[.:]\s*$/, "")),
  );
}

function looksLikeTitle(value: string): boolean {
  const cleaned = collapseWhitespace(value);
  if (!cleaned || cleaned.length < 8 || cleaned.length > 180) return false;
  if (/^(?:abstract|introduction|references|appendix)$/i.test(cleaned)) return false;
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
        (isTemplateInstructionLine(trimmed) && !/^line\s*\d+\s*:/i.test(trimmed))
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
        (isTemplateInstructionLine(trimmed) && !/^line\s*\d+\s*:/i.test(trimmed))
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
    if (/^(?:publication\s+date|journal|conference|doi|issn|vol(?:ume)?)\s*:/i.test(trimmed)) {
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

function renderAuthorBlocks(authorBlocks: AuthorBlock[]): string {
  if (!authorBlocks.length) return "";

  const capped = authorBlocks.slice(0, 6);
  const columnCount = Math.min(3, Math.max(1, capped.length));
  const blocksHtml = capped
    .map((block) => {
      const detailHtml = block.details
        .map((line) => `<p class="author-line">${escapeHtml(line)}</p>`)
        .join("");
      return (
        `<div class="author-block">` +
        `<p class="author-name">${escapeHtml(block.name)}</p>` +
        detailHtml +
        `</div>`
      );
    })
    .join("");

  return (
    `<div class="author-grid author-grid-${columnCount}">` +
    blocksHtml +
    `</div>`
  );
}

/* ═══════════════════════════════════════════════════════════════
 *  MAIN FORMATTER
 * ═══════════════════════════════════════════════════════════════ */

export interface FormatResult {
  html: string;
  sectionCount: number;
  tableCount: number;
  equationCount: number;
  algorithmCount: number;
  citationCount: number;
}

export function formatToIEEE(rawText: string): FormatResult {
  const lines = rawText.replace(/\r\n?/g, "\n").split("\n");
  const htmlParts: string[] = [];

  // ── front matter ──
  const frontMatter = extractFrontMatter(lines);
  if (frontMatter.title) {
    htmlParts.push(
      `<h1 class="paper-title">${escapeHtml(frontMatter.title)}</h1>`,
    );
  }
  const authorGridHtml = renderAuthorBlocks(frontMatter.authorBlocks);
  if (authorGridHtml) htmlParts.push(authorGridHtml);

  // ── counters ──
  let paragraphBuffer: string[] = [];
  let tableBuffer: string[] = [];
  let tableCaptionPending: string | null = null;
  let referenceBuffer: string[] = [];
  let referenceLabel: string | null = null;

  let sectionCount = 0;
  let subsectionCounter = 0; // resets per section
  let tableCount = 0;
  let equationCount = 0;
  let algorithmCount = 0;
  let citationCount = 0;
  let autoReferenceNumber = 1;
  let inAbstract = false;
  let inReferences = false;
  let abstractLabelWritten = false;
  let justAfterHeading = false; // track first-paragraph-after-heading

  /* ── flush helpers ── */

  const flushParagraph = () => {
    if (!paragraphBuffer.length) return;
    const text = collapseWhitespace(paragraphBuffer.join(" "));
    paragraphBuffer = [];
    if (!text) return;

    if (inAbstract) {
      const sanitized = sanitizeTemplateRestrictedText(text);
      const abstractPrefix = abstractLabelWritten
        ? ""
        : '<strong>Abstract&mdash;</strong> ';
      abstractLabelWritten = true;
      htmlParts.push(
        `<p class="abstract-text">${abstractPrefix}${escapeHtml(sanitized)}</p>`,
      );
      return;
    }

    const formatted = processInlineContent(text);
    equationCount += formatted.equationCount;

    // Count citations
    const citationMatches = text.match(/\[\d+(?:\s*[,\-–]\s*\d+)*\]/g);
    if (citationMatches) citationCount += citationMatches.length;

    // First paragraph after heading: no indent
    const noIndentClass = justAfterHeading ? ' class="no-indent"' : "";
    justAfterHeading = false;

    htmlParts.push(`<p${noIndentClass}>${formatted.html}</p>`);
  };

  const flushTable = () => {
    if (!tableBuffer.length) return;
    const table = convertTable(tableBuffer, tableCaptionPending ?? undefined);
    tableBuffer = [];
    tableCaptionPending = null;
    if (!table.html) return;
    tableCount += 1;
    equationCount += table.equationCount;
    htmlParts.push(table.html);
  };

  const flushReference = () => {
    if (!referenceBuffer.length) return;
    const text = collapseWhitespace(referenceBuffer.join(" "));
    referenceBuffer = [];
    if (!text) return;

    const inline = processInlineContent(text);
    equationCount += inline.equationCount;
    const label = referenceLabel ?? `[${autoReferenceNumber}]`;
    if (!referenceLabel) autoReferenceNumber += 1;
    referenceLabel = null;
    htmlParts.push(`<p class="reference-item">${label} ${inline.html}</p>`);
  };

  /* ── main loop ── */

  for (let i = frontMatter.startIndex; i < lines.length; i += 1) {
    const line = lines[i];
    const trimmed = collapseWhitespace(line);

    // Empty line → flush all buffers
    if (!trimmed) {
      flushTable();
      flushParagraph();
      flushReference();
      continue;
    }

    if (isTemplateInstructionLine(trimmed)) continue;

    // ── Inline abstract (e.g. "Abstract: We present...")
    const abstractInlineMatch = trimmed.match(
      /^abstract\b(?:\s*[^\w\s]\s*|\s+)(.+)$/i,
    );
    if (abstractInlineMatch) {
      flushTable();
      flushParagraph();
      flushReference();
      inAbstract = true;
      inReferences = false;
      const sanitized = sanitizeTemplateRestrictedText(abstractInlineMatch[1]);
      htmlParts.push(
        `<p class="abstract-text"><strong>Abstract&mdash;</strong> ${escapeHtml(sanitized)}</p>`,
      );
      abstractLabelWritten = true;
      justAfterHeading = false;
      continue;
    }

    // ── Keywords / Index Terms
    const keywordMatch = trimmed.match(
      /^(?:index terms?|keywords?)\b(?:\s*[^\w\s]\s*|\s+)(.+)$/i,
    );
    if (keywordMatch) {
      flushTable();
      flushParagraph();
      flushReference();
      const formatted = processInlineContent(keywordMatch[1]);
      equationCount += formatted.equationCount;
      htmlParts.push(
        `<p class="index-terms"><strong>Keywords&mdash;</strong> ${formatted.html}</p>`,
      );
      inAbstract = false;
      justAfterHeading = false;
      continue;
    }

    // ── Algorithm block detection
    const algoStart = isAlgorithmStart(trimmed);
    if (algoStart) {
      flushTable();
      flushParagraph();
      flushReference();
      inAbstract = false;

      // Collect algorithm body lines
      const algoBodyLines: string[] = [];
      let j = i + 1;
      while (j < lines.length) {
        const algoLine = lines[j];
        const algoTrimmed = collapseWhitespace(algoLine);
        if (!algoTrimmed) {
          // Empty line might be internal spacing or end of algorithm
          // Look ahead to see if more algorithm lines follow
          if (j + 1 < lines.length && isAlgorithmBodyLine(lines[j + 1])) {
            algoBodyLines.push(""); // keep internal blank line
            j++;
            continue;
          }
          break;
        }
        if (isAlgorithmBodyLine(algoLine)) {
          algoBodyLines.push(algoLine);
          j++;
        } else {
          break;
        }
      }

      algorithmCount += 1;
      htmlParts.push(renderAlgorithmBlock(algoStart.title, algoBodyLines));
      i = j - 1; // advance past algorithm body
      justAfterHeading = false;
      continue;
    }

    // ── Table caption line (e.g. "Table 1: Results")
    const tableCaption = parseTableCaption(trimmed);
    if (tableCaption && !inReferences) {
      flushTable();
      flushParagraph();
      // Look ahead: is the next non-empty line a table?
      let nextIdx = i + 1;
      while (nextIdx < lines.length && !collapseWhitespace(lines[nextIdx])) {
        nextIdx++;
      }
      if (nextIdx < lines.length && isTableLine(collapseWhitespace(lines[nextIdx]))) {
        // This is a caption for the upcoming table, store it
        tableCaptionPending = tableCaption;
        continue;
      }
      // Not followed by a table—render as a standalone caption paragraph
      htmlParts.push(`<p class="table-caption">${escapeHtml(tableCaption)}</p>`);
      continue;
    }

    // ── Table data lines
    if (isTableLine(trimmed)) {
      flushParagraph();
      flushReference();
      tableBuffer.push(trimmed);
      continue;
    }
    flushTable();

    // ── References zone
    if (inReferences) {
      const breakHeading = detectHeading(trimmed);
      const isReferenceSectionBreak =
        breakHeading.kind === "appendix" || breakHeading.kind === "acknowledgment";

      if (isReferenceSectionBreak) {
        flushReference();
        inReferences = false;
        htmlParts.push(`<h1 class="ieee-heading">${escapeHtml(breakHeading.title)}</h1>`);
        justAfterHeading = true;
        continue;
      }

      const referenceStart = parseReferenceStart(trimmed);
      if (referenceStart) {
        flushReference();
        referenceLabel = referenceStart.label;
        referenceBuffer.push(referenceStart.content);
      } else if (referenceBuffer.length) {
        referenceBuffer.push(trimmed);
      } else {
        referenceLabel = `[${autoReferenceNumber}]`;
        autoReferenceNumber += 1;
        referenceBuffer.push(trimmed);
      }
      continue;
    }

    // ── Heading detection
    const heading = detectHeading(trimmed);
    if (heading.kind !== "none") {
      flushParagraph();
      flushReference();
      inAbstract = false;
      inReferences = false;

      if (heading.kind === "abstract") {
        inAbstract = true;
        abstractLabelWritten = false;
        justAfterHeading = true;
        continue;
      }

      if (heading.kind === "references") {
        htmlParts.push(`<h1 class="ieee-heading">References</h1>`);
        inReferences = true;
        justAfterHeading = false;
        continue;
      }

      if (heading.kind === "appendix" || heading.kind === "acknowledgment") {
        htmlParts.push(`<h1 class="ieee-heading">${escapeHtml(heading.title)}</h1>`);
        justAfterHeading = true;
        continue;
      }

      if (heading.kind === "subsection") {
        subsectionCounter += 1;
        const letterLabel = toLetterLabel(subsectionCounter);
        htmlParts.push(
          `<h2 class="ieee-subheading"><em>${letterLabel}. ${escapeHtml(heading.title)}</em></h2>`,
        );
        justAfterHeading = true;
        continue;
      }

      // Main section
      sectionCount += 1;
      subsectionCounter = 0; // reset subsection counter
      const romanLabel = toRoman(sectionCount);
      htmlParts.push(
        `<h1 class="ieee-heading">${romanLabel}. ${escapeHtml(heading.title).toUpperCase()}</h1>`,
      );
      justAfterHeading = true;
      continue;
    }

    // ── Regular paragraph text
    paragraphBuffer.push(trimmed);
  }

  // ── final flush ──
  flushTable();
  flushParagraph();
  flushReference();
  htmlParts.push(`<p class="ieee-copyright">${IEEE_COPYRIGHT_FOOTER}</p>`);

  return {
    html: htmlParts.join("\n"),
    sectionCount,
    tableCount,
    equationCount,
    algorithmCount,
    citationCount,
  };
}

/**
 * Estimate page count with simple IEEE-friendly heuristics.
 */
export function estimatePageCount(html: string, colCount: 1 | 2): number {
  const textOnly = html
    .replace(/<blockquote[^>]*>[\s\S]*?<\/blockquote>/g, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  const wordCount = textOnly ? textOnly.split(" ").length : 0;
  const tableCount = (html.match(/<table>/g) || []).length;
  const equationCount = (html.match(/class="math-inline"|class="equation"/g) || [])
    .length;

  const wordsPerPage = colCount === 2 ? 750 : 1050;
  const structuralPenalty = tableCount * 0.33 + equationCount * 0.08;
  return Math.max(1, Math.ceil(wordCount / wordsPerPage + structuralPenalty));
}

import {
  ParsedDocument,
  ASTNode,
  AuthorBlock,
  processInlineContent,
  escapeHtml,
  toRoman,
  toLetterLabel,
  CitationContext
} from "../parser/document-parser";

export interface FormatResult {
  html: string;
  sectionCount: number;
  tableCount: number;
  equationCount: number;
  algorithmCount: number;
  citationCount: number;
}

export interface FormatOptions {
  numberingStyle?: "roman" | "arabic";
  useDropCap?: boolean;
  hideCopyright?: boolean;
  addCCSBlock?: boolean;
  addKeywordsBlock?: boolean;
  authorStyle?: "grid" | "stacked";
}

const IEEE_COPYRIGHT_FOOTER = "XXX-X-XXXX-XXXX-X/XX/$XX.00 &copy;20XX IEEE";

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

  return `<div class="author-grid author-grid-${columnCount}">${blocksHtml}</div>`;
}

function renderAuthorBlocksStacked(authorBlocks: AuthorBlock[]): string {
  if (!authorBlocks.length) return "";
  const blocksHtml = authorBlocks
    .map((block) => {
      const detailHtml = block.details
        .map((line) => `<p class="author-line">${escapeHtml(line)}</p>`)
        .join("");
      return (
        `<div class="author-block author-stacked">` +
        `<p class="author-name">${escapeHtml(block.name)}</p>` +
        detailHtml +
        `</div>`
      );
    })
    .join("");
  return `<div class="author-grid author-stacked-container">${blocksHtml}</div>`;
}

export function formatToIEEE(doc: ParsedDocument, options: FormatOptions = {}): FormatResult {
  const numberingStyle = options.numberingStyle ?? "roman";
  const useDropCap = options.useDropCap ?? false;
  const hideCopyright = options.hideCopyright ?? false;
  const addCCSBlock = options.addCCSBlock ?? false;
  const addKeywordsBlock = options.addKeywordsBlock ?? false;
  const authorStyle = options.authorStyle ?? "grid";

  const htmlParts: string[] = [];

  if (doc.frontMatter.title) {
    htmlParts.push(`<h1 class="paper-title">${escapeHtml(doc.frontMatter.title)}</h1>`);
  }
  if (authorStyle === "stacked") {
    const stackedHtml = renderAuthorBlocksStacked(doc.frontMatter.authorBlocks);
    if (stackedHtml) htmlParts.push(stackedHtml);
  } else {
    const authorGridHtml = renderAuthorBlocks(doc.frontMatter.authorBlocks);
    if (authorGridHtml) htmlParts.push(authorGridHtml);
  }

  let sectionCount = 0;
  let subsectionCounter = 0;
  let tableCount = 0;
  let equationCount = 0;
  let algorithmCount = 0;
  let citationCount = 0;
  let citationAnchorCounter = 1;

  let justAfterHeading = false;
  let isFirstSectionFirstPara = false;
  let keywordsWritten = false;
  const citationBacklinks = new Map<number, string[]>();

  const citationContext: CitationContext = {
    getNextCitationId: () => {
      const id = `cite-${citationAnchorCounter}`;
      citationAnchorCounter += 1;
      return id;
    },
    registerCitation: (referenceNumber: number, citationId: string) => {
      const existing = citationBacklinks.get(referenceNumber) ?? [];
      existing.push(citationId);
      citationBacklinks.set(referenceNumber, existing);
    },
  };

  for (const node of doc.nodes) {
    if (node.type === "abstract") {
      htmlParts.push(`<p class="abstract-text"><strong>Abstract&mdash;</strong> ${escapeHtml(node.text || '')}</p>`);
      justAfterHeading = true;
    } else if (node.type === "keywords") {
      const formatted = processInlineContent(node.text || '');
      equationCount += formatted.equationCount;
      htmlParts.push(`<p class="index-terms"><strong>Keywords&mdash;</strong> ${formatted.html}</p>`);
      justAfterHeading = false;
    } else if (node.type === "algorithm") {
      algorithmCount++;
      const bodyHtml = (node.lines || [])
        .map((line) => {
          const escaped = escapeHtml(line);
          const leadingSpaces = line.match(/^(\s*)/)?.[1]?.length ?? 0;
          const indentLevel = Math.min(Math.floor(leadingSpaces / 2), 4);
          const paddingLeft = indentLevel * 16;
          return `<p class="algo-line" style="margin:0;padding-left:${paddingLeft}px;text-indent:0">${escaped}</p>`;
        })
        .join("");
      htmlParts.push(
        `<div class="algorithm-block"><p class="algo-title"><strong>${escapeHtml(node.title || '')}</strong></p><div class="algo-body">${bodyHtml}</div></div>`
      );
      justAfterHeading = false;
    } else if (node.type === "table") {
      tableCount++;
      let html = "";
      if (node.caption) {
        html += `<p class="table-caption">${escapeHtml(node.caption)}</p>`;
      }
      html += "<table><thead><tr>";
      const rows = node.rows || [];
      if (rows.length > 0) {
        for (const cell of rows[0]) {
          const rendered = processInlineContent(cell);
          equationCount += rendered.equationCount;
          html += `<th>${rendered.html}</th>`;
        }
        html += "</tr></thead><tbody>";
        for (let i = 1; i < rows.length; i++) {
          html += "<tr>";
          for (const cell of rows[i]) {
            const rendered = processInlineContent(cell);
            equationCount += rendered.equationCount;
            html += `<td>${rendered.html}</td>`;
          }
          html += "</tr>";
        }
        html += "</tbody></table>";
      }
      htmlParts.push(`<div class="table-wrapper">${html}</div>`);
    } else if (node.type === "reference") {
      const inline = processInlineContent(node.text || '');
      equationCount += inline.equationCount;
      const refNumberMatch = (node.label || '').match(/\[(\d+)\]/);
      const refId = refNumberMatch ? `ref-${refNumberMatch[1]}` : undefined;
      const refNumber = refNumberMatch ? Number.parseInt(refNumberMatch[1], 10) : Number.NaN;
      const backlinks = Number.isFinite(refNumber) ? (citationBacklinks.get(refNumber) ?? []) : [];
      const backlinkHtml = backlinks.length
        ? `<span class="reference-backlinks"> ${backlinks
            .map((citationId, index) => `<a class="reference-backlink" href="#${citationId}" title="Back to citation${backlinks.length > 1 ? ` ${index + 1}` : ''}">↩</a>`)
            .join(" ")}</span>`
        : "";
      htmlParts.push(
        `<p class="reference-item"${refId ? ` id="${refId}"` : ""}>` +
        `<span class="reference-label">${node.label || ''}</span> ${inline.html}${backlinkHtml}` +
        `</p>`
      );
    } else if (node.type === "heading") {
      if (node.kind === "references" || node.kind === "appendix" || node.kind === "acknowledgment") {
        htmlParts.push(`<h1 class="ieee-heading">${escapeHtml(node.title || '')}</h1>`);
        justAfterHeading = true;
      } else if (node.level === 2) {
        subsectionCounter += 1;
        if (numberingStyle === "arabic") {
          htmlParts.push(`<h2 class="ieee-subheading">${sectionCount}.${subsectionCounter} ${escapeHtml(node.title || '')}</h2>`);
        } else {
          const letterLabel = toLetterLabel(subsectionCounter);
          htmlParts.push(`<h2 class="ieee-subheading"><em>${letterLabel}. ${escapeHtml(node.title || '')}</em></h2>`);
        }
        justAfterHeading = true;
      } else {
        sectionCount += 1;
        subsectionCounter = 0;
        if (sectionCount === 1) {
          if (addCCSBlock) {
            htmlParts.push(
              `<div class="ccs-concepts"><p class="ccs-title"><strong>CCS Concepts</strong></p>` +
              `<p class="ccs-item">&bull; <em>Computing methodologies</em> &rarr; <em>Artificial intelligence</em></p></div>`
            );
          }
          if (addKeywordsBlock && !keywordsWritten) {
            htmlParts.push(`<p class="acm-keywords"><strong>Keywords</strong> &mdash; research, methodology, analysis</p>`);
            keywordsWritten = true;
          }
          isFirstSectionFirstPara = true;
        }

        if (numberingStyle === "arabic") {
          htmlParts.push(`<h1 class="ieee-heading">${sectionCount} ${escapeHtml(node.title || '').toUpperCase()}</h1>`);
        } else {
          const romanLabel = toRoman(sectionCount);
          htmlParts.push(`<h1 class="ieee-heading">${romanLabel}. ${escapeHtml(node.title || '').toUpperCase()}</h1>`);
        }
        justAfterHeading = true;
      }
    } else if (node.type === "paragraph") {
      const text = node.text || '';
      const formatted = processInlineContent(text, citationContext);
      equationCount += formatted.equationCount;
      const citationMatches = text.match(/\[\d+(?:\s*[,\-–]\s*\d+)*\]/g);
      if (citationMatches) citationCount += citationMatches.length;

      const cssClasses: string[] = [];
      if (justAfterHeading) cssClasses.push("no-indent");
      if (useDropCap && isFirstSectionFirstPara) cssClasses.push("drop-cap");
      justAfterHeading = false;
      isFirstSectionFirstPara = false;

      const classAttr = cssClasses.length ? ` class="${cssClasses.join(" ")}"` : "";
      htmlParts.push(`<p${classAttr}>${formatted.html}</p>`);
    }
  }

  if (!hideCopyright) {
    htmlParts.push(`<p class="ieee-copyright">${IEEE_COPYRIGHT_FOOTER}</p>`);
  }

  return { html: htmlParts.join("\n"), sectionCount, tableCount, equationCount, algorithmCount, citationCount };
}

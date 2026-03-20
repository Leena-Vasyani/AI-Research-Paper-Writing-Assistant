import {
  ParsedDocument,
  ASTNode,
  AuthorBlock,
  processInlineContent,
  escapeHtml,
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

export interface FormatOptions {}

function renderSpringerAuthors(authorBlocks: AuthorBlock[]): string {
  if (!authorBlocks.length) return "";
  
  // Springer usually renders all authors in a single line, separated by commas
  // and their affiliations grouped below with superscript indices.
  const authorNames = authorBlocks.map(block => escapeHtml(block.name)).join(", ");
  
  // A simple representation for Springer: each author's details as a block below the main names.
  const affiliationsHtml = authorBlocks.map(block => {
    if (!block.details.length) return "";
    return `<p class="springer-affiliation">${block.details.map(escapeHtml).join("<br/>")}</p>`;
  }).join("");

  return `<div class="springer-author-block">
    <p class="springer-authors">${authorNames}</p>
    ${affiliationsHtml}
  </div>`;
}

export function formatToSpringer(doc: ParsedDocument, options: FormatOptions = {}): FormatResult {
  const htmlParts: string[] = [];
  
  if (doc.frontMatter.title) {
    htmlParts.push(`<h1 class="springer-title">${escapeHtml(doc.frontMatter.title)}</h1>`);
  }
  const authorGridHtml = renderSpringerAuthors(doc.frontMatter.authorBlocks);
  if (authorGridHtml) htmlParts.push(authorGridHtml);

  let sectionCount = 0;
  let subsectionCounter = 0;
  let tableCount = 0;
  let equationCount = 0;
  let algorithmCount = 0;
  let citationCount = 0;
  let citationAnchorCounter = 1;

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
      htmlParts.push(`<div class="springer-abstract"><strong>Abstract.</strong> ${escapeHtml(node.text || '')}</div>`);
    } else if (node.type === "keywords") {
      const formatted = processInlineContent(node.text || '');
      equationCount += formatted.equationCount;
      htmlParts.push(`<div class="springer-keywords"><strong>Keywords:</strong> ${formatted.html}</div>`);
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
        `<div class="algorithm-block springer-algorithm"><p class="algo-title"><strong>${escapeHtml(node.title || '')}</strong></p><div class="algo-body">${bodyHtml}</div></div>`
      );
    } else if (node.type === "table") {
      tableCount++;
      let html = "";
      if (node.caption) {
        html += `<p class="springer-table-caption"><strong>Table ${tableCount}.</strong> ${escapeHtml(node.caption.replace(/table\s*\d*\s*[.:*\-]*\s*/i, ''))}</p>`;
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
      htmlParts.push(`<div class="table-wrapper springer-table">${html}</div>`);
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
      
      const lbl = node.label ? `<span class="springer-ref-label">${node.label.replace(/(\[|\])/g, '')}.</span>` : '';
      
      htmlParts.push(
        `<p class="springer-reference-item"${refId ? ` id="${refId}"` : ""}>` +
        `${lbl} ${inline.html}${backlinkHtml}` +
        `</p>`
      );
    } else if (node.type === "heading") {
      if (node.kind === "references" || node.kind === "appendix" || node.kind === "acknowledgment") {
        htmlParts.push(`<h1 class="springer-heading">${escapeHtml(node.title || '')}</h1>`);
      } else if (node.level === 2) {
        subsectionCounter += 1;
        htmlParts.push(`<h2 class="springer-subheading">${sectionCount}.${subsectionCounter} ${escapeHtml(node.title || '')}</h2>`);
      } else {
        sectionCount += 1;
        subsectionCounter = 0;
        htmlParts.push(`<h1 class="springer-heading">${sectionCount} ${escapeHtml(node.title || '')}</h1>`);
      }
    } else if (node.type === "paragraph") {
      const text = node.text || '';
      const formatted = processInlineContent(text, citationContext);
      equationCount += formatted.equationCount;
      const citationMatches = text.match(/\[\d+(?:\s*[,\-–]\s*\d+)*\]/g);
      if (citationMatches) citationCount += citationMatches.length;

      htmlParts.push(`<p class="springer-paragraph">${formatted.html}</p>`);
    }
  }

  return { html: htmlParts.join("\n"), sectionCount, tableCount, equationCount, algorithmCount, citationCount };
}

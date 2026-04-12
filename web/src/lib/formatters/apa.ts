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

export type FormatOptions = Record<string, unknown>;

function renderAPATitlePage(doc: ParsedDocument): string {
  const htmlParts: string[] = [];
  
  // APA 7th Edition Student Title Page requires double spacing, centered text, 
  // placed in upper half of the page. Contains: Title, Author(s), Affiliation(s), Course, Instructor, Date.
  htmlParts.push(`<div class="apa-title-page">`);
  
  if (doc.frontMatter.title) {
    htmlParts.push(`<h1 class="apa-paper-title">${escapeHtml(doc.frontMatter.title)}</h1>`);
  }

  if (doc.frontMatter.authorBlocks.length > 0) {
    const mainAuthor = doc.frontMatter.authorBlocks[0];
    htmlParts.push(`<p class="apa-authors">${escapeHtml(mainAuthor.name)}</p>`);
    
    // Simulate typical APA student details if available
    for (const detail of mainAuthor.details) {
      htmlParts.push(`<p class="apa-affiliation">${escapeHtml(detail)}</p>`);
    }
  }

  htmlParts.push(`<div class="front-matter-page-break"></div></div>`);
  return htmlParts.join("\n");
}

export function formatToAPA(doc: ParsedDocument, options: FormatOptions = {}): FormatResult {
  const htmlParts: string[] = [];

  // Title Page
  htmlParts.push(renderAPATitlePage(doc));

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

  htmlParts.push(`<div class="apa-body-content">`);

  for (const node of doc.nodes) {
    if (node.type === "abstract") {
      htmlParts.push(`<h1 class="apa-heading">Abstract</h1>`);
      htmlParts.push(`<p class="apa-paragraph" style="text-indent: 0;">${escapeHtml(node.text || '')}</p>`);
      htmlParts.push(`<div class="front-matter-page-break"></div>`);
      
      // The body of the paper must start with the paper's title centered and bold at the top of the new page
      if (doc.frontMatter.title) {
        htmlParts.push(`<h1 class="apa-heading">${escapeHtml(doc.frontMatter.title)}</h1>`);
      }
    } else if (node.type === "keywords") {
      const formatted = processInlineContent(node.text || '');
      equationCount += formatted.equationCount;
      htmlParts.push(`<p class="apa-keywords"><em>Keywords:</em> ${formatted.html}</p>`);
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
        `<div class="algorithm-block apa-algorithm"><p class="algo-title"><strong>${escapeHtml(node.title || '')}</strong></p><div class="algo-body">${bodyHtml}</div></div>`
      );
    } else if (node.type === "table") {
      tableCount++;
      let html = "";
      html += `<p class="apa-table-caption"><strong>Table ${tableCount}</strong><br/><em>${node.caption ? escapeHtml(node.caption.replace(/table\s*\d*\s*[.:*\-]*\s*/i, '')) : 'Table Title'}</em></p>`;
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
      htmlParts.push(`<div class="table-wrapper apa-table">${html}</div>`);
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
        `<p class="apa-reference-item"${refId ? ` id="${refId}"` : ""}>` +
        `${inline.html}${backlinkHtml}` +
        `</p>`
      );
    } else if (node.type === "heading") {
      if (node.kind === "references" || node.kind === "appendix" || node.kind === "acknowledgment") {
        htmlParts.push(`<div class="front-matter-page-break"></div><h1 class="apa-heading">${escapeHtml(node.title || '')}</h1>`);
      } else if (node.level === 2) {
        subsectionCounter += 1;
        htmlParts.push(`<h2 class="apa-subheading">${escapeHtml(node.title || '')}</h2>`);
      } else {
        sectionCount += 1;
        subsectionCounter = 0;
        // In APA, body titles aren't numbered but we'll include section titles without artificial numbering 
        // to maintain flow unless strictly required. Typically they're just centered bold.
        htmlParts.push(`<h1 class="apa-heading">${escapeHtml(node.title || '')}</h1>`);
      }
    } else if (node.type === "paragraph") {
      const text = node.text || '';
      const formatted = processInlineContent(text, citationContext);
      equationCount += formatted.equationCount;
      const citationMatches = text.match(/\[\d+(?:\s*[,\-–]\s*\d+)*\]/g);
      if (citationMatches) citationCount += citationMatches.length;

      htmlParts.push(`<p class="apa-paragraph">${formatted.html}</p>`);
    }
  }

  htmlParts.push(`</div>`);

  return { html: htmlParts.join("\n"), sectionCount, tableCount, equationCount, algorithmCount, citationCount };
}

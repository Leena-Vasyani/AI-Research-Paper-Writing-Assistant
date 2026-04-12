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

function renderMLAHeader(doc: ParsedDocument): string {
  const htmlParts: string[] = [];
  
  // MLA First Page Header
  // Top left: Name, Instructor, Course, Date. Double spaced.
  htmlParts.push(`<div class="mla-first-page-header">`);
  
  if (doc.frontMatter.authorBlocks.length > 0) {
    const mainAuthor = doc.frontMatter.authorBlocks[0];
    htmlParts.push(`<p class="mla-header-line">${escapeHtml(mainAuthor.name)}</p>`);
    // Mock the other lines if details are present sequentially
    const details = mainAuthor.details;
    htmlParts.push(`<p class="mla-header-line">${details.length > 0 ? escapeHtml(details[0]) : "Instructor Name"}</p>`);
    htmlParts.push(`<p class="mla-header-line">${details.length > 1 ? escapeHtml(details[1]) : "Course Name"}</p>`);
    
    // Add a generic date or parsed
    const today = new Date();
    const formattedDate = `${today.getDate()} ${today.toLocaleString('default', { month: 'long' })} ${today.getFullYear()}`;
    htmlParts.push(`<p class="mla-header-line">${formattedDate}</p>`);
  } else {
    htmlParts.push(`<p class="mla-header-line">First Last</p>`);
    htmlParts.push(`<p class="mla-header-line">Instructor</p>`);
    htmlParts.push(`<p class="mla-header-line">Course</p>`);
    htmlParts.push(`<p class="mla-header-line">Date</p>`);
  }
  htmlParts.push(`</div>`);

  // Title is centered below header
  if (doc.frontMatter.title) {
    htmlParts.push(`<h1 class="mla-paper-title">${escapeHtml(doc.frontMatter.title)}</h1>`);
  }

  return htmlParts.join("\n");
}

export function formatToMLA(doc: ParsedDocument, options: FormatOptions = {}): FormatResult {
  const htmlParts: string[] = [];

  htmlParts.push(renderMLAHeader(doc));

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

  htmlParts.push(`<div class="mla-body-content">`);

  for (const node of doc.nodes) {
    if (node.type === "abstract") {
      htmlParts.push(`<h1 class="mla-heading">Abstract</h1>`);
      htmlParts.push(`<p class="mla-paragraph" style="text-indent: 0;">${escapeHtml(node.text || '')}</p>`);
    } else if (node.type === "keywords") {
      const formatted = processInlineContent(node.text || '');
      equationCount += formatted.equationCount;
      htmlParts.push(`<p class="mla-keywords"><em>Keywords:</em> ${formatted.html}</p>`);
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
        `<div class="algorithm-block mla-algorithm"><p class="algo-title"><strong>${escapeHtml(node.title || '')}</strong></p><div class="algo-body">${bodyHtml}</div></div>`
      );
    } else if (node.type === "table") {
      tableCount++;
      let html = "";
      html += `<p class="mla-table-caption">Table ${tableCount}<br/>${node.caption ? escapeHtml(node.caption.replace(/table\s*\d*\s*[.:*\-]*\s*/i, '')) : 'Table Title'}</p>`;
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
      htmlParts.push(`<div class="table-wrapper mla-table">${html}</div>`);
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
        `<p class="mla-reference-item"${refId ? ` id="${refId}"` : ""}>` +
        `${inline.html}${backlinkHtml}` +
        `</p>`
      );
    } else if (node.type === "heading") {
      if (node.kind === "references" || node.kind === "appendix" || node.kind === "acknowledgment") {
        htmlParts.push(`<div class="front-matter-page-break"></div><h1 class="mla-heading">Works Cited</h1>`);
      } else if (node.level === 2) {
        subsectionCounter += 1;
        htmlParts.push(`<h2 class="mla-subheading"><em>${escapeHtml(node.title || '')}</em></h2>`);
      } else {
        sectionCount += 1;
        subsectionCounter = 0;
        htmlParts.push(`<h1 class="mla-heading"><strong>${escapeHtml(node.title || '')}</strong></h1>`);
      }
    } else if (node.type === "paragraph") {
      const text = node.text || '';
      const formatted = processInlineContent(text, citationContext);
      equationCount += formatted.equationCount;
      const citationMatches = text.match(/\[\d+(?:\s*[,\-–]\s*\d+)*\]/g);
      if (citationMatches) citationCount += citationMatches.length;

      htmlParts.push(`<p class="mla-paragraph">${formatted.html}</p>`);
    }
  }

  htmlParts.push(`</div>`);

  return { html: htmlParts.join("\n"), sectionCount, tableCount, equationCount, algorithmCount, citationCount };
}

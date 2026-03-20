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

export interface FormatOptions {
  addCCSBlock?: boolean;
  addKeywordsBlock?: boolean;
}

const ACM_COPYRIGHT_BOX = `
<div class="acm-copyright-box">
  <p>Permission to make digital or hard copies of all or part of this work for personal or classroom use is granted without fee provided that copies are not made or distributed for profit or commercial advantage and that copies bear this notice and the full citation on the first page.</p>
  <p>&copy; 2026 Association for Computing Machinery.<br/>ACM ISBN 978-1-4503-XXXX-X/XX/XX...$15.00<br/>https://doi.org/10.1145/XXXXXXX.XXXXXXX</p>
</div>
`;

function renderACMAuthors(authorBlocks: AuthorBlock[]): string {
  if (!authorBlocks.length) return "";
  const blocksHtml = authorBlocks
    .map((block) => {
      const detailHtml = block.details
        .map((line) => `<p class="acm-author-detail">${escapeHtml(line)}</p>`)
        .join("");
      return (
        `<div class="acm-author-block">` +
        `<p class="acm-author-name">${escapeHtml(block.name)}</p>` +
        detailHtml +
        `</div>`
      );
    })
    .join("");

  return `<div class="acm-author-grid">${blocksHtml}</div>`;
}

export function formatToACM(doc: ParsedDocument, options: FormatOptions = {}): FormatResult {
  const addCCSBlock = options.addCCSBlock ?? true;
  const addKeywordsBlock = options.addKeywordsBlock ?? true;

  const htmlParts: string[] = [];

  // ACM Header is usually full-width (spans both columns)
  htmlParts.push(`<div class="acm-title-block">`);
  if (doc.frontMatter.title) {
    htmlParts.push(`<h1 class="acm-paper-title">${escapeHtml(doc.frontMatter.title)}</h1>`);
  }
  const authorGridHtml = renderACMAuthors(doc.frontMatter.authorBlocks);
  if (authorGridHtml) htmlParts.push(authorGridHtml);
  htmlParts.push(`</div>`);

  let sectionCount = 0;
  let subsectionCounter = 0;
  let tableCount = 0;
  let equationCount = 0;
  let algorithmCount = 0;
  let citationCount = 0;
  let citationAnchorCounter = 1;

  let keywordsWritten = false;
  let ccsWritten = false;
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

  // Insert copyright box at the start of the body for CSS floating to bottom of first column
  htmlParts.push(ACM_COPYRIGHT_BOX);

  for (const node of doc.nodes) {
    if (node.type === "abstract") {
      htmlParts.push(`<div class="acm-abstract"><p class="acm-heading-abstract"><strong>ABSTRACT</strong></p>`);
      htmlParts.push(`<p class="acm-abstract-text">${escapeHtml(node.text || '')}</p></div>`);
    } else if (node.type === "keywords") {
      const formatted = processInlineContent(node.text || '');
      equationCount += formatted.equationCount;
      htmlParts.push(`<div class="acm-keywords"><p><strong>KEYWORDS</strong></p><p>${formatted.html}</p></div>`);
      keywordsWritten = true;
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
        `<div class="algorithm-block acm-algorithm"><p class="algo-title"><strong>${escapeHtml(node.title || '')}</strong></p><div class="algo-body">${bodyHtml}</div></div>`
      );
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
      htmlParts.push(`<div class="table-wrapper acm-table">${html}</div>`);
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
        `<p class="acm-reference-item"${refId ? ` id="${refId}"` : ""}>` +
        `<span class="acm-reference-label">${node.label || ''}</span> ${inline.html}${backlinkHtml}` +
        `</p>`
      );
    } else if (node.type === "heading") {
      if (node.kind === "references" || node.kind === "appendix" || node.kind === "acknowledgment") {
        htmlParts.push(`<h1 class="acm-heading">${escapeHtml(node.title || '')}</h1>`);
      } else if (node.level === 2) {
        subsectionCounter += 1;
        htmlParts.push(`<h2 class="acm-subheading">${sectionCount}.${subsectionCounter} ${escapeHtml(node.title || '')}</h2>`);
      } else {
        sectionCount += 1;
        subsectionCounter = 0;

        if (sectionCount === 1) {
          if (addCCSBlock && !ccsWritten) {
            htmlParts.push(
              `<div class="ccs-concepts"><p class="ccs-title"><strong>CCS Concepts:</strong> &bull; <strong>Computing methodologies</strong> &rarr; Artificial intelligence</p></div>`
            );
            ccsWritten = true;
          }
          if (addKeywordsBlock && !keywordsWritten) {
            htmlParts.push(`<div class="acm-keywords"><p><strong>Keywords:</strong> research, methodology, analysis</p></div>`);
            keywordsWritten = true;
          }
        }

        htmlParts.push(`<h1 class="acm-heading">${sectionCount} ${escapeHtml(node.title || '').toUpperCase()}</h1>`);
      }
    } else if (node.type === "paragraph") {
      const text = node.text || '';
      const formatted = processInlineContent(text, citationContext);
      equationCount += formatted.equationCount;
      const citationMatches = text.match(/\[\d+(?:\s*[,\-–]\s*\d+)*\]/g);
      if (citationMatches) citationCount += citationMatches.length;

      htmlParts.push(`<p class="acm-paragraph">${formatted.html}</p>`);
    }
  }

  // Generate ACM Reference Format block at the end (or can be placed after abstract depending on variant)
  if (doc.frontMatter.authorBlocks.length > 0 && doc.frontMatter.title) {
    const authorNames = doc.frontMatter.authorBlocks.map(b => escapeHtml(b.name)).join(", ");
    htmlParts.push(`<div class="acm-reference-format">
      <strong>ACM Reference Format:</strong><br/>
      ${authorNames}. 2026. ${escapeHtml(doc.frontMatter.title)}. In <em>Proceedings of ACM Conference (Conference'26)</em>. ACM, New York, NY, USA, ${htmlParts.length} pages. https://doi.org/10.1145/nnnnnnn.nnnnnnn
    </div>`);
  }

  return { html: htmlParts.join("\n"), sectionCount, tableCount, equationCount, algorithmCount, citationCount };
}

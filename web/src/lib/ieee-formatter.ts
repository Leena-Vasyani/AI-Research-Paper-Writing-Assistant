/**
 * IEEE Paper Formatter - Deterministic, consistent formatting
 * Converts raw text to structured IEEE HTML format
 */

// Greek letter mappings
const GREEK_LETTERS: Record<string, string> = {
    "\\alpha": "α", "\\beta": "β", "\\gamma": "γ", "\\delta": "δ",
    "\\epsilon": "ε", "\\zeta": "ζ", "\\eta": "η", "\\theta": "θ",
    "\\iota": "ι", "\\kappa": "κ", "\\lambda": "λ", "\\mu": "μ",
    "\\nu": "ν", "\\xi": "ξ", "\\pi": "π", "\\rho": "ρ",
    "\\sigma": "σ", "\\tau": "τ", "\\phi": "φ", "\\chi": "χ",
    "\\psi": "ψ", "\\omega": "ω",
    "\\Alpha": "Α", "\\Beta": "Β", "\\Gamma": "Γ", "\\Delta": "Δ",
    "\\Epsilon": "Ε", "\\Zeta": "Ζ", "\\Eta": "Η", "\\Theta": "Θ",
    "\\Iota": "Ι", "\\Kappa": "Κ", "\\Lambda": "Λ", "\\Mu": "Μ",
    "\\Nu": "Ν", "\\Xi": "Ξ", "\\Pi": "Π", "\\Rho": "Ρ",
    "\\Sigma": "Σ", "\\Tau": "Τ", "\\Phi": "Φ", "\\Chi": "Χ",
    "\\Psi": "Ψ", "\\Omega": "Ω",
    "\\infty": "∞", "\\approx": "≈", "\\neq": "≠", "\\leq": "≤",
    "\\geq": "≥", "\\pm": "±", "\\times": "×", "\\div": "÷",
    "\\sum": "Σ", "\\prod": "Π", "\\partial": "∂", "\\nabla": "∇",
};

// Section name patterns
const SECTION_PATTERNS = [
    { pattern: /^(?:ABSTRACT|Abstract)$/i, roman: "", name: "ABSTRACT" },
    { pattern: /^(?:I\.|1\.|I\s|1\s)?(?:INTRODUCTION|Introduction)$/i, roman: "I", name: "INTRODUCTION" },
    { pattern: /^(?:II\.|2\.|II\s|2\s)?(?:RELATED\s?WORK|Related\s?Work|BACKGROUND|Background|LITERATURE\s?REVIEW)$/i, roman: "II", name: "RELATED WORK" },
    { pattern: /^(?:III\.|3\.|III\s|3\s)?(?:METHODOLOGY|Methodology|METHOD|Method|APPROACH|Approach|PROPOSED\s?METHOD)$/i, roman: "III", name: "METHODOLOGY" },
    { pattern: /^(?:IV\.|4\.|IV\s|4\s)?(?:SYSTEM|System|IMPLEMENTATION|Implementation|ARCHITECTURE)$/i, roman: "IV", name: "SYSTEM IMPLEMENTATION" },
    { pattern: /^(?:V\.|5\.|V\s|5\s)?(?:EXPERIMENT|Experiment|RESULTS|Results|EVALUATION|Evaluation|EXPERIMENTAL)$/i, roman: "V", name: "EXPERIMENTAL RESULTS" },
    { pattern: /^(?:VI\.|6\.|VI\s|6\s)?(?:DISCUSSION|Discussion|ANALYSIS)$/i, roman: "VI", name: "DISCUSSION" },
    { pattern: /^(?:VII\.|7\.|VII\s|7\s)?(?:CONCLUSION|Conclusion|CONCLUSIONS)$/i, roman: "VII", name: "CONCLUSION" },
    { pattern: /^(?:VIII\.|8\.|VIII\s|8\s)?(?:FUTURE\s?WORK|Future\s?Work)$/i, roman: "VIII", name: "FUTURE WORK" },
    { pattern: /^(?:REFERENCES|References|BIBLIOGRAPHY)$/i, roman: "", name: "REFERENCES" },
    { pattern: /^(?:APPENDIX|Appendix)(?:\s?[A-Z])?$/i, roman: "", name: "APPENDIX" },
];

// Subsection patterns (A., B., C., or a), b), c))
const SUBSECTION_PATTERN = /^([A-Z])[.\)]\s*(.+)$/;

/**
 * Convert LaTeX math to HTML with proper rendering
 */
function convertMath(text: string): string {
    // Replace Greek letters
    let result = text;
    for (const [latex, unicode] of Object.entries(GREEK_LETTERS)) {
        result = result.replace(new RegExp(latex.replace(/\\/g, "\\\\"), "g"), unicode);
    }

    // Convert subscripts: x_i or x_{ij}
    result = result.replace(/(\w)_\{([^}]+)\}/g, "$1<sub>$2</sub>");
    result = result.replace(/(\w)_(\w)/g, "$1<sub>$2</sub>");

    // Convert superscripts: x^2 or x^{2n}
    result = result.replace(/(\w)\^\{([^}]+)\}/g, "$1<sup>$2</sup>");
    result = result.replace(/(\w)\^(\w)/g, "$1<sup>$2</sup>");

    // Convert fractions: \frac{a}{b}
    result = result.replace(/\\frac\{([^}]+)\}\{([^}]+)\}/g, "($1/$2)");

    // Convert sqrt
    result = result.replace(/\\sqrt\{([^}]+)\}/g, "√($1)");

    // Remove remaining backslashes for common commands
    result = result.replace(/\\text\{([^}]+)\}/g, "$1");
    result = result.replace(/\\mathbf\{([^}]+)\}/g, "<strong>$1</strong>");
    result = result.replace(/\\textbf\{([^}]+)\}/g, "<strong>$1</strong>");
    result = result.replace(/\\textit\{([^}]+)\}/g, "<em>$1</em>");
    result = result.replace(/\\emph\{([^}]+)\}/g, "<em>$1</em>");

    // Clean up remaining LaTeX artifacts
    result = result.replace(/\\\\/g, "");
    result = result.replace(/\\[a-zA-Z]+/g, "");

    return result;
}

/**
 * Process inline math ($...$) and display math ($$...$$)
 */
function processMathExpressions(text: string): string {
    // Display math ($$...$$) -> blockquote
    let result = text.replace(/\$\$([^$]+)\$\$/g, (_, math) => {
        return `<blockquote class="equation"><em>${convertMath(math.trim())}</em></blockquote>`;
    });

    // Inline math ($...$) -> italic
    result = result.replace(/\$([^$]+)\$/g, (_, math) => {
        return `<em class="math">${convertMath(math.trim())}</em>`;
    });

    return result;
}

/**
 * Detect and convert ASCII tables to HTML tables
 */
function convertTable(lines: string[]): string {
    const rows: string[][] = [];

    for (const line of lines) {
        // Skip separator lines (---+---)
        if (/^[\s\-+|=]+$/.test(line)) continue;

        // Parse pipe-separated values
        const cells = line
            .split("|")
            .map((c) => c.trim())
            .filter((c) => c);

        if (cells.length > 0) {
            rows.push(cells);
        }
    }

    if (rows.length === 0) return "";

    // First row is header
    const headerRow = rows[0];
    const dataRows = rows.slice(1);

    let html = "<table>\n<thead>\n<tr>";
    for (const cell of headerRow) {
        html += `<th>${processMathExpressions(cell)}</th>`;
    }
    html += "</tr>\n</thead>\n<tbody>\n";

    for (const row of dataRows) {
        html += "<tr>";
        for (const cell of row) {
            html += `<td>${processMathExpressions(cell)}</td>`;
        }
        html += "</tr>\n";
    }

    html += "</tbody>\n</table>";
    return html;
}

/**
 * Check if a line looks like part of a table
 */
function isTableLine(line: string): boolean {
    const trimmed = line.trim();
    // Has multiple | characters or is a separator line
    return (trimmed.split("|").length > 2) || /^[\s\-+|=]+$/.test(trimmed);
}

/**
 * Detect section type from a line
 */
function detectSection(line: string): { type: "section" | "subsection" | null; name: string; roman: string } {
    const trimmed = line.trim();

    // Check main sections
    for (const sect of SECTION_PATTERNS) {
        if (sect.pattern.test(trimmed)) {
            return { type: "section", name: sect.name, roman: sect.roman };
        }
    }

    // Check subsections (A. Something, B. Something)
    const subMatch = trimmed.match(SUBSECTION_PATTERN);
    if (subMatch) {
        return { type: "subsection", name: `${subMatch[1]}. ${subMatch[2]}`, roman: "" };
    }

    return { type: null, name: "", roman: "" };
}

export interface FormatResult {
    html: string;
    sectionCount: number;
    tableCount: number;
    equationCount: number;
}

/**
 * Main formatting function - deterministic IEEE formatting
 */
export function formatToIEEE(rawText: string): FormatResult {
    const lines = rawText.split("\n");
    const htmlParts: string[] = [];
    let currentParagraph: string[] = [];
    let inTable = false;
    let tableLines: string[] = [];
    let sectionCount = 0;
    let tableCount = 0;
    let equationCount = 0;
    let isFirstSection = true;
    let inAbstract = false;

    const flushParagraph = () => {
        if (currentParagraph.length > 0) {
            let text = currentParagraph.join(" ").trim();
            if (text) {
                text = processMathExpressions(text);
                // Count equations
                equationCount += (text.match(/<em class="math">/g) || []).length;
                equationCount += (text.match(/<blockquote class="equation">/g) || []).length;

                if (inAbstract) {
                    htmlParts.push(`<p><em>${text}</em></p>`);
                } else {
                    htmlParts.push(`<p>${text}</p>`);
                }
            }
            currentParagraph = [];
        }
    };

    const flushTable = () => {
        if (tableLines.length > 0) {
            const tableHtml = convertTable(tableLines);
            if (tableHtml) {
                htmlParts.push(tableHtml);
                tableCount++;
            }
            tableLines = [];
            inTable = false;
        }
    };

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const trimmed = line.trim();

        // Skip empty lines (flush paragraph)
        if (!trimmed) {
            flushTable();
            flushParagraph();
            continue;
        }

        // Check for table
        if (isTableLine(trimmed)) {
            flushParagraph();
            inTable = true;
            tableLines.push(trimmed);
            continue;
        } else if (inTable) {
            flushTable();
        }

        // Check for sections
        const section = detectSection(trimmed);
        if (section.type === "section") {
            flushParagraph();
            sectionCount++;

            // Handle Abstract specially
            if (section.name === "ABSTRACT") {
                inAbstract = true;
                htmlParts.push(`<h1>ABSTRACT</h1>`);
            } else {
                inAbstract = false;
                const label = section.roman ? `${section.roman}. ${section.name}` : section.name;
                htmlParts.push(`<h1>${label}</h1>`);
            }
            continue;
        }

        if (section.type === "subsection") {
            flushParagraph();
            inAbstract = false;
            htmlParts.push(`<h2>${section.name}</h2>`);
            continue;
        }

        // Check if this might be a title (first non-empty line, all caps or title case)
        if (isFirstSection && htmlParts.length === 0) {
            const isAllCaps = trimmed === trimmed.toUpperCase() && trimmed.length > 10;
            const isTitleCase = /^[A-Z][a-zA-Z\s:,\-]+$/.test(trimmed) && trimmed.length > 15;

            if (isAllCaps || isTitleCase) {
                htmlParts.push(`<h1 class="paper-title">${trimmed}</h1>`);
                isFirstSection = false;
                continue;
            }
        }

        // Regular paragraph content
        currentParagraph.push(trimmed);
    }

    // Flush remaining content
    flushTable();
    flushParagraph();

    return {
        html: htmlParts.join("\n"),
        sectionCount,
        tableCount,
        equationCount,
    };
}

/**
 * Estimate page count based on content length
 * Rough estimate: ~3000 characters per page for 2-column, ~4500 for 1-column
 */
export function estimatePageCount(html: string, colCount: 1 | 2): number {
    // Strip HTML tags to get text length
    const textLength = html.replace(/<[^>]+>/g, "").length;
    const charsPerPage = colCount === 2 ? 3000 : 4500;
    return Math.max(1, Math.ceil(textLength / charsPerPage));
}

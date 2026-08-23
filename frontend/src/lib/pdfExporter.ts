/**
 * FinExplain Universal PDF Exporter
 * Generates standard PDF (1.4 compliant) binary files directly in the browser
 * with automatic text wrapping, pagination, structured tables, and styled headers.
 */

export interface PdfTable {
  headers: string[];
  rows: string[][];
}

export interface PdfSection {
  title?: string;
  subtitle?: string;
  content?: string | string[];
  table?: PdfTable;
  bulletPoints?: string[];
  keyValuePairs?: Array<{ label: string; value: string }>;
}

export interface PdfExportOptions {
  filename: string;
  title: string;
  subtitle?: string;
  author?: string;
  metadata?: Record<string, string>;
  sections: PdfSection[];
  rawMarkdownFallback?: string;
}

/**
 * Escapes characters for PDF literal strings (parentheses, backslashes)
 */
function escapePdfText(text: string): string {
  if (!text) return "";
  return text
    .replace(/\\/g, "\\\\")
    .replace(/\(/g, "\\(")
    .replace(/\)/g, "\\)")
    .replace(/[\r\n]+/g, " ");
}

/**
 * Basic word wrapper for fixed-width PDF text blocks
 */
function wrapText(text: string, maxCharsPerLine = 85): string[] {
  if (!text) return [];
  const words = text.split(/\s+/);
  const lines: string[] = [];
  let currentLine = "";

  for (const word of words) {
    if ((currentLine + " " + word).trim().length <= maxCharsPerLine) {
      currentLine = (currentLine + " " + word).trim();
    } else {
      if (currentLine) lines.push(currentLine);
      currentLine = word;
    }
  }
  if (currentLine) lines.push(currentLine);
  return lines;
}

/**
 * Generates a valid standard PDF 1.4 binary file in memory
 */
export function generatePdfBlob(options: PdfExportOptions): Blob {
  const { title, subtitle, author = "FinExplain Financial RAG Engine", metadata = {}, sections } = options;

  // Page dimensions (Standard Letter / A4: 595 x 842 pt)
  const pageWidth = 595;
  const pageHeight = 842;
  const margin = 50;
  const contentWidth = pageWidth - margin * 2;

  // Layout cursor state
  const pages: string[][] = [];
  let currentPageStream: string[] = [];
  let currentY = pageHeight - margin; // Starts at top (PDF coords go bottom-up: 0 to 842)

  function startNewPage() {
    if (currentPageStream.length > 0) {
      pages.push([...currentPageStream]);
      currentPageStream = [];
    }
    currentY = pageHeight - margin;
  }

  function ensureSpace(requiredHeight: number) {
    if (currentY - requiredHeight < margin) {
      startNewPage();
    }
  }

  // Draw Page Header on first page
  currentPageStream.push("BT");
  currentPageStream.push("/F1 20 Tf");
  currentPageStream.push(`${margin} ${currentY} Td`);
  currentPageStream.push(`(${escapePdfText(title)}) Tj`);
  currentPageStream.push("ET");
  currentY -= 25;

  if (subtitle) {
    currentPageStream.push("BT");
    currentPageStream.push("/F2 11 Tf");
    currentPageStream.push(`${margin} ${currentY} Td`);
    currentPageStream.push(`(${escapePdfText(subtitle)}) Tj`);
    currentPageStream.push("ET");
    currentY -= 18;
  }

  // Metadata Timestamp line
  const metaLine = `Generated on ${new Date().toLocaleString("en-IN")} | ${author}`;
  currentPageStream.push("BT");
  currentPageStream.push("/F2 9 Tf");
  currentPageStream.push(`${margin} ${currentY} Td`);
  currentPageStream.push(`(${escapePdfText(metaLine)}) Tj`);
  currentPageStream.push("ET");
  currentY -= 15;

  // Header separator line
  currentPageStream.push(`${margin} ${currentY} m ${pageWidth - margin} ${currentY} l S`);
  currentY -= 20;

  // Render Key Metadata if provided
  const metaKeys = Object.keys(metadata);
  if (metaKeys.length > 0) {
    ensureSpace(30 + metaKeys.length * 14);
    currentPageStream.push("BT");
    currentPageStream.push("/F1 11 Tf");
    currentPageStream.push(`${margin} ${currentY} Td`);
    currentPageStream.push("(Document Overview & Scope:) Tj");
    currentPageStream.push("ET");
    currentY -= 16;

    for (const key of metaKeys) {
      const val = metadata[key];
      currentPageStream.push("BT");
      currentPageStream.push("/F2 9 Tf");
      currentPageStream.push(`${margin + 10} ${currentY} Td`);
      currentPageStream.push(`(${escapePdfText(`* ${key}: ${val}`)}) Tj`);
      currentPageStream.push("ET");
      currentY -= 13;
    }
    currentY -= 10;
  }

  // Render Sections
  for (const sec of sections) {
    // Section Header
    if (sec.title) {
      ensureSpace(40);
      currentPageStream.push("BT");
      currentPageStream.push("/F1 13 Tf");
      currentPageStream.push(`${margin} ${currentY} Td`);
      currentPageStream.push(`(${escapePdfText(sec.title)}) Tj`);
      currentPageStream.push("ET");
      currentY -= 18;
    }

    if (sec.subtitle) {
      ensureSpace(20);
      currentPageStream.push("BT");
      currentPageStream.push("/F2 10 Tf");
      currentPageStream.push(`${margin} ${currentY} Td`);
      currentPageStream.push(`(${escapePdfText(sec.subtitle)}) Tj`);
      currentPageStream.push("ET");
      currentY -= 15;
    }

    // Content paragraphs
    if (sec.content) {
      const paragraphs = Array.isArray(sec.content) ? sec.content : [sec.content];
      for (const p of paragraphs) {
        const wrappedLines = wrapText(p, 80);
        for (const line of wrappedLines) {
          ensureSpace(14);
          currentPageStream.push("BT");
          currentPageStream.push("/F2 9.5 Tf");
          currentPageStream.push(`${margin} ${currentY} Td`);
          currentPageStream.push(`(${escapePdfText(line)}) Tj`);
          currentPageStream.push("ET");
          currentY -= 13;
        }
        currentY -= 6;
      }
    }

    // Key Value Pairs
    if (sec.keyValuePairs && sec.keyValuePairs.length > 0) {
      for (const kv of sec.keyValuePairs) {
        const lines = wrapText(`${kv.label}: ${kv.value}`, 80);
        for (let i = 0; i < lines.length; i++) {
          ensureSpace(14);
          currentPageStream.push("BT");
          currentPageStream.push(i === 0 ? "/F1 9.5 Tf" : "/F2 9.5 Tf");
          currentPageStream.push(`${margin + 8} ${currentY} Td`);
          currentPageStream.push(`(${escapePdfText(lines[i])}) Tj`);
          currentPageStream.push("ET");
          currentY -= 13;
        }
      }
      currentY -= 6;
    }

    // Bullet Points
    if (sec.bulletPoints && sec.bulletPoints.length > 0) {
      for (const bp of sec.bulletPoints) {
        const lines = wrapText(`- ${bp}`, 78);
        for (const line of lines) {
          ensureSpace(14);
          currentPageStream.push("BT");
          currentPageStream.push("/F2 9.5 Tf");
          currentPageStream.push(`${margin + 8} ${currentY} Td`);
          currentPageStream.push(`(${escapePdfText(line)}) Tj`);
          currentPageStream.push("ET");
          currentY -= 13;
        }
      }
      currentY -= 6;
    }

    // Tables
    if (sec.table && sec.table.rows.length > 0) {
      const headers = sec.table.headers;
      const numCols = headers.length;
      const colWidth = contentWidth / numCols;

      // Table Header Row
      ensureSpace(24);
      currentPageStream.push(`${margin} ${currentY - 2} m ${pageWidth - margin} ${currentY - 2} l S`);
      for (let c = 0; c < numCols; c++) {
        const colX = margin + c * colWidth;
        currentPageStream.push("BT");
        currentPageStream.push("/F1 9 Tf");
        currentPageStream.push(`${colX + 3} ${currentY} Td`);
        currentPageStream.push(`(${escapePdfText(headers[c].slice(0, 24))}) Tj`);
        currentPageStream.push("ET");
      }
      currentY -= 16;

      // Table Data Rows
      for (const row of sec.table.rows) {
        ensureSpace(18);
        for (let c = 0; c < numCols; c++) {
          const colX = margin + c * colWidth;
          const cellVal = row[c] || "-";
          currentPageStream.push("BT");
          currentPageStream.push("/F2 8.5 Tf");
          currentPageStream.push(`${colX + 3} ${currentY} Td`);
          currentPageStream.push(`(${escapePdfText(cellVal.slice(0, 32))}) Tj`);
          currentPageStream.push("ET");
        }
        currentY -= 14;
      }
      currentY -= 10;
    }

    currentY -= 8;
  }

  // Push final page
  if (currentPageStream.length > 0) {
    pages.push(currentPageStream);
  }

  // Build Standard PDF 1.4 Object Structures
  const totalPages = pages.length || 1;
  const objects: string[] = [];
  const xrefOffsets: number[] = [];

  let pdfString = "%PDF-1.4\n";

  function addObject(content: string): number {
    const objNum = objects.length + 1;
    xrefOffsets.push(pdfString.length);
    const objStr = `${objNum} 0 obj\n${content}\nendobj\n`;
    pdfString += objStr;
    objects.push(objStr);
    return objNum;
  }

  // Object 1: Catalog
  // Object 2: Pages Root
  // Object 3: Font Helvetica Bold (F1)
  // Object 4: Font Helvetica Regular (F2)

  // Placeholders for Page object numbers
  const pageObjIds: number[] = [];
  const contentObjIds: number[] = [];

  // We will construct objects sequentially
  // 1: Catalog
  addObject("<< /Type /Catalog /Pages 2 0 R >>");

  // 2: Pages root placeholder (will compute page objects after)
  // Let's create font objects
  const f1Obj = addObject("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>");
  const f2Obj = addObject("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>");

  // Create page content streams
  for (let i = 0; i < totalPages; i++) {
    const pageCommands = pages[i] || [];
    // Add page number footer
    const footerText = `Page ${i + 1} of ${totalPages}  |  FinExplain Verified Credit Audit`;
    pageCommands.push("BT");
    pageCommands.push("/F2 8 Tf");
    pageCommands.push(`${margin} 30 Td`);
    pageCommands.push(`(${escapePdfText(footerText)}) Tj`);
    pageCommands.push("ET");

    const streamContent = pageCommands.join("\n");
    const streamLength = streamContent.length;
    const contentObj = addObject(`<< /Length ${streamLength} >>\nstream\n${streamContent}\nendstream`);
    contentObjIds.push(contentObj);
  }

  // Create Page objects
  for (let i = 0; i < totalPages; i++) {
    const pageObj = addObject(
      `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${pageWidth} ${pageHeight}] ` +
      `/Contents ${contentObjIds[i]} 0 R ` +
      `/Resources << /Font << /F1 ${f1Obj} 0 R /F2 ${f2Obj} 0 R >> >> >>`
    );
    pageObjIds.push(pageObj);
  }

  // Re-generate entire PDF with correct Pages Root in position 2
  // We can write a clean, well-indexed output string:
  let finalPdf = "%PDF-1.4\n";
  const finalOffsets: number[] = [];

  function addFinalObj(content: string): number {
    finalOffsets.push(finalPdf.length);
    const num = finalOffsets.length;
    finalPdf += `${num} 0 obj\n${content}\nendobj\n`;
    return num;
  }

  // 1: Catalog
  addFinalObj("<< /Type /Catalog /Pages 2 0 R >>");

  // 2: Pages root
  const pageRefs = pageObjIds.map((_, idx) => `${idx + 5 + totalPages} 0 R`).join(" ");
  addFinalObj(`<< /Type /Pages /Kids [${pageRefs}] /Count ${totalPages} >>`);

  // 3: F1 Font
  addFinalObj("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>");
  // 4: F2 Font
  addFinalObj("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>");

  // 5..(4+totalPages): Content streams
  for (let i = 0; i < totalPages; i++) {
    const pageCommands = pages[i] || [];
    const footerText = `Page ${i + 1} of ${totalPages}  |  FinExplain Verified Credit Audit`;
    pageCommands.push("BT");
    pageCommands.push("/F2 8 Tf");
    pageCommands.push(`${margin} 30 Td`);
    pageCommands.push(`(${escapePdfText(footerText)}) Tj`);
    pageCommands.push("ET");

    const streamContent = pageCommands.join("\n");
    addFinalObj(`<< /Length ${streamContent.length} >>\nstream\n${streamContent}\nendstream`);
  }

  // (5+totalPages)..(4+2*totalPages): Page objects
  for (let i = 0; i < totalPages; i++) {
    const contentRef = `${i + 5} 0 R`;
    addFinalObj(
      `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${pageWidth} ${pageHeight}] ` +
      `/Contents ${contentRef} ` +
      `/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> >>`
    );
  }

  // Cross-reference table (xref)
  const xrefOffset = finalPdf.length;
  finalPdf += "xref\n";
  finalPdf += `0 ${finalOffsets.length + 1}\n`;
  finalPdf += "0000000000 65535 f \n";
  for (const offset of finalOffsets) {
    finalPdf += `${String(offset).padStart(10, "0")} 00000 n \n`;
  }

  // Trailer
  finalPdf += "trailer\n";
  finalPdf += `<< /Size ${finalOffsets.length + 1} /Root 1 0 R >>\n`;
  finalPdf += "startxref\n";
  finalPdf += `${xrefOffset}\n`;
  finalPdf += "%%EOF\n";

  return new Blob([finalPdf], { type: "application/pdf" });
}

/**
 * Triggers standard browser file download of the generated PDF Blob
 */
export function downloadPdf(options: PdfExportOptions): void {
  const blob = generatePdfBlob(options);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = options.filename.endsWith(".pdf") ? options.filename : `${options.filename}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

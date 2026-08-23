import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface FormattedMarkdownProps {
  content: string;
  className?: string;
}

/**
 * Preprocesses raw LLM responses:
 * 1. Cleans raw LaTeX math notation (e.g. $\text{APR} = ...$, \times, \frac) into readable formatted math.
 * 2. Structures multi-sentence dense text into readable bullet points when appropriate.
 * 3. Normalizes stray escaped brackets and asterisks.
 */
function preprocessMarkdown(raw: string): string {
  if (!raw) return "";

  let text = raw;

  // 1. Transform raw LaTeX math blocks / inline math:
  // e.g. $\text{APR} = (((( \text{Fee} + ... ) / ... ) \times 365) \times 100)$
  text = text.replace(/\$\$([\s\S]*?)\$\$|\$([^$]+?)\$/g, (match, blockMath, inlineMath) => {
    let math = (blockMath || inlineMath || "").trim();
    // Clean \text{...} -> ...
    math = math.replace(/\\text\{([^}]+)\}/g, "$1");
    // Clean \times -> × or *
    math = math.replace(/\\times/g, "×");
    // Clean \cdot -> ·
    math = math.replace(/\\cdot/g, "·");
    // Clean \frac{a}{b} -> (a / b)
    math = math.replace(/\\frac\{([^}]+)\}\{([^}]+)\}/g, "($1 / $2)");
    // Clean \approx -> ≈
    math = math.replace(/\\approx/g, "≈");
    // Clean \le -> ≤, \ge -> ≥
    math = math.replace(/\\le/g, "≤").replace(/\\ge/g, "≥");
    // Clean \pm -> ±
    math = math.replace(/\\pm/g, "±");
    // Clean multiple spaces and escaped chars
    math = math.replace(/\\([a-zA-Z]+)/g, "$1");
    math = math.replace(/\s+/g, " ");

    return `\`${math}\``;
  });

  // 2. If the text is a dense paragraph with multiple distinct sentence claims followed by citations,
  // split them into distinct readable bullet points:
  // e.g. "The loan processing charge is 3% [Page 18]. The APR is calculated using [Page 18]."
  const sentenceCount = (text.match(/\[Page\s+\d+[^\]]*\]/gi) || []).length;
  if (sentenceCount >= 2 && !text.includes("\n- ") && !text.includes("\n* ") && !text.includes("\n1. ")) {
    // Break before each subsequent major claim
    text = text.replace(/(\.\s+)(?=[A-Z][^.!?]*\[Page\s+\d+)/g, "$1\n\n- ");
    if (!text.startsWith("- ")) {
      text = "- " + text;
    }
  }

  return text;
}

export function FormattedMarkdown({ content, className = "" }: FormattedMarkdownProps) {
  if (!content) return null;

  const processedContent = preprocessMarkdown(content);

  return (
    <div className={`prose prose-invert max-w-none text-sm text-white/90 leading-relaxed break-words [overflow-wrap:anywhere] ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="text-lg sm:text-xl font-bold text-white mt-5 mb-2.5 pb-1.5 border-b border-white/10 flex items-center gap-2 first:mt-0">
              <span className="h-2 w-2 rounded-full bg-primary inline-block shrink-0" />
              <span>{children}</span>
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-base sm:text-lg font-bold text-white mt-4 mb-2 flex items-center gap-2 first:mt-0">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 inline-block shrink-0" />
              <span>{children}</span>
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mt-3.5 mb-1.5 first:mt-0">
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-xs font-semibold text-white/80 mt-2.5 mb-1 first:mt-0">
              {children}
            </h4>
          ),
          p: ({ children }) => {
            return (
              <p className="text-sm text-white/90 leading-relaxed mb-3 last:mb-0 break-words">
                {children}
              </p>
            );
          },
          ul: ({ children }) => (
            <ul className="list-disc pl-5 space-y-2 mb-3.5 text-sm text-white/85 marker:text-primary">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal pl-5 space-y-2 mb-3.5 text-sm text-white/85 marker:text-emerald-400 font-medium">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="text-sm text-white/85 leading-relaxed break-words pl-0.5">
              {children}
            </li>
          ),
          strong: ({ children }) => (
            <strong className="font-semibold text-white bg-white/5 px-1 py-0.5 rounded text-xs sm:text-sm">
              {children}
            </strong>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-primary/70 bg-primary/5 pl-3.5 pr-3 py-2 my-2.5 rounded-r-xl text-xs text-white/90 leading-relaxed border-y border-r border-white/5 shadow-sm">
              {children}
            </blockquote>
          ),
          pre: ({ children }) => (
            <pre className="overflow-x-auto p-3.5 rounded-xl bg-black/70 border border-white/10 text-xs font-mono my-3 text-emerald-400/95 max-w-full shadow-inner">
              {children}
            </pre>
          ),
          code: ({ children }) => {
            const codeStr = String(children);
            const isFormula = codeStr.includes("=") || codeStr.includes("×") || codeStr.includes("/") || codeStr.includes("+");
            if (isFormula && codeStr.length > 20) {
              return (
                <div className="my-2.5 p-2.5 sm:p-3 rounded-xl bg-black/40 border border-primary/30 text-xs font-mono text-primary-light flex items-start gap-2 shadow-inner">
                  <i className="fa-solid fa-calculator text-primary text-xs mt-0.5 shrink-0" />
                  <span className="break-all">{codeStr}</span>
                </div>
              );
            }
            return (
              <code className="bg-white/10 text-primary-light px-1.5 py-0.5 rounded text-xs font-mono border border-white/10 break-all">
                {children}
              </code>
            );
          },
          table: ({ children }) => (
            <div className="w-full overflow-x-auto my-3.5 rounded-xl border border-white/10 bg-surface-2/80 shadow-md backdrop-blur-sm">
              <table className="w-full text-xs text-left border-collapse min-w-[480px]">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-white/10 text-white font-semibold border-b border-white/10">
              {children}
            </thead>
          ),
          tbody: ({ children }) => (
            <tbody className="divide-y divide-white/5">
              {children}
            </tbody>
          ),
          tr: ({ children }) => (
            <tr className="hover:bg-white/5 transition-colors even:bg-white/[0.02]">
              {children}
            </tr>
          ),
          th: ({ children }) => (
            <th className="px-3.5 py-2.5 font-semibold text-white text-xs uppercase tracking-wider bg-white/5">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-3.5 py-2.5 text-white/90 text-xs leading-relaxed align-top">
              {children}
            </td>
          ),
          hr: () => (
            <hr className="my-4 border-white/10" />
          ),
        }}
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  );
}

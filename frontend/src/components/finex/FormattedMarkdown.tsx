import React from "react";
import ReactMarkdown from "react-markdown";

interface FormattedMarkdownProps {
  content: string;
  className?: string;
}

export function FormattedMarkdown({ content, className = "" }: FormattedMarkdownProps) {
  if (!content) return null;

  return (
    <div className={`prose prose-invert max-w-none text-sm text-white/90 leading-relaxed break-words [overflow-wrap:anywhere] ${className}`}>
      <ReactMarkdown
        components={{
          h1: ({ children }) => (
            <h1 className="text-base font-bold text-white mt-3.5 mb-2 pb-1 border-b border-white/10 first:mt-0">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-sm font-bold text-white mt-3 mb-1.5 first:mt-0">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mt-2.5 mb-1 first:mt-0">
              {children}
            </h3>
          ),
          p: ({ children }) => (
            <p className="text-sm text-white/90 leading-relaxed mb-2.5 last:mb-0 break-words">
              {children}
            </p>
          ),
          ul: ({ children }) => (
            <ul className="list-disc pl-5 space-y-1.5 mb-3 text-sm text-white/85">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal pl-5 space-y-1.5 mb-3 text-sm text-white/85">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="text-sm text-white/85 leading-relaxed break-words">
              {children}
            </li>
          ),
          strong: ({ children }) => (
            <strong className="font-semibold text-white">
              {children}
            </strong>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-primary/60 bg-white/5 pl-3.5 py-2 my-2.5 rounded-r-lg text-xs text-white/85 italic leading-relaxed">
              {children}
            </blockquote>
          ),
          pre: ({ children }) => (
            <pre className="overflow-x-auto p-3 rounded-xl bg-black/40 border border-white/10 text-xs font-mono my-2 text-white/90 max-w-full">
              {children}
            </pre>
          ),
          code: ({ children }) => (
            <code className="bg-white/10 text-primary-light px-1.5 py-0.5 rounded text-xs font-mono break-all">
              {children}
            </code>
          ),
          table: ({ children }) => (
            <div className="w-full overflow-x-auto my-3 rounded-xl border border-white/10 bg-black/20">
              <table className="w-full text-xs text-left border-collapse min-w-[280px]">
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
            <tr className="hover:bg-white/5 transition-colors">
              {children}
            </tr>
          ),
          th: ({ children }) => (
            <th className="px-3 py-2 font-semibold text-white text-xs">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-3 py-2 text-white/90 text-xs break-words">
              {children}
            </td>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

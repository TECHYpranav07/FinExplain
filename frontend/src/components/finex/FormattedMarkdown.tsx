import React from "react";
import ReactMarkdown from "react-markdown";

interface FormattedMarkdownProps {
  content: string;
  className?: string;
}

export function FormattedMarkdown({ content, className = "" }: FormattedMarkdownProps) {
  if (!content) return null;

  return (
    <div className={`prose prose-invert max-w-none text-sm text-white/90 leading-relaxed space-y-3 ${className}`}>
      <ReactMarkdown
        components={{
          h1: ({ children }) => (
            <h1 className="text-base font-bold text-white mt-4 mb-2 pb-1 border-b border-white/10 first:mt-0">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-sm font-bold text-white mt-3.5 mb-1.5 first:mt-0">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mt-3 mb-1 first:mt-0">
              {children}
            </h3>
          ),
          p: ({ children }) => (
            <p className="text-sm text-white/90 leading-relaxed mb-2.5 last:mb-0">
              {children}
            </p>
          ),
          ul: ({ children }) => (
            <ul className="list-disc list-inside space-y-1.5 mb-3 pl-1 text-sm text-white/85">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-inside space-y-1.5 mb-3 pl-1 text-sm text-white/85">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="text-sm text-white/85 leading-relaxed">
              {children}
            </li>
          ),
          strong: ({ children }) => (
            <strong className="font-semibold text-white">
              {children}
            </strong>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-primary/50 bg-surface-2/60 pl-3 py-1.5 my-2 rounded-r text-xs text-white/80 italic">
              {children}
            </blockquote>
          ),
          code: ({ children }) => (
            <code className="bg-surface-3 text-primary-light px-1.5 py-0.5 rounded text-xs font-mono">
              {children}
            </code>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

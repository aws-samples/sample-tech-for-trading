'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

/**
 * Renders assistant markdown (headings, GFM tables, code blocks, lists)
 * with dark-theme styling that matches the glass UI.
 */
export default function MarkdownMessage({ content }: { content: string }) {
  return (
    <div className="markdown-message text-gray-200 text-sm leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="text-lg font-bold text-white mt-4 mb-2 first:mt-0">{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-base font-bold text-accent-blue mt-4 mb-2 first:mt-0">{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-sm font-bold text-accent-blue/90 mt-3 mb-1.5 first:mt-0">{children}</h3>
          ),
          p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
          ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-0.5">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-0.5">{children}</ol>,
          li: ({ children }) => <li className="text-gray-300">{children}</li>,
          strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
          hr: () => <hr className="border-white/10 my-3" />,
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer"
               className="text-accent-blue underline hover:text-accent-purple">
              {children}
            </a>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-accent-blue/50 pl-3 my-2 text-gray-400 italic">
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto my-3 rounded-lg border border-white/10">
              <table className="w-full text-xs">{children}</table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-white/10 text-gray-100">{children}</thead>
          ),
          tbody: ({ children }) => (
            <tbody className="divide-y divide-white/5">{children}</tbody>
          ),
          tr: ({ children }) => <tr className="hover:bg-white/5 transition-colors">{children}</tr>,
          th: ({ children }) => (
            <th className="px-3 py-2 text-left font-semibold whitespace-nowrap">{children}</th>
          ),
          td: ({ children }) => (
            <td className="px-3 py-1.5 text-gray-300 whitespace-nowrap">{children}</td>
          ),
          code: ({ className, children }) => {
            const isBlock = /language-/.test(className || '') || String(children).includes('\n');
            if (isBlock) {
              return (
                <code className="block bg-black/40 border border-white/10 rounded-lg p-3 my-2 overflow-x-auto text-xs font-mono text-emerald-300">
                  {children}
                </code>
              );
            }
            return (
              <code className="bg-white/10 rounded px-1.5 py-0.5 text-xs font-mono text-emerald-300">
                {children}
              </code>
            );
          },
          pre: ({ children }) => <pre className="my-0">{children}</pre>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

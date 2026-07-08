import ReactMarkdown from "react-markdown";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import remarkGfm from "remark-gfm";

const schema = {
  ...defaultSchema,
  tagNames: [
    "p", "strong", "em", "code", "pre", "ul", "ol", "li",
    "table", "thead", "tbody", "tr", "th", "td",
    "h1", "h2", "h3", "h4", "h5", "h6", "a", "br", "hr",
    "details", "summary",
  ],
  attributes: {
    ...defaultSchema.attributes,
    a: ["href", "title", "rel", "target"],
  },
};

interface SafeMarkdownProps {
  content: string;
}

export function SafeMarkdown({ content }: SafeMarkdownProps) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[[rehypeSanitize, schema]]}
      components={{
        p: ({ children, ...props }) => (
          <p className="mb-3" {...props}>
            {children}
          </p>
        ),
        h1: ({ children, ...props }) => (
          <h1 className="text-xl font-bold mb-3 mt-4" {...props}>
            {children}
          </h1>
        ),
        h2: ({ children, ...props }) => (
          <h2 className="text-lg font-bold mb-3 mt-4" {...props}>
            {children}
          </h2>
        ),
        h3: ({ children, ...props }) => (
          <h3 className="text-base font-bold mb-2 mt-3" {...props}>
            {children}
          </h3>
        ),
        h4: ({ children, ...props }) => (
          <h4 className="text-sm font-bold mb-2 mt-3" {...props}>
            {children}
          </h4>
        ),
        ul: ({ children, ...props }) => (
          <ul className="list-disc pl-5 mb-3" {...props}>
            {children}
          </ul>
        ),
        ol: ({ children, ...props }) => (
          <ol className="list-decimal pl-5 mb-3" {...props}>
            {children}
          </ol>
        ),
        li: ({ children, ...props }) => (
          <li className="mb-1" {...props}>
            {children}
          </li>
        ),
        strong: ({ children, ...props }) => (
          <strong className="font-semibold" {...props}>
            {children}
          </strong>
        ),
        code: ({ children, ...props }) => (
          <code className="bg-blue-950/60 px-1.5 py-0.5 rounded text-sm font-mono border border-blue-800/30" {...props}>
            {children}
          </code>
        ),
        pre: ({ children, ...props }) => (
          <pre className="bg-blue-950/60 p-3 rounded-lg mb-3 overflow-x-auto border border-blue-800/30" {...props}>
            {children}
          </pre>
        ),
        hr: ({ ...props }) => (
          <hr className="my-4 border-blue-700/30" {...props} />
        ),
        a: ({ href, children, ...props }) => (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-300 underline hover:text-blue-200"
            {...props}
          >
            {children}
          </a>
        ),
        table: ({ children, ...props }) => (
          <div className="my-3 overflow-x-auto rounded-lg border border-blue-800/30">
            <table className="min-w-full text-xs" {...props}>
              {children}
            </table>
          </div>
        ),
        thead: ({ children, ...props }) => (
          <thead className="bg-blue-950/60 text-slate-200" {...props}>
            {children}
          </thead>
        ),
        th: ({ children, ...props }) => (
          <th className="px-2 py-1 text-left font-medium" {...props}>
            {children}
          </th>
        ),
        td: ({ children, ...props }) => (
          <td className="border-t border-blue-800/30 px-2 py-1" {...props}>
            {children}
          </td>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

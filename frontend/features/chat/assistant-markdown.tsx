"use client";

import { type ReactNode } from "react";

function inlineFormat(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|https?:\/\/[^\s<]+)/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let key = 0;
  while ((match = re.exec(text)) !== null) {
    if (match.index > last) {
      nodes.push(text.slice(last, match.index));
    }
    const token = match[0];
    if (token.startsWith("**") && token.endsWith("**")) {
      nodes.push(<strong key={key++}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith("*") && token.endsWith("*")) {
      nodes.push(<em key={key++}>{token.slice(1, -1)}</em>);
    } else if (token.startsWith("`") && token.endsWith("`")) {
      nodes.push(
        <code key={key++} className="rounded bg-[var(--border)]/60 px-1 py-0.5 text-[0.85em]">
          {token.slice(1, -1)}
        </code>,
      );
    } else if (token.startsWith("http")) {
      const href = token.replace(/[),.;]+$/, "");
      const trailing = token.slice(href.length);
      nodes.push(
        <a
          key={key++}
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="underline underline-offset-2"
        >
          {href}
        </a>,
      );
      if (trailing) nodes.push(trailing);
    } else {
      nodes.push(token);
    }
    last = match.index + token.length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

function renderBlock(block: string, key: number): ReactNode {
  const lines = block.split("\n");
  const listLines = lines.filter((l) => l.trim().length > 0);
  const isList = listLines.length > 0 && listLines.every((l) => /^[-*]\s+/.test(l.trim()));
  if (isList) {
    return (
      <ul key={key} className="my-1 list-disc space-y-1 pl-5">
        {listLines.map((l, i) => (
          <li key={i}>{inlineFormat(l.trim().replace(/^[-*]\s+/, ""))}</li>
        ))}
      </ul>
    );
  }
  return (
    <p key={key} className="my-1 whitespace-pre-wrap">
      {inlineFormat(block)}
    </p>
  );
}

export function AssistantMarkdown({ content }: { content: string }) {
  if (!content) return null;
  const blocks = content.split(/\n{2,}/);
  return (
    <div className="text-sm leading-6 break-words [&_a]:text-[var(--accent)]">
      {blocks.map((block, i) => renderBlock(block, i))}
    </div>
  );
}

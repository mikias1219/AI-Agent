import type { ReactNode } from "react";

export type PageFrameProps = {
  children: ReactNode;
  /** Narrower column for reading-heavy screens (chat, inbox). */
  width?: "content" | "chat" | "full";
  className?: string;
};

const WIDTH: Record<NonNullable<PageFrameProps["width"]>, string> = {
  content: "max-w-[var(--content-width)]",
  chat: "max-w-[var(--chat-text-width)]",
  full: "max-w-none",
};

/** Shared page column. The shell owns the destination title; pages own tabs and content. */
export function PageFrame({ children, width = "content", className = "" }: PageFrameProps) {
  return (
    <div className={`mx-auto flex w-full flex-col gap-5 ${WIDTH[width]} ${className}`.trim()}>
      {children}
    </div>
  );
}

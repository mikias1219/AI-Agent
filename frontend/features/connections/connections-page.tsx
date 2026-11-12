import { ChannelGrid } from "./channel-grid";

export function ConnectionsPage() {
  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-5">
      <header>
        <p className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">
          Connections
        </p>
        <h1
          className="mt-2 text-2xl font-semibold tracking-tight text-[var(--ink)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Channels
        </h1>
        <p className="mt-2 max-w-xl text-sm text-[var(--muted)]">
          Open a channel to work in it. Telegram, Google, and MCP use the live API.
        </p>
      </header>
      <ChannelGrid />
    </div>
  );
}

import { ChannelGrid } from "./channel-grid";
import { GoogleAppsGrid } from "./google-apps-grid";
import { BackupSyncCard } from "./sync-card";

export type ConnectionsPageProps = {
  embedded?: boolean;
};

export function ConnectionsPage({ embedded = false }: ConnectionsPageProps) {
  const body = (
    <>
      <ChannelGrid />
      <GoogleAppsGrid />
      <BackupSyncCard />
    </>
  );

  if (embedded) {
    return <div className="flex flex-col gap-5">{body}</div>;
  }

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
          Open a channel to work in it. Warnings appear only when something is broken or
          disconnected — healthy connections stay quiet.
        </p>
      </header>
      {body}
    </div>
  );
}

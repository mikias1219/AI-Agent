"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { apiErrorMessage } from "@/lib/api/client";
import {
  createMcpServer,
  deleteMcpServer,
  discoverMcpServer,
  listMcpServers,
  patchMcpServer,
  type McpServer,
} from "@/lib/api/mcp";

export function McpPage() {
  const [items, setItems] = useState<McpServer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState("Echo");
  const [transport, setTransport] = useState<"stdio" | "http">("stdio");
  const [command, setCommand] = useState("python3 scripts/mcp_echo_server.py");
  const [url, setUrl] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await listMcpServers());
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await createMcpServer({
        name,
        transport,
        command: transport === "stdio" ? command : "",
        url: transport === "http" ? url : "",
        enabled: true,
        read_only: false,
      });
      await load();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function toggle(server: McpServer) {
    setBusy(true);
    try {
      await patchMcpServer(server.id, { enabled: !server.enabled });
      await load();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function toggleReadOnly(server: McpServer) {
    setBusy(true);
    try {
      await patchMcpServer(server.id, { read_only: !server.read_only });
      await load();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function onDiscover(server: McpServer) {
    setBusy(true);
    try {
      await discoverMcpServer(server.id);
      await load();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(server: McpServer) {
    setBusy(true);
    try {
      await deleteMcpServer(server.id);
      await load();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-5">
      <header>
        <Link
          href="/connections"
          className="text-xs font-medium text-[var(--accent)] hover:underline"
        >
          All channels
        </Link>
        <h1
          className="mt-2 text-2xl font-semibold tracking-tight text-[var(--ink)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          MCP servers
        </h1>
        <p className="mt-2 text-sm text-[var(--muted)]">
          Discover tools from stdio or HTTP MCP servers. Outputs are untrusted; execute tools need
          approval unless marked read-only.
        </p>
      </header>

      <form
        onSubmit={onCreate}
        className="flex flex-col gap-3 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4"
      >
        <Field label="Name" htmlFor="mcp-name">
          <Input id="mcp-name" value={name} onChange={(e) => setName(e.target.value)} required />
        </Field>
        <Field label="Transport" htmlFor="mcp-transport">
          <select
            id="mcp-transport"
            value={transport}
            onChange={(e) => setTransport(e.target.value as "stdio" | "http")}
            className="w-full rounded-[var(--radius)] border border-[var(--border)] bg-[var(--canvas)] px-3 py-2 text-sm"
          >
            <option value="stdio">stdio</option>
            <option value="http">http (Streamable HTTP)</option>
          </select>
        </Field>
        {transport === "stdio" ? (
          <Field label="Command" htmlFor="mcp-command">
            <Input
              id="mcp-command"
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              required
            />
          </Field>
        ) : (
          <Field label="URL" htmlFor="mcp-url">
            <Input id="mcp-url" value={url} onChange={(e) => setUrl(e.target.value)} required />
          </Field>
        )}
        <div className="flex justify-end">
          <Button type="submit" disabled={busy}>
            Add server
          </Button>
        </div>
      </form>

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-[var(--muted)]">
          <Spinner size="sm" /> Loading MCP servers…
        </div>
      ) : null}

      {error ? (
        <p className="text-sm text-[var(--danger)]" role="alert">
          {error}{" "}
          <Button size="sm" variant="secondary" onClick={() => void load()}>
            Retry
          </Button>
        </p>
      ) : null}

      {!loading && items.length === 0 ? (
        <EmptyState
          title="No MCP servers"
          description="Add the local echo server to try discovery from chat."
        />
      ) : null}

      <ul className="flex flex-col gap-3">
        {items.map((server) => (
          <li
            key={server.id}
            className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h2 className="text-sm font-semibold text-[var(--ink)]">{server.name}</h2>
                <p className="mt-1 text-xs text-[var(--muted)]">
                  {server.transport}
                  {server.enabled ? " · enabled" : " · disabled"}
                  {server.read_only ? " · read-only" : " · execute (approval)"}
                </p>
                <p className="mt-1 break-all text-xs text-[var(--muted)]">
                  {server.transport === "stdio" ? server.command : server.url}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={busy}
                  onClick={() => void toggle(server)}
                >
                  {server.enabled ? "Disable" : "Enable"}
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={busy}
                  onClick={() => void toggleReadOnly(server)}
                >
                  {server.read_only ? "Allow execute" : "Mark read-only"}
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={busy}
                  onClick={() => void onDiscover(server)}
                >
                  Discover
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={busy}
                  onClick={() => void onDelete(server)}
                >
                  Remove
                </Button>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

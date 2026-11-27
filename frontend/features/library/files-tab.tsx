"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type DragEvent } from "react";
import { Download, FileText, HardDrive, Image as ImageIcon, Search, Upload } from "lucide-react";
import { Button, buttonClassName } from "@/components/ui/button";
import { DataTable, type Column } from "@/components/ui/data-table";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { KpiCard } from "@/components/ui/kpi-card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { apiErrorMessage } from "@/lib/api/client";
import {
  fileContentUrl,
  getFileStats,
  listFiles,
  uploadFile,
  type FileItem,
} from "@/lib/api/files";
import { FilePreviewModal } from "./file-preview-modal";
import {
  ALLOWED_MIMES,
  dataUrlToBase64,
  formatBytes,
  isImageMime,
  relativeTime,
  STORAGE_CAP_BYTES,
  storagePercent,
  validateUpload,
} from "./library-logic";
import { DriveBadge } from "./drive-badge";
import { AskCompassLink, ErrorBlock, TOUCH, useLoad } from "./shared";

type Filter = "all" | "image" | "file";
const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "image", label: "Images" },
  { id: "file", label: "Documents" },
];

type QueueItem = {
  id: number;
  name: string;
  status: "queued" | "uploading" | "done" | "failed";
  error?: string;
};

function readAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error("Could not read this file."));
    reader.readAsDataURL(file);
  });
}

export function FilesTab() {
  const { toast } = useToast();
  const [filter, setFilter] = useState<Filter>("all");
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [dragging, setDragging] = useState(false);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const counter = useRef(0);

  useEffect(() => {
    const t = window.setTimeout(() => setDebounced(search.trim()), 250);
    return () => window.clearTimeout(t);
  }, [search]);

  const stats = useLoad(() => getFileStats(), []);
  const list = useLoad(
    () => listFiles({ kind: filter === "all" ? undefined : filter, q: debounced, limit: 200 }),
    [filter, debounced],
  );

  const reloadAll = useCallback(() => {
    stats.reload();
    list.reload();
  }, [stats, list]);

  const items = list.data ?? [];
  const images = useMemo(
    () => items.filter((f) => f.kind === "image" && isImageMime(f.mime)),
    [items],
  );
  const docs = useMemo(
    () => items.filter((f) => f.kind !== "image" || !isImageMime(f.mime)),
    [items],
  );

  function patchQueue(id: number, patch: Partial<QueueItem>) {
    setQueue((q) => q.map((x) => (x.id === id ? { ...x, ...patch } : x)));
  }

  async function handleFiles(fileList: FileList | File[]) {
    const files = Array.from(fileList);
    if (files.length === 0) return;
    const entries = files.map((file) => ({ file, id: ++counter.current }));
    setQueue((q) => [
      ...q.filter((x) => x.status === "uploading" || x.status === "queued"),
      ...entries.map(({ file, id }) => ({ id, name: file.name, status: "queued" as const })),
    ]);
    let done = 0;
    for (const { file, id } of entries) {
      const check = validateUpload(file);
      if (!check.ok) {
        patchQueue(id, { status: "failed", error: check.error });
        continue;
      }
      patchQueue(id, { status: "uploading" });
      try {
        const data = dataUrlToBase64(await readAsDataUrl(file));
        await uploadFile({ name: file.name, mime: check.mime, data_base64: data });
        patchQueue(id, { status: "done" });
        done += 1;
      } catch (err) {
        patchQueue(id, { status: "failed", error: apiErrorMessage(err) });
      }
    }
    if (done > 0) {
      toast(done === 1 ? "File uploaded." : `${done} files uploaded.`, "success");
      reloadAll();
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    void handleFiles(e.dataTransfer.files);
  }

  const used = stats.data?.bytes ?? 0;
  const pct = storagePercent(used);
  const previewIndex = previewId ? items.findIndex((f) => f.id === previewId) : -1;

  const columns: Column<FileItem>[] = [
    {
      id: "name",
      header: "Name",
      sortValue: (f) => f.name.toLowerCase(),
      cell: (f) => <span className="block max-w-[16rem] truncate font-medium">{f.name}</span>,
    },
    {
      id: "type",
      header: "Type",
      hideOnMobile: true,
      sortValue: (f) => f.mime,
      cell: (f) => <span className="text-[var(--muted)]">{f.mime}</span>,
    },
    {
      id: "size",
      header: "Size",
      align: "right",
      sortValue: (f) => f.size,
      cell: (f) => <span className="tabular-nums">{formatBytes(f.size)}</span>,
    },
    {
      id: "added",
      header: "Added",
      hideOnMobile: true,
      sortValue: (f) => f.created_at,
      cell: (f) => <span className="text-[var(--muted)]">{relativeTime(f.created_at)}</span>,
    },
    {
      id: "actions",
      header: "Actions",
      align: "right",
      cell: (f) => (
        <span className="inline-flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
          <a
            href={fileContentUrl(f)}
            download={f.name}
            className={buttonClassName(
              "ghost",
              "sm",
              `${TOUCH} focus-visible:outline-2 focus-visible:outline-[var(--accent)]`,
            )}
            aria-label={`Download ${f.name}`}
          >
            <Download className="h-4 w-4" aria-hidden />
          </a>
        </span>
      ),
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-3 sm:grid-cols-3">
        {stats.loading && !stats.data ? (
          <>
            <Skeleton heightClass="h-28" />
            <Skeleton heightClass="h-28" />
            <Skeleton heightClass="h-28" />
          </>
        ) : stats.error ? (
          <div className="sm:col-span-3">
            <ErrorBlock message={`Could not load stats: ${stats.error}`} onRetry={stats.reload} />
          </div>
        ) : (
          <>
            <KpiCard label="Files" value={stats.data?.files ?? 0} icon={FileText} />
            <KpiCard label="Images" value={stats.data?.images ?? 0} icon={ImageIcon} />
            <KpiCard
              label="Storage used"
              value={formatBytes(used)}
              icon={HardDrive}
              tone={pct >= 90 ? "warning" : "default"}
              trend={undefined}
              hint={`${pct}% of ${formatBytes(STORAGE_CAP_BYTES)}`}
            />
          </>
        )}
      </div>
      {stats.data ? (
        <div
          role="progressbar"
          aria-label="Storage used"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={pct}
          className="-mt-2 h-1.5 overflow-hidden rounded-full bg-[var(--border)]"
        >
          <div
            className={`h-full ${pct >= 90 ? "bg-[var(--warning)]" : "bg-[var(--accent)]"}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      ) : null}

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-0 flex-1 basis-48">
          <Search
            className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-[var(--muted)]"
            aria-hidden
          />
          <Input
            type="search"
            aria-label="Search files"
            placeholder="Search files"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="min-h-11 pl-9 sm:min-h-0"
          />
        </div>
        <div role="group" aria-label="Show" className="flex gap-1">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              aria-pressed={filter === f.id}
              onClick={() => setFilter(f.id)}
              className={`min-h-11 rounded-full border px-3 text-sm font-medium focus-visible:outline-2 focus-visible:outline-[var(--accent)] sm:min-h-9 ${
                filter === f.id
                  ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)]"
                  : "border-[var(--border)] bg-[var(--surface)] text-[var(--muted)] hover:text-[var(--ink)]"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <Button className={TOUCH} onClick={() => inputRef.current?.click()}>
          <Upload className="h-4 w-4" aria-hidden />
          Upload
        </Button>
        <input
          ref={inputRef}
          type="file"
          multiple
          hidden
          accept={[...ALLOWED_MIMES, ".md", ".csv", ".txt", ".json"].join(",")}
          onChange={(e) => {
            if (e.target.files) void handleFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`rounded-[var(--radius)] border border-dashed px-4 py-4 text-center text-sm text-[var(--muted)] transition ${
          dragging
            ? "border-[var(--accent)] bg-[var(--accent-soft)]"
            : "border-[var(--border)] bg-[var(--surface)]"
        }`}
      >
        Drop files here, up to 5 MB each. Images, PDF, text, Markdown, CSV and JSON.
      </div>

      {queue.length > 0 ? (
        <ul className="flex flex-col gap-1 text-sm" aria-live="polite" aria-label="Uploads">
          {queue.map((q) => (
            <li
              key={q.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2"
            >
              <span className="min-w-0 truncate">{q.name}</span>
              <span
                className={
                  q.status === "failed"
                    ? "text-[var(--danger)]"
                    : q.status === "done"
                      ? "text-[var(--success)]"
                      : "text-[var(--muted)]"
                }
              >
                {q.status === "queued" && "Queued"}
                {q.status === "uploading" && "Uploading…"}
                {q.status === "done" && "Done"}
                {q.status === "failed" && (q.error ?? "Failed")}
              </span>
            </li>
          ))}
        </ul>
      ) : null}

      {list.error ? (
        <ErrorBlock message={`Could not load files: ${list.error}`} onRetry={list.reload} />
      ) : list.loading && !list.data ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4" aria-busy="true">
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} heightClass="aspect-square" />
          ))}
        </div>
      ) : items.length === 0 ? (
        debounced ? (
          <EmptyState
            compact
            title="No files match"
            description="Try a different word."
            action={
              <Button variant="secondary" className={TOUCH} onClick={() => setSearch("")}>
                Clear search
              </Button>
            }
          />
        ) : (
          <EmptyState
            title="No files yet."
            description="Upload an image or document, or drop it above. You can find it again by name or by asking Compass."
            action={
              <div className="flex flex-wrap items-center justify-center gap-2">
                <Button className={TOUCH} onClick={() => inputRef.current?.click()}>
                  Upload
                </Button>
                <AskCompassLink prompt={"Find my files about "} label="Ask Compass" />
              </div>
            }
          />
        )
      ) : (
        <div className="flex flex-col gap-5" aria-busy={list.loading}>
          {images.length > 0 ? (
            <ul
              className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4"
              aria-label="Images"
            >
              {images.map((f) => (
                <li key={f.id} className="min-w-0">
                  <button
                    type="button"
                    onClick={() => setPreviewId(f.id)}
                    className="group block w-full overflow-hidden rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] text-left focus-visible:outline-2 focus-visible:outline-[var(--accent)]"
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={fileContentUrl(f)}
                      alt={f.name}
                      loading="lazy"
                      className="aspect-square w-full object-cover"
                    />
                    <span className="block truncate px-2 py-1.5 text-xs text-[var(--muted)]">
                      {f.name}
                    </span>
                    <span className="block px-2 pb-1.5">
                      <DriveBadge driveUrl={f.drive_url} />
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
          {docs.length > 0 ? (
            <div className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)]">
              <DataTable
                label="Documents"
                columns={columns}
                rows={docs}
                rowKey={(f) => f.id}
                pageSize={10}
                onRowClick={(f) => setPreviewId(f.id)}
                initialSort={{ id: "added", dir: "desc" }}
              />
            </div>
          ) : null}
        </div>
      )}

      <FilePreviewModal
        items={items}
        index={previewIndex}
        onIndex={(i) => setPreviewId(items[i]?.id ?? null)}
        onClose={() => setPreviewId(null)}
        onChanged={reloadAll}
      />
    </div>
  );
}

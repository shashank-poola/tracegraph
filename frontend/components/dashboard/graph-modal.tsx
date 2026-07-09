"use client";

import { useMemo, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Code2,
  Copy,
  Database,
  ExternalLink,
  Search,
} from "lucide-react";
import { Modal } from "@/components/ui/modal";
import { cn } from "@/lib/utils";
import type { RepoTree } from "@/lib/api";

function FileRow({
  file,
  query,
}: {
  file: RepoTree["files"][number];
  query: string;
}) {
  const [open, setOpen] = useState(false);
  const symbols = [
    ...file.classes.map((c) => ({ kind: "class", name: c.name })),
    ...file.functions.map((f) => ({ kind: "func", name: f.name })),
  ];
  const count = symbols.length;
  const hay = `${file.path} ${symbols.map((s) => s.name).join(" ")}`.toLowerCase();
  if (query && !hay.includes(query.toLowerCase())) return null;

  return (
    <div className="border-b border-border last:border-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-4 py-2.5 text-left transition-colors hover:bg-white/[0.03]"
      >
        {open ? (
          <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted" />
        )}
        <Code2 className="h-3.5 w-3.5 shrink-0 text-muted" />
        <span className="min-w-0 flex-1 truncate font-mono text-xs text-foreground">
          {file.path}
        </span>
        <span className="shrink-0 text-[11px] text-muted">{count} sym</span>
      </button>
      {open && symbols.length > 0 && (
        <div className="border-t border-border bg-white/[0.02] px-4 py-2">
          {symbols.map((s) => (
            <div
              key={`${s.kind}-${s.name}`}
              className="flex items-center gap-2 py-1 font-mono text-[11px] text-muted"
            >
              <span className="rounded border border-border px-1 text-[10px] uppercase">
                {s.kind}
              </span>
              {s.name}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function GraphModal({
  open,
  onClose,
  fullName,
  tree,
}: {
  open: boolean;
  onClose: () => void;
  fullName: string;
  tree: RepoTree | null;
}) {
  const [query, setQuery] = useState("");
  const graph = tree?.graph;

  const files = useMemo(
    () => (tree?.files ?? []).filter((f) => f.parsed !== false),
    [tree],
  );

  if (!tree || !graph) return null;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Knowledge graph · ${fullName}`}
      icon={<Database className="h-4 w-4 text-foreground" strokeWidth={1.5} />}
      subtitle="The codebase parsed into an AST and mirrored into Neo4j. Explore the per-file symbols below, or run a scoped query in the Aura console."
      headerRight={
        graph.console_url ? (
          <a
            href={graph.console_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex h-9 items-center gap-2 rounded-full bg-foreground px-4 text-sm font-medium text-background transition-colors hover:bg-zinc-200"
          >
            Open Neo4j console
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        ) : undefined
      }
      className="max-w-6xl"
    >
      <div className="flex flex-wrap gap-2 border-b border-border px-6 py-3">
        <span className="rounded-full border border-border px-2.5 py-0.5 text-xs text-foreground">
          {graph.nodes_written.toLocaleString()} nodes
        </span>
        <span className="rounded-full border border-border px-2.5 py-0.5 text-xs text-foreground">
          {graph.relationships_written.toLocaleString()} relationships
        </span>
        <span className="rounded-full border border-border px-2.5 py-0.5 text-xs text-muted">
          {fullName}
        </span>
      </div>

      <div className="grid min-h-[420px] md:grid-cols-2">
        <div className="flex flex-col border-b border-border md:border-b-0 md:border-r">
          <div className="relative border-b border-border px-4 py-3">
            <Search className="pointer-events-none absolute left-7 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search files, classes, functions…"
              className="w-full rounded-md border border-border bg-transparent py-2 pl-9 pr-3 text-xs text-foreground placeholder:text-muted focus:border-zinc-500 focus:outline-none"
            />
          </div>
          <div className="flex-1 overflow-y-auto">
            {files.map((file) => (
              <FileRow key={file.path} file={file} query={query} />
            ))}
          </div>
        </div>

        <div className="flex flex-col">
          <div className="border-b border-border px-4 py-3">
            <span className="text-[11px] font-medium uppercase tracking-wider text-muted">
              Scoped queries
            </span>
          </div>
          <div className="flex-1 space-y-3 overflow-y-auto p-4">
            {graph.queries.map((q) => (
              <QueryCard key={q.name} name={q.name} cypher={q.cypher} />
            ))}
          </div>
        </div>
      </div>
    </Modal>
  );
}

function QueryCard({ name, cypher }: { name: string; cypher: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await navigator.clipboard.writeText(cypher);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="rounded-lg border border-border">
      <div className="flex items-center justify-between gap-2 border-b border-border px-3 py-2">
        <span className="text-xs font-medium text-foreground">{name}</span>
        <button
          type="button"
          onClick={handleCopy}
          className={cn(
            "flex items-center gap-1 rounded px-2 py-0.5 text-[11px] transition-colors",
            copied
              ? "text-emerald-400"
              : "text-muted hover:bg-white/5 hover:text-foreground",
          )}
        >
          <Copy className="h-3 w-3" />
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="overflow-x-auto p-3 font-mono text-[11px] leading-5 text-muted">
        {cypher}
      </pre>
    </div>
  );
}

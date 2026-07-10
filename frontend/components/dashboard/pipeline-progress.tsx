"use client";

import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import type { JobStatus } from "@/lib/api";

type Step = { label: string; at: number };

const GRAPH_STEPS: Step[] = [
  { label: "Fetch repository", at: 0.05 },
  { label: "Parse AST", at: 0.35 },
  { label: "Describe files", at: 0.55 },
  { label: "Build Neo4j graph", at: 0.9 },
];

const CRAWL_STEPS: Step[] = [
  { label: "Discover screens", at: 0.2 },
  { label: "Attach screenshots", at: 0.55 },
  { label: "Label screens", at: 0.85 },
];

const INGEST_STEPS: Step[] = [
  { label: "Fetch documentation", at: 0.15 },
  { label: "Extract requirements", at: 0.5 },
  { label: "Persist layers", at: 0.85 },
];

function activeIndex(steps: Step[], progress: number) {
  let idx = 0;
  for (let i = 0; i < steps.length; i++) {
    if (progress >= steps[i].at) idx = i;
  }
  return idx;
}

export function PipelineProgress({
  status,
  kind = "graph",
}: {
  status: JobStatus;
  kind?: "graph" | "ingest" | "crawl";
}) {
  const steps =
    kind === "graph"
      ? GRAPH_STEPS
      : kind === "ingest"
        ? INGEST_STEPS
        : CRAWL_STEPS;
  const isError = status.state === "error";
  const isDone = status.state === "done";
  const pct = Math.round(status.progress * 100);
  const current = activeIndex(steps, status.progress);

  return (
    <div className="mt-2 flex flex-col gap-3 rounded-lg border border-border/60 bg-white/[0.02] p-3">
      <div className="flex items-center justify-between text-[11px]">
        <span className={cn(isError ? "text-red-400" : "text-muted")}>
          {isError
            ? status.error ?? "Something went wrong"
            : isDone
              ? "Complete"
              : status.message || steps[current]?.label}
        </span>
        <span className="font-medium text-foreground">{pct}%</span>
      </div>

      <div className="relative h-2 overflow-hidden rounded-md bg-white/10">
        <div
          className={cn(
            "h-full rounded-md transition-all duration-500 ease-out",
            isError
              ? "bg-red-500"
              : kind === "graph"
                ? "progress-gradient animate-shimmer"
                : "progress-gradient-ingest animate-shimmer",
          )}
          style={{ width: `${Math.max(pct, isError ? 100 : 3)}%` }}
        />
        {!isError && !isDone && (
          <div
            className="animate-pulse-glow absolute inset-y-0 w-8 rounded-md bg-white/20 blur-sm"
            style={{ left: `calc(${Math.max(pct - 4, 0)}% - 8px)` }}
          />
        )}
      </div>

      <ol className="flex flex-col gap-1.5">
        {steps.map((step, i) => {
          const done = isDone || i < current || (i === current && pct >= 99);
          const active = !isDone && !isError && i === current;
          return (
            <li
              key={step.label}
              className={cn(
                "flex items-center gap-2 text-[11px] transition-colors",
                done && "text-emerald-400",
                active && "text-cyan-300",
                !done && !active && "text-muted/60",
                isError && i === current && "text-red-400",
              )}
            >
              <span
                className={cn(
                  "flex h-4 w-4 shrink-0 items-center justify-center rounded-sm border",
                  done && "border-emerald-500/50 bg-emerald-500/20",
                  active && "border-cyan-400/50 bg-cyan-400/10",
                  !done && !active && "border-border",
                )}
              >
                {done ? (
                  <Check className="h-2.5 w-2.5" />
                ) : (
                  <span
                    className={cn(
                      "h-1.5 w-1.5 rounded-full",
                      active ? "bg-cyan-400 animate-pulse" : "bg-zinc-600",
                    )}
                  />
                )}
              </span>
              {step.label}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

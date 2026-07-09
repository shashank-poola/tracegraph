"use client";

import { useEffect, useState } from "react";
import { ExternalLink, GitPullRequest } from "lucide-react";
import { cn } from "@/lib/utils";
import { type PullRequest, listRepoPulls } from "@/lib/api";

const RISK_DOT: Record<string, string> = {
  low: "bg-emerald-400",
  medium: "bg-amber-400",
  high: "bg-red-400",
};

const VERDICT_LABEL: Record<string, string> = {
  approve: "Looks good",
  request_changes: "Changes requested",
  comment: "Review notes",
};

export function PullRequestsPanel({ fullName }: { fullName: string }) {
  const [pulls, setPulls] = useState<PullRequest[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    listRepoPulls(fullName)
      .then((res) => setPulls(res.pulls))
      .catch((err) => setError(err.message ?? "Failed to load pull requests"));
  }, [fullName]);

  return (
    <div>
      <h2 className="font-heading text-lg text-foreground">Pull requests</h2>
      <p className="mt-1 text-sm text-muted">
        Every PR is fetched from GitHub, persisted to the database, and shown
        with its blast-radius review.
      </p>

      <div className="mt-4 rounded-xl border border-border">
        {error && (
          <p className="p-6 text-center text-sm text-red-400">{error}</p>
        )}

        {!pulls && !error && (
          <p className="p-6 text-center text-sm text-muted">Loading…</p>
        )}

        {pulls && pulls.length === 0 && (
          <p className="p-6 text-center text-sm text-muted">
            No pull requests found for this repository.
          </p>
        )}

        {pulls?.map((pr, i) => (
          <a
            key={pr.number}
            href={pr.review?.comment_url || pr.html_url}
            target="_blank"
            rel="noreferrer"
            className={cn(
              "flex items-center justify-between gap-4 px-5 py-4 transition-colors hover:bg-white/[0.03]",
              i !== 0 && "border-t border-border",
            )}
          >
            <div className="flex items-center gap-3 overflow-hidden">
              <GitPullRequest className="h-4 w-4 shrink-0 text-muted" />
              <div className="flex flex-col overflow-hidden">
                <span className="truncate text-sm text-foreground">
                  #{pr.number} {pr.title}
                </span>
                <span className="text-xs text-muted">
                  {pr.author} · {pr.state}
                </span>
              </div>
            </div>

            <div className="flex shrink-0 items-center gap-2">
              {pr.review ? (
                <span className="flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-[11px] text-muted">
                  <span
                    className={cn(
                      "h-1.5 w-1.5 rounded-full",
                      RISK_DOT[pr.review.risk] ?? "bg-zinc-500",
                    )}
                  />
                  {VERDICT_LABEL[pr.review.verdict] ?? pr.review.verdict}
                </span>
              ) : (
                <span className="rounded-full border border-border px-2.5 py-1 text-[11px] text-muted">
                  Not reviewed
                </span>
              )}
              <ExternalLink className="h-3.5 w-3.5 text-muted" />
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { ExternalLink, GitPullRequest } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  type PullRequest,
  getRepoAppInstalled,
  getRepoPull,
  githubInstallUrl,
  listRepoPulls,
} from "@/lib/api";

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

const STATE_BADGE: Record<string, string> = {
  open: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
  merged: "border-purple-500/30 bg-purple-500/10 text-purple-400",
  closed: "border-zinc-500/30 bg-zinc-500/10 text-zinc-400",
};

function PrStat({
  label,
  value,
  accent,
}: {
  label: string;
  value: number | string;
  accent?: "green" | "red";
}) {
  return (
    <div className="flex flex-col rounded-lg border border-border px-4 py-3">
      <span className="text-[11px] text-muted">{label}</span>
      <span
        className={cn(
          "mt-0.5 font-heading text-lg text-foreground",
          accent === "green" && "text-emerald-400",
          accent === "red" && "text-red-400",
        )}
      >
        {value}
      </span>
    </div>
  );
}

export function PullRequestsPanel({ fullName }: { fullName: string }) {
  const [pulls, setPulls] = useState<PullRequest[] | null>(null);
  const [selectedNumber, setSelectedNumber] = useState<number | null>(null);
  const [selected, setSelected] = useState<PullRequest | null>(null);
  const [error, setError] = useState("");
  const [appInstalled, setAppInstalled] = useState<boolean | null>(null);

  useEffect(() => {
    getRepoAppInstalled(fullName)
      .then((res) => setAppInstalled(res.required ? res.installed : true))
      .catch(() => setAppInstalled(null));
  }, [fullName]);

  useEffect(() => {
    listRepoPulls(fullName)
      .then((res) => {
        setPulls(res.pulls);
        if (res.pulls.length > 0) {
          setSelectedNumber(res.pulls[0].number);
          setSelected(res.pulls[0]);
        }
      })
      .catch((err) => setError(err.message ?? "Failed to load pull requests"));
  }, [fullName]);

  useEffect(() => {
    if (selectedNumber == null) return;
    getRepoPull(fullName, selectedNumber)
      .then(setSelected)
      .catch(() => {
        // keep list-level data on detail fetch failure
      });
  }, [fullName, selectedNumber]);

  const reviewedCount =
    pulls?.filter((pr) => pr.review != null).length ?? 0;

  return (
    <div>
      <h2 className="font-heading text-lg text-foreground">Pull requests</h2>
      <p className="mt-1 text-sm text-muted">
        Every PR is fetched from GitHub, persisted to the database, and shown
        with its blast-radius review.
      </p>
      {pulls && (
        <p className="mt-2 text-xs text-muted">
          {pulls.length} pull request{pulls.length === 1 ? "" : "s"} ·{" "}
          {reviewedCount} reviewed · persisted in DB
        </p>
      )}

      {appInstalled === false && (
        <div className="mt-4 rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-sm text-amber-200/90">
          The TraceGraph GitHub App is not installed on this repository. PR
          webhooks and automatic review comments will not run until you{" "}
          <a
            href={githubInstallUrl()}
            className="font-medium text-amber-100 underline underline-offset-2"
          >
            install the app
          </a>
          .
        </div>
      )}

      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
        <div className="rounded-xl border border-border">
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
            <button
              key={pr.number}
              type="button"
              onClick={() => {
                setSelectedNumber(pr.number);
                setSelected(pr);
              }}
              className={cn(
                "flex w-full flex-col gap-2 px-5 py-4 text-left transition-colors hover:bg-white/[0.03]",
                i !== 0 && "border-t border-border",
                selected?.number === pr.number && "bg-white/[0.04]",
              )}
            >
              <span className="line-clamp-2 text-sm text-foreground">
                {pr.title}
              </span>
              <span className="text-xs text-muted">
                #{pr.number} {pr.author}
                {pr.head_ref && pr.base_ref
                  ? ` · ${pr.head_ref} → ${pr.base_ref}`
                  : ""}
              </span>
              <div className="flex flex-wrap gap-2">
                <span
                  className={cn(
                    "rounded-full border px-2 py-0.5 text-[11px] capitalize",
                    STATE_BADGE[pr.state] ?? STATE_BADGE.closed,
                  )}
                >
                  {pr.state}
                </span>
                <span className="rounded-full border border-border px-2 py-0.5 text-[11px] text-muted">
                  {pr.review ? "reviewed" : "not reviewed"}
                </span>
              </div>
            </button>
          ))}
        </div>

        <div className="rounded-xl border border-border">
          {!selected && pulls && pulls.length > 0 && (
            <p className="p-6 text-center text-sm text-muted">
              Select a pull request
            </p>
          )}

          {selected && (
            <div className="flex flex-col gap-5 p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <GitPullRequest className="h-4 w-4 shrink-0 text-muted" />
                    <h3 className="font-heading text-base text-foreground">
                      {selected.title}
                    </h3>
                  </div>
                  <p className="mt-1 text-xs text-muted">
                    #{selected.number} {selected.author}
                    {selected.head_ref && selected.base_ref
                      ? ` · ${selected.head_ref} → ${selected.base_ref}`
                      : ""}
                  </p>
                </div>
                <a
                  href={selected.html_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex h-9 shrink-0 items-center gap-1.5 rounded-full border border-border px-4 text-sm text-foreground transition-colors hover:bg-white/5"
                >
                  GitHub
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              </div>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
                <PrStat label="Commits" value={selected.commits ?? 0} />
                <PrStat label="Files" value={selected.changed_files ?? 0} />
                <PrStat
                  label="+Added"
                  value={selected.additions ?? 0}
                  accent="green"
                />
                <PrStat
                  label="−Removed"
                  value={selected.deletions ?? 0}
                  accent="red"
                />
                <PrStat
                  label="Comments"
                  value={
                    (selected.comments ?? 0) + (selected.review_comments ?? 0)
                  }
                />
              </div>

              {selected.review ? (
                <div className="rounded-lg border border-border bg-white/[0.02] p-4">
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        "h-2 w-2 rounded-full",
                        RISK_DOT[selected.review.risk] ?? "bg-zinc-500",
                      )}
                    />
                    <span className="text-sm font-medium text-foreground">
                      {VERDICT_LABEL[selected.review.verdict] ??
                        selected.review.verdict}
                    </span>
                    <span className="text-xs capitalize text-muted">
                      · {selected.review.risk} risk
                    </span>
                  </div>
                  {selected.review.summary && (
                    <p className="mt-2 text-sm leading-6 text-muted">
                      {selected.review.summary}
                    </p>
                  )}
                  {selected.review.comment_url && (
                    <a
                      href={selected.review.comment_url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-3 inline-flex items-center gap-1 text-xs text-foreground underline underline-offset-2"
                    >
                      View review comment on GitHub
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                </div>
              ) : (
                <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-sm text-amber-200/90">
                  Not yet reviewed. Open or update this PR to trigger the
                  webhook blast-radius reasoner, or call{" "}
                  <code className="rounded bg-black/30 px-1 py-0.5 text-xs">
                    POST /reason
                  </code>{" "}
                  from the API docs.
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

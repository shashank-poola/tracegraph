"use client";

import Link from "next/link";
import { Check, Globe, Lock, Plus, Star, GitFork } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Repo } from "@/lib/api";

const LANGUAGE_COLORS: Record<string, string> = {
  Python: "bg-yellow-400",
  TypeScript: "bg-blue-400",
  JavaScript: "bg-yellow-300",
  Go: "bg-cyan-400",
  Rust: "bg-orange-500",
  Java: "bg-red-400",
};

export function RepoCard({
  repo,
  onToggleTrack,
  pending,
}: {
  repo: Repo;
  onToggleTrack: (repo: Repo) => void;
  pending: boolean;
}) {
  return (
    <div className="group relative flex flex-col gap-3 rounded-xl border border-border p-5 transition-colors hover:border-zinc-600">
      <Link
        href={`/dashboard/${repo.full_name}`}
        className="absolute inset-0"
        aria-label={`Open ${repo.full_name}`}
      />
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="font-heading text-sm text-foreground">
            {repo.name}
          </span>
          <span className="flex items-center gap-1 rounded-full border border-border px-2 py-0.5 text-[11px] text-muted">
            {repo.private ? (
              <Lock className="h-3 w-3" />
            ) : (
              <Globe className="h-3 w-3" />
            )}
            {repo.private ? "Private" : "Public"}
          </span>
        </div>

        <button
          type="button"
          disabled={pending}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onToggleTrack(repo);
          }}
          className={cn(
            "relative z-10 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border transition-colors disabled:opacity-50",
            repo.tracked
              ? "border-foreground bg-foreground text-background"
              : "border-border text-muted hover:border-zinc-500 hover:text-foreground",
          )}
          title={repo.tracked ? "Untrack" : "Track this repo"}
        >
          {repo.tracked ? (
            <Check className="h-3.5 w-3.5" />
          ) : (
            <Plus className="h-3.5 w-3.5" />
          )}
        </button>
      </div>

      <p className="line-clamp-2 text-xs leading-5 text-muted">
        {repo.description || "No description"}
      </p>

      <div className="flex items-center gap-4 text-xs text-muted">
        {repo.language && (
          <span className="flex items-center gap-1.5">
            <span
              className={cn(
                "h-2 w-2 rounded-full",
                LANGUAGE_COLORS[repo.language] ?? "bg-zinc-500",
              )}
            />
            {repo.language}
          </span>
        )}
        <span className="flex items-center gap-1">
          <Star className="h-3 w-3" />
          {repo.stargazers_count}
        </span>
        <span className="flex items-center gap-1">
          <GitFork className="h-3 w-3" />
          {repo.forks_count}
        </span>
      </div>
    </div>
  );
}

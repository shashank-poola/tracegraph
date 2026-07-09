import Link from "next/link";
import {
  ArrowLeft,
  ExternalLink,
  GitCommitHorizontal,
  GitFork,
  GitPullRequest,
  Globe,
  Lock,
  Star,
} from "lucide-react";
import type { RepoDetail } from "@/lib/api";

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof GitPullRequest;
  label: string;
  value: number;
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-border px-5 py-4">
      <Icon className="h-4 w-4 text-muted" strokeWidth={1.5} />
      <div className="flex flex-col">
        <span className="text-xs text-muted">{label}</span>
        <span className="font-heading text-lg text-foreground">{value}</span>
      </div>
    </div>
  );
}

export function RepoHeader({ repo }: { repo: RepoDetail }) {
  return (
    <div className="flex flex-col gap-6">
      <Link
        href="/dashboard"
        className="flex items-center gap-1.5 text-sm text-muted transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        All repositories
      </Link>

      <div>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="font-heading text-2xl tracking-tight text-foreground">
            {repo.full_name}
          </h1>
          <span className="flex items-center gap-1 rounded-full border border-border px-2.5 py-0.5 text-xs text-muted">
            {repo.private ? (
              <Lock className="h-3 w-3" />
            ) : (
              <Globe className="h-3 w-3" />
            )}
            {repo.private ? "Private" : "Public"}
          </span>
        </div>

        <p className="mt-2 text-sm text-muted">
          {repo.description || "No description"}
        </p>

        <div className="mt-3 flex items-center gap-4 text-sm text-muted">
          {repo.language && <span>{repo.language}</span>}
          <span className="flex items-center gap-1">
            <Star className="h-3.5 w-3.5" /> {repo.stargazers_count}
          </span>
          <span className="flex items-center gap-1">
            <GitFork className="h-3.5 w-3.5" /> {repo.forks_count}
          </span>
          <a
            href={repo.html_url}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1 transition-colors hover:text-foreground"
          >
            Open on GitHub <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <StatCard
          icon={GitPullRequest}
          label="Pull requests"
          value={repo.pull_request_count}
        />
        <StatCard
          icon={GitCommitHorizontal}
          label="Commits"
          value={repo.commit_count}
        />
      </div>
    </div>
  );
}

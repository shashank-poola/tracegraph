"use client";

import { use, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useCurrentUser } from "@/hooks/use-current-user";
import { Topbar } from "@/components/dashboard/topbar";
import { RepoHeader } from "@/components/dashboard/repo-header";
import { AnalysisTools } from "@/components/dashboard/analysis-tools";
import { LiveCrawl } from "@/components/dashboard/live-crawl";
import { PullRequestsPanel } from "@/components/dashboard/pull-requests-panel";
import { CONTAINER } from "@/lib/layout";
import { type RepoDetail, getRepoDetail } from "@/lib/api";

export default function RepoDetailPage({
  params,
}: {
  params: Promise<{ owner: string; repo: string }>;
}) {
  const { owner, repo: repoName } = use(params);
  const fullName = `${owner}/${repoName}`;

  const router = useRouter();
  const { user, loading: userLoading } = useCurrentUser();
  const [repo, setRepo] = useState<RepoDetail | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    getRepoDetail(fullName)
      .then(setRepo)
      .catch((err) => setError(err.message ?? "Failed to load repository"));
  }, [fullName]);

  useEffect(() => {
    if (!userLoading && !user) {
      router.replace("/login");
    }
  }, [userLoading, user, router]);

  useEffect(() => {
    if (user) load();
  }, [user, load]);

  if (userLoading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-foreground" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col">
      <Topbar user={user} />

      <main className={`${CONTAINER} flex flex-1 flex-col gap-10 py-10`}>
        {error && (
          <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {error}
          </p>
        )}

        {!repo && !error && (
          <div className="h-48 animate-pulse rounded-xl border border-border" />
        )}

        {repo && (
          <>
            <RepoHeader repo={repo} />

            <section>
              <h2 className="font-heading text-lg text-foreground">
                Analysis tools
              </h2>
              <p className="mt-1 text-sm text-muted">
                Build the knowledge graph, ingest the codebase docs, and crawl
                the live app — all inline, right here on the repository.
              </p>
              <div className="mt-4 flex flex-col gap-4">
                <AnalysisTools repo={repo} onAnalyzed={load} />
                <LiveCrawl fullName={repo.full_name} onCrawled={load} />
              </div>
            </section>

            <PullRequestsPanel fullName={repo.full_name} />
          </>
        )}
      </main>
    </div>
  );
}

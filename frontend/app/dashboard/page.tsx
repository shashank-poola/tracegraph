"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import { useCurrentUser } from "@/hooks/use-current-user";
import { Topbar } from "@/components/dashboard/topbar";
import { ProfileCard } from "@/components/dashboard/profile-card";
import { RepoCard } from "@/components/dashboard/repo-card";
import { CONTAINER } from "@/lib/layout";
import {
  type GithubProfile,
  type Repo,
  getProfile,
  listRepos,
  trackRepo,
  untrackRepo,
} from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const { user, loading: userLoading } = useCurrentUser();

  const [profile, setProfile] = useState<GithubProfile | null>(null);
  const [repos, setRepos] = useState<Repo[] | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [pendingRepo, setPendingRepo] = useState<string | null>(null);

  useEffect(() => {
    if (!userLoading && !user) {
      router.replace("/login");
    }
  }, [userLoading, user, router]);

  useEffect(() => {
    if (!user) return;
    Promise.all([getProfile(), listRepos()])
      .then(([p, r]) => {
        setProfile(p);
        setRepos(r.repos);
      })
      .catch((err) => setError(err.message ?? "Failed to load repositories"));
  }, [user]);

  async function handleToggleTrack(repo: Repo) {
    if (!repos) return;
    setPendingRepo(repo.full_name);
    try {
      if (repo.tracked) {
        await untrackRepo(repo.full_name);
      } else {
        await trackRepo(repo.full_name);
      }
      setRepos((prev) =>
        (prev ?? []).map((r) =>
          r.full_name === repo.full_name ? { ...r, tracked: !r.tracked } : r,
        ),
      );
      setProfile((prev) =>
        prev
          ? {
              ...prev,
              tracked_count: prev.tracked_count + (repo.tracked ? -1 : 1),
            }
          : prev,
      );
    } catch {
      // no-op — leave state unchanged on failure
    } finally {
      setPendingRepo(null);
    }
  }

  const filtered = useMemo(() => {
    if (!repos) return [];
    const q = query.trim().toLowerCase();
    if (!q) return repos;
    return repos.filter(
      (r) =>
        r.name.toLowerCase().includes(q) ||
        r.description.toLowerCase().includes(q),
    );
  }, [repos, query]);

  const tracked = filtered.filter((r) => r.tracked);
  const untracked = filtered.filter((r) => !r.tracked);

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

      <main className={`${CONTAINER} flex flex-1 flex-col gap-8 py-10 md:flex-row`}>
        <aside className="w-full shrink-0 md:w-72">
          {profile ? (
            <ProfileCard profile={profile} />
          ) : (
            <div className="h-64 animate-pulse rounded-xl border border-border" />
          )}
        </aside>

        <section className="flex-1">
          <h1 className="font-heading text-2xl tracking-tight text-foreground">
            Repositories
          </h1>
          <p className="mt-1 text-sm text-muted">
            {repos ? `${repos.length} repositories` : "Loading…"} · click a
            card to analyze, or track the ones you want TraceGraph to watch.
          </p>

          <div className="relative mt-6 max-w-sm">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search repositories…"
              className="w-full rounded-lg border border-border bg-transparent py-2 pl-9 pr-3 text-sm text-foreground placeholder:text-muted focus:border-zinc-500 focus:outline-none"
            />
          </div>

          {error && (
            <p className="mt-6 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
              {error}
            </p>
          )}

          {!repos && !error && (
            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <div
                  key={i}
                  className="h-32 animate-pulse rounded-xl border border-border"
                />
              ))}
            </div>
          )}

          {tracked.length > 0 && (
            <div className="mt-8">
              <h3 className="text-sm text-muted">Tracked ({tracked.length})</h3>
              <div className="mt-3 grid gap-4 sm:grid-cols-2">
                {tracked.map((repo) => (
                  <RepoCard
                    key={repo.full_name}
                    repo={repo}
                    onToggleTrack={handleToggleTrack}
                    pending={pendingRepo === repo.full_name}
                  />
                ))}
              </div>
            </div>
          )}

          {untracked.length > 0 && (
            <div className="mt-8">
              {tracked.length > 0 && (
                <h3 className="text-sm text-muted">All repositories</h3>
              )}
              <div className="mt-3 grid gap-4 sm:grid-cols-2">
                {untracked.map((repo) => (
                  <RepoCard
                    key={repo.full_name}
                    repo={repo}
                    onToggleTrack={handleToggleTrack}
                    pending={pendingRepo === repo.full_name}
                  />
                ))}
              </div>
            </div>
          )}

          {repos && filtered.length === 0 && (
            <p className="mt-10 text-center text-sm text-muted">
              No repositories match &ldquo;{query}&rdquo;.
            </p>
          )}
        </section>
      </main>
    </div>
  );
}

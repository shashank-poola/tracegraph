"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronRight, Compass, Lock, Plus, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { PipelineProgress } from "@/components/dashboard/pipeline-progress";
import { CrawlHeroScreenshot, CrawlLiveFeed } from "@/components/dashboard/crawl-live-feed";
import { CrawlModal } from "@/components/dashboard/crawl-modal";
import {
  type CrawlResult,
  type JobStatus,
  type RepoDetail,
  getRepoCrawl,
  pollJob,
  startCrawl,
} from "@/lib/api";

type CrawlRoute = { path: string; authenticated: boolean };

function isAbortError(err: unknown): boolean {
  return err instanceof DOMException && err.name === "AbortError";
}

export function LiveCrawl({
  repo,
  onCrawled,
}: {
  repo: RepoDetail;
  onCrawled: () => void;
}) {
  const [baseUrl, setBaseUrl] = useState("");
  const [routes, setRoutes] = useState<CrawlRoute[]>([{ path: "/", authenticated: false }]);
  const [job, setJob] = useState<JobStatus | null>(null);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<CrawlResult | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const pollAbort = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => pollAbort.current?.abort();
  }, []);

  useEffect(() => {
    if (repo.status.has_crawl) {
      getRepoCrawl(repo.full_name)
        .then(setResult)
        .catch(() => setResult(null));
    } else {
      setResult(null);
    }
  }, [repo.full_name, repo.status.has_crawl]);

  async function openDetails() {
    if (result) {
      setModalOpen(true);
      return;
    }
    try {
      setResult(await getRepoCrawl(repo.full_name));
      setModalOpen(true);
    } catch {
      // Cached crawl unavailable — user can re-run.
    }
  }

  function updateRoute(index: number, patch: Partial<CrawlRoute>) {
    setRoutes((prev) => prev.map((r, i) => (i === index ? { ...r, ...patch } : r)));
  }

  function removeRoute(index: number) {
    setRoutes((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleCrawl() {
    if (!baseUrl.trim()) return;
    setRunning(true);
    setJob(null);
    pollAbort.current?.abort();
    const controller = new AbortController();
    pollAbort.current = controller;
    try {
      const { job_id } = await startCrawl({
        base_url: baseUrl.trim(),
        full_name: repo.full_name,
        routes: routes.filter((r) => r.path.trim()),
      });
      const final = await pollJob(job_id, setJob, { signal: controller.signal });
      if (final.state === "done") {
        if (final.crawl_result) {
          setResult(final.crawl_result);
          if (final.crawl_result.screen_count > 0) {
            setModalOpen(true);
          }
        }
        onCrawled();
      }
    } catch (err) {
      if (isAbortError(err)) return;
      setJob({
        job_id: "",
        state: "error",
        progress: 1,
        message: "",
        error: err instanceof Error ? err.message : "Failed to start crawl",
      });
    } finally {
      setRunning(false);
    }
  }

  const isRunning = job && job.state !== "done" && job.state !== "error";
  const liveScreens = job?.crawl_result?.screens ?? [];
  const heroScreen =
    result?.screens.find((screen) => screen.screenshot_url) ?? result?.screens[0];

  return (
    <div className="rounded-xl border border-border p-5">
      <div className="flex items-center gap-2">
        <Compass className="h-4 w-4 text-foreground" strokeWidth={1.5} />
        <h3 className="font-heading text-sm text-foreground">
          Live application crawl
        </h3>
      </div>
      <p className="mt-1 text-xs leading-5 text-muted">
        List routes to capture. For Streamlit apps with sidebar navigation, only add
        <code className="mx-1 rounded bg-white/5 px-1">/</code> — TraceGraph will
        auto-capture each sidebar view (Home, Add expense, etc.).
      </p>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-2">
          <input
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="Base URL — https://app.example.com"
            className="rounded-lg border border-border bg-transparent px-3 py-2 text-xs text-foreground placeholder:text-muted focus:border-zinc-500 focus:outline-none"
          />

          {routes.map((route, i) => (
            <div key={i} className="flex items-center gap-2">
              <input
                value={route.path}
                onChange={(e) => updateRoute(i, { path: e.target.value })}
                placeholder="/"
                className="flex-1 rounded-lg border border-border bg-transparent px-3 py-2 text-xs text-foreground placeholder:text-muted focus:border-zinc-500 focus:outline-none"
              />
              <button
                type="button"
                onClick={() => updateRoute(i, { authenticated: !route.authenticated })}
                className={cn(
                  "flex items-center gap-1 whitespace-nowrap rounded-full border px-2.5 py-1.5 text-[11px]",
                  route.authenticated
                    ? "border-zinc-500 text-foreground"
                    : "border-border text-muted",
                )}
              >
                {route.authenticated && <Lock className="h-3 w-3" />}
                {route.authenticated ? "Authenticated" : "Public"}
              </button>
              <button
                type="button"
                onClick={() => removeRoute(i)}
                className="text-muted transition-colors hover:text-red-400"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}

          <button
            type="button"
            onClick={() => setRoutes((prev) => [...prev, { path: "", authenticated: false }])}
            className="flex items-center gap-1 self-start text-xs text-muted transition-colors hover:text-foreground"
          >
            <Plus className="h-3.5 w-3.5" /> Add route
          </button>

          <Button
            size="sm"
            className="mt-1"
            disabled={running || !baseUrl.trim()}
            onClick={handleCrawl}
          >
            <Compass className="h-3.5 w-3.5" />
            Crawl {routes.filter((r) => r.path.trim()).length || 0} route
            {routes.filter((r) => r.path.trim()).length === 1 ? "" : "s"}
          </Button>

          {job && <PipelineProgress status={job} kind="crawl" />}
        </div>

        <div className="flex flex-col rounded-lg border border-border p-4">
          {isRunning ? (
            <>
              <p className="mb-3 flex items-center gap-2 text-[11px] font-medium uppercase tracking-wider text-muted">
                Crawled {liveScreens.length}{" "}
                {liveScreens.length === 1 ? "screen" : "screens"}
              </p>
              <CrawlLiveFeed screens={liveScreens} statusMessage={job.message} />
            </>
          ) : result?.capture_note && result.screen_count === 0 ? (
            <div className="flex flex-1 flex-col justify-center gap-2 rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-sm text-amber-200/90">
              <p className="font-medium text-amber-100">Crawl could not capture any screens</p>
              <p className="text-xs leading-5">{result.capture_note}</p>
            </div>
          ) : result ? (
            <button
              type="button"
              onClick={openDetails}
              className="flex flex-1 flex-col gap-3 text-left transition-opacity hover:opacity-95"
            >
              <div className="flex items-center gap-2 text-[11px] font-medium uppercase tracking-wider text-muted">
                <Compass className="h-3.5 w-3.5" strokeWidth={1.5} />
                Crawled {result.screen_count}{" "}
                {result.screen_count === 1 ? "screen" : "screens"}
              </div>

              <CrawlHeroScreenshot
                src={heroScreen?.screenshot_url}
                title={heroScreen?.label || heroScreen?.title || "Captured screen"}
                subtitle={
                  heroScreen?.interactive_count != null
                    ? `${heroScreen.interactive_count} controls`
                    : result.base_url
                }
              />

              <div className="flex items-center justify-between gap-3 rounded-lg border border-border px-3 py-2.5">
                <div className="flex flex-col gap-0.5">
                  <span className="text-xs text-foreground">
                    {result.transitions.length.toLocaleString()} transitions
                  </span>
                  <span className="text-[11px] text-muted">Saved to DB</span>
                </div>
                <span className="flex shrink-0 items-center gap-0.5 text-xs text-muted">
                  View screen graph & browser responses{" "}
                  <ChevronRight className="h-3.5 w-3.5" />
                </span>
              </div>
            </button>
          ) : (
            <p className="flex h-full items-center justify-center text-center text-xs text-muted">
              Crawl results appear here.
            </p>
          )}
        </div>
      </div>

      <CrawlModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        fullName={repo.full_name}
        result={result}
      />
    </div>
  );
}

"use client";

import { useState } from "react";
import { Compass, Lock, Plus, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { PipelineProgress } from "@/components/dashboard/pipeline-progress";
import { type JobStatus, pollJob, startCrawl } from "@/lib/api";

type Route = { path: string; authenticated: boolean };
type Screen = { url: string; title?: string; label?: string };

export function LiveCrawl({
  fullName,
  onCrawled,
}: {
  fullName: string;
  onCrawled: () => void;
}) {
  const [baseUrl, setBaseUrl] = useState("");
  const [routes, setRoutes] = useState<Route[]>([{ path: "/", authenticated: false }]);
  const [job, setJob] = useState<JobStatus | null>(null);
  const [running, setRunning] = useState(false);
  const [screens, setScreens] = useState<Screen[] | null>(null);

  function updateRoute(index: number, patch: Partial<Route>) {
    setRoutes((prev) => prev.map((r, i) => (i === index ? { ...r, ...patch } : r)));
  }

  function removeRoute(index: number) {
    setRoutes((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleCrawl() {
    if (!baseUrl.trim()) return;
    setRunning(true);
    setJob(null);
    setScreens(null);
    try {
      const { job_id } = await startCrawl({
        base_url: baseUrl.trim(),
        full_name: fullName,
        routes: routes.filter((r) => r.path.trim()),
        crawl_mode: "hybrid",
      });
      const final = await pollJob(job_id, setJob);
      if (final.state === "done") {
        const result = final.crawl_result as { screens?: Screen[] } | undefined;
        setScreens(result?.screens ?? []);
        onCrawled();
      }
    } catch (err) {
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

  return (
    <div className="rounded-xl border border-border p-5">
      <div className="flex items-center gap-2">
        <Compass className="h-4 w-4 text-foreground" strokeWidth={1.5} />
        <h3 className="font-heading text-sm text-foreground">
          Live application crawl
        </h3>
      </div>
      <p className="mt-1 text-xs leading-5 text-muted">
        List the routes to capture and mark each public or authenticated. The
        browser visits each, captures DOM + screenshot, and maps how the
        screens connect.
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

        <div className="rounded-lg border border-border p-4">
          {!screens && (
            <p className="flex h-full items-center justify-center text-center text-xs text-muted">
              Crawl results appear here.
            </p>
          )}
          {screens && screens.length === 0 && (
            <p className="text-center text-xs text-muted">
              No screens captured.
            </p>
          )}
          {screens && screens.length > 0 && (
            <ul className="flex flex-col gap-2">
              {screens.slice(0, 8).map((s, i) => (
                <li key={i} className="text-xs text-foreground">
                  <span className="text-muted">{i + 1}.</span>{" "}
                  {s.label || s.title || s.url}
                </li>
              ))}
              {screens.length > 8 && (
                <li className="text-xs text-muted">
                  +{screens.length - 8} more screens
                </li>
              )}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

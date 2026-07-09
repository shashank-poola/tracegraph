"use client";

import { useState } from "react";
import { Database, ExternalLink, FileText, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PipelineProgress } from "@/components/dashboard/pipeline-progress";
import {
  type JobStatus,
  type RepoDetail,
  pollJob,
  startAnalyze,
  startIngest,
} from "@/lib/api";

export function AnalysisTools({
  repo,
  onAnalyzed,
}: {
  repo: RepoDetail;
  onAnalyzed: () => void;
}) {
  const [graphJob, setGraphJob] = useState<JobStatus | null>(null);
  const [graphUrl, setGraphUrl] = useState<string | null>(null);
  const [graphRunning, setGraphRunning] = useState(false);

  const [ingestJob, setIngestJob] = useState<JobStatus | null>(null);
  const [ingestRunning, setIngestRunning] = useState(false);
  const [reqCount, setReqCount] = useState<number | null>(null);

  async function handleGenerateGraph() {
    setGraphRunning(true);
    setGraphJob(null);
    try {
      const [owner, name] = repo.full_name.split("/");
      const { job_id } = await startAnalyze({
        full_name: repo.full_name,
        owner,
        repo: name,
        ref: repo.default_branch,
        build_graph: true,
      });
      const final = await pollJob(job_id, setGraphJob);
      if (final.state === "done") {
        const tree = final.result as { graph?: { console_url?: string } } | undefined;
        setGraphUrl(tree?.graph?.console_url ?? null);
        onAnalyzed();
      }
    } catch (err) {
      setGraphJob({
        job_id: "",
        state: "error",
        progress: 1,
        message: "",
        error: err instanceof Error ? err.message : "Failed to start",
      });
    } finally {
      setGraphRunning(false);
    }
  }

  async function handleIngest() {
    setIngestRunning(true);
    setIngestJob(null);
    try {
      const { job_id } = await startIngest({
        source: repo.full_name,
        source_type: "github_repo",
        full_name: repo.full_name,
      });
      const final = await pollJob(job_id, setIngestJob);
      if (final.state === "done") {
        const result = final.ingest_result as { requirement_count?: number } | undefined;
        setReqCount(result?.requirement_count ?? null);
        onAnalyzed();
      }
    } catch (err) {
      setIngestJob({
        job_id: "",
        state: "error",
        progress: 1,
        message: "",
        error: err instanceof Error ? err.message : "Failed to start",
      });
    } finally {
      setIngestRunning(false);
    }
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <div className="flex flex-col gap-3 rounded-xl border border-border p-5">
        <div className="flex items-center gap-2">
          <Database className="h-4 w-4 text-foreground" strokeWidth={1.5} />
          <h3 className="font-heading text-sm text-foreground">
            Knowledge graph
          </h3>
        </div>
        <p className="text-xs leading-5 text-muted">
          Parse the codebase into an AST and write it straight into the Neo4j
          knowledge graph.
        </p>
        <Button
          size="sm"
          className="mt-1"
          disabled={graphRunning}
          onClick={handleGenerateGraph}
        >
          <Sparkles className="h-3.5 w-3.5" />
          {repo.status.has_graph ? "Regenerate knowledge graph" : "Generate knowledge graph"}
        </Button>
        {graphJob && <PipelineProgress status={graphJob} kind="graph" />}
        {graphUrl && (
          <a
            href={graphUrl}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1 text-xs text-foreground underline underline-offset-2"
          >
            Open in Neo4j console <ExternalLink className="h-3 w-3" />
          </a>
        )}
      </div>

      <div className="flex flex-col gap-3 rounded-xl border border-border p-5">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-foreground" strokeWidth={1.5} />
          <h3 className="font-heading text-sm text-foreground">
            Product requirements
          </h3>
        </div>
        <p className="text-xs leading-5 text-muted">
          Pulls every .md / .vdk doc straight from the codebase and parses
          them into testable, persisted requirements.
        </p>
        <Button
          size="sm"
          variant="outline"
          disabled={ingestRunning}
          onClick={handleIngest}
        >
          Ingest codebase docs
        </Button>
        {ingestJob && <PipelineProgress status={ingestJob} kind="ingest" />}
        {reqCount !== null && (
          <p className="text-xs text-muted">
            Extracted <span className="text-foreground">{reqCount}</span>{" "}
            requirements.
          </p>
        )}
      </div>
    </div>
  );
}

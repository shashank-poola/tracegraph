"use client";

import { useEffect, useState } from "react";
import { ChevronRight, Database, FileText, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PipelineProgress } from "@/components/dashboard/pipeline-progress";
import { GraphModal } from "@/components/dashboard/graph-modal";
import { IngestModal } from "@/components/dashboard/ingest-modal";
import {
  type IngestResult,
  type JobStatus,
  type RepoDetail,
  type RepoTree,
  getRepoIngest,
  getRepoTree,
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
  const [graphRunning, setGraphRunning] = useState(false);
  const [graphTree, setGraphTree] = useState<RepoTree | null>(null);
  const [graphOpen, setGraphOpen] = useState(false);

  const [ingestJob, setIngestJob] = useState<JobStatus | null>(null);
  const [ingestRunning, setIngestRunning] = useState(false);
  const [ingestResult, setIngestResult] = useState<IngestResult | null>(null);
  const [ingestOpen, setIngestOpen] = useState(false);

  useEffect(() => {
    if (repo.status.has_graph) {
      getRepoTree(repo.full_name)
        .then(setGraphTree)
        .catch(() => setGraphTree(null));
    } else {
      setGraphTree(null);
    }
  }, [repo.full_name, repo.status.has_graph]);

  useEffect(() => {
    if (repo.status.has_requirements) {
      getRepoIngest(repo.full_name)
        .then(setIngestResult)
        .catch(() => setIngestResult(null));
    } else {
      setIngestResult(null);
    }
  }, [repo.full_name, repo.status.has_requirements]);

  async function openGraphDetails() {
    if (graphTree) {
      setGraphOpen(true);
      return;
    }
    try {
      const tree = await getRepoTree(repo.full_name);
      setGraphTree(tree);
      setGraphOpen(true);
    } catch {
      // no-op
    }
  }

  async function openIngestDetails() {
    if (ingestResult) {
      setIngestOpen(true);
      return;
    }
    try {
      const result = await getRepoIngest(repo.full_name);
      setIngestResult(result);
      setIngestOpen(true);
    } catch {
      // no-op
    }
  }

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
        const tree = (final.result ?? null) as RepoTree | null;
        if (tree) {
          setGraphTree(tree);
          setGraphOpen(true);
        }
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
        const result = (final.ingest_result ?? null) as IngestResult | null;
        if (result) {
          setIngestResult(result);
          setIngestOpen(true);
        }
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

  const graphNodes = graphTree?.graph?.nodes_written;
  const graphRels = graphTree?.graph?.relationships_written;

  return (
    <>
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
            {repo.status.has_graph
              ? "Regenerate knowledge graph"
              : "Generate knowledge graph"}
          </Button>
          {graphJob && <PipelineProgress status={graphJob} kind="graph" />}
          {repo.status.has_graph && graphNodes != null && (
            <button
              type="button"
              onClick={openGraphDetails}
              className="flex items-center justify-between rounded-lg border border-border px-3 py-2.5 text-left transition-colors hover:bg-white/[0.03]"
            >
              <div className="flex flex-col gap-0.5">
                <span className="text-xs text-foreground">
                  {graphNodes.toLocaleString()} nodes ·{" "}
                  {graphRels?.toLocaleString() ?? 0} relationships
                </span>
                <span className="text-[11px] text-muted">
                  Persisted in Neo4j
                </span>
              </div>
              <span className="flex items-center gap-0.5 text-xs text-muted">
                View details <ChevronRight className="h-3.5 w-3.5" />
              </span>
            </button>
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
            {repo.status.has_requirements
              ? "Re-ingest codebase docs"
              : "Ingest codebase docs"}
          </Button>
          {ingestJob && <PipelineProgress status={ingestJob} kind="ingest" />}
          {repo.status.has_requirements && ingestResult && (
            <button
              type="button"
              onClick={openIngestDetails}
              className="flex items-center justify-between rounded-lg border border-border px-3 py-2.5 text-left transition-colors hover:bg-white/[0.03]"
            >
              <div className="flex flex-col gap-0.5">
                <span className="text-xs text-foreground">
                  {ingestResult.requirement_count} requirements ·{" "}
                  {ingestResult.files?.length ?? 0} docs
                </span>
                <span className="text-[11px] text-muted">
                  Persisted in database
                </span>
              </div>
              <span className="flex items-center gap-0.5 text-xs text-muted">
                View details <ChevronRight className="h-3.5 w-3.5" />
              </span>
            </button>
          )}
        </div>
      </div>

      <GraphModal
        open={graphOpen}
        onClose={() => setGraphOpen(false)}
        fullName={repo.full_name}
        tree={graphTree}
      />
      <IngestModal
        open={ingestOpen}
        onClose={() => setIngestOpen(false)}
        fullName={repo.full_name}
        result={ingestResult}
      />
    </>
  );
}

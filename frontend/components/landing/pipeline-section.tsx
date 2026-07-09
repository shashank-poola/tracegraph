import { Compass, Database, FileText, Sparkles } from "lucide-react";
import { CONTAINER } from "@/lib/layout";

const STEPS = [
  {
    icon: Sparkles,
    color: "text-violet-400",
    bg: "bg-violet-500/10",
    title: "Analyze",
    description: "Fetch repo, parse Python AST, describe every file with LLM.",
  },
  {
    icon: Database,
    color: "text-cyan-400",
    bg: "bg-cyan-500/10",
    title: "Graph",
    description: "Mirror symbols, deps, and calls into Neo4j as a deep graph.",
  },
  {
    icon: FileText,
    color: "text-amber-400",
    bg: "bg-amber-500/10",
    title: "Ingest",
    description: "Pull .md docs from the repo and extract testable requirements.",
  },
  {
    icon: Compass,
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
    title: "Crawl",
    description: "Hybrid browser agent + Playwright capture of every screen.",
  },
];

export function PipelineSection() {
  return (
    <section className="py-24">
      <div className={CONTAINER}>
        <p className="text-xs uppercase tracking-widest text-emerald-400">
          Pipeline
        </p>
        <h2 className="font-heading mt-2 text-2xl tracking-tight text-foreground sm:text-3xl">
          Build the graph in four steps — right from your dashboard
        </h2>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">
          No giant payloads, no frontend cache juggling. TraceGraph owns
          persistence in SQLite and Neo4j; you click a button and watch the
          pipeline run.
        </p>
        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map(({ icon: Icon, color, bg, title, description }) => (
            <div
              key={title}
              className="flex flex-col gap-3 rounded-xl border border-border p-5"
            >
              <div
                className={`flex h-9 w-9 items-center justify-center rounded-md ${bg}`}
              >
                <Icon className={`h-4 w-4 ${color}`} strokeWidth={1.5} />
              </div>
              <h3 className="font-heading text-sm text-foreground">{title}</h3>
              <p className="text-xs leading-5 text-muted">{description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

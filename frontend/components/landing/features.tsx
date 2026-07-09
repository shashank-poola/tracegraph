import { GitBranch, Layers3, Radar } from "lucide-react";
import { CONTAINER } from "@/lib/layout";

const FEATURES = [
  {
    icon: Radar,
    color: "text-cyan-400",
    bg: "bg-cyan-500/10 border-cyan-500/20",
    title: "Crawl the live app",
    description:
      "A browser agent discovers screens and flows, then Playwright captures DOM, screenshots, and accessibility trees.",
  },
  {
    icon: Layers3,
    color: "text-violet-400",
    bg: "bg-violet-500/10 border-violet-500/20",
    title: "Ingest the PRD",
    description:
      "Requirements are extracted from your spec and linked to the UI that should implement them — including gaps.",
  },
  {
    icon: GitBranch,
    color: "text-emerald-400",
    bg: "bg-emerald-500/10 border-emerald-500/20",
    title: "Reason about the diff",
    description:
      "Every pull request is checked across all three layers and posted back as a plain-English blast-radius report.",
  },
];

export function Features() {
  return (
    <section id="layers" className="py-24">
      <div className={CONTAINER}>
        <p className="text-xs uppercase tracking-widest text-violet-400">
          Three layers
        </p>
        <h2 className="font-heading mt-2 max-w-lg text-2xl tracking-tight text-foreground sm:text-3xl">
          One graph that sees what RAG cannot
        </h2>
        <p className="mt-3 max-w-xl text-sm leading-6 text-muted">
          Unlike retrieval systems that search documents, TraceGraph models
          relationships — and absence. A requirement with no UI coverage is a
          first-class signal.
        </p>
        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {FEATURES.map(({ icon: Icon, color, bg, title, description }) => (
            <div
              key={title}
              className="flex flex-col gap-4 rounded-xl border border-border p-6 transition-colors hover:border-zinc-600"
            >
              <div
                className={`flex h-10 w-10 items-center justify-center rounded-md border ${bg}`}
              >
                <Icon className={`h-5 w-5 ${color}`} strokeWidth={1.5} />
              </div>
              <h3 className="font-heading text-lg text-foreground">{title}</h3>
              <p className="text-sm leading-6 text-muted">{description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

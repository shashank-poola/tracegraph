import { GitBranch, Layers3, Radar } from "lucide-react";

const FEATURES = [
  {
    icon: Radar,
    title: "Crawl the live app",
    description:
      "A browser agent discovers screens and flows, then Playwright captures the DOM, screenshots, and accessibility tree for every one.",
  },
  {
    icon: Layers3,
    title: "Ingest the PRD",
    description:
      "Requirements are extracted from your product spec and linked to the UI that should implement them — including the ones that aren't.",
  },
  {
    icon: GitBranch,
    title: "Reason about the diff",
    description:
      "Every pull request is checked against requirements, UI, and code in one graph, and posted back as a plain-English blast-radius report.",
  },
];

export function Features() {
  return (
    <section id="layers" className="border-t border-border/60 py-24">
      <div className="mx-auto max-w-6xl px-6">
        <h2 className="font-heading max-w-lg text-2xl tracking-tight text-foreground sm:text-3xl">
          Three layers. One graph.
        </h2>
        <div className="mt-12 grid gap-8 md:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, description }) => (
            <div
              key={title}
              className="flex flex-col gap-4 rounded-xl border border-border p-6"
            >
              <Icon className="h-6 w-6 text-foreground" strokeWidth={1.5} />
              <h3 className="font-heading text-lg text-foreground">{title}</h3>
              <p className="text-sm leading-6 text-muted">{description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

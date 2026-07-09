import { CONTAINER } from "@/lib/layout";

const LAYERS = [
  { name: "Requirements", color: "bg-violet-500", x: "12%", y: "20%" },
  { name: "DOM / UI", color: "bg-cyan-400", x: "55%", y: "15%" },
  { name: "Code AST", color: "bg-emerald-400", x: "35%", y: "55%" },
  { name: "Neo4j", color: "bg-amber-400", x: "72%", y: "48%" },
];

export function ConnectedLayers() {
  return (
    <section id="how" className="border-y border-border/40 py-24">
      <div className={`${CONTAINER} grid items-center gap-16 md:grid-cols-2`}>
        <div>
          <p className="text-xs uppercase tracking-widest text-cyan-400">
            Cross-layer linking
          </p>
          <h2 className="font-heading mt-2 text-2xl tracking-tight text-foreground sm:text-3xl">
            Connect spec, screens, and symbols in one queryable graph
          </h2>
          <p className="mt-4 text-sm leading-7 text-muted">
            TraceGraph doesn&apos;t just store artifacts — it wires requirements
            to UI elements to code functions. When a PR touches checkout logic,
            you see which flows and specs move with it.
          </p>
          <ul className="mt-8 flex flex-col gap-4">
            {[
              "Detect MISSING_UI_COVERAGE — requirements with no screen",
              "Map crawl transitions to user journeys in the PRD",
              "Resolve AST call graphs into Neo4j behaviour edges",
            ].map((item) => (
              <li key={item} className="flex gap-3 text-sm text-muted">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-cyan-400" />
                {item}
              </li>
            ))}
          </ul>
        </div>

        <div className="relative aspect-[4/3] overflow-hidden rounded-xl border border-border bg-zinc-950">
          <svg
            className="absolute inset-0 h-full w-full"
            viewBox="0 0 400 300"
            fill="none"
          >
            <line x1="80" y1="70" x2="220" y2="55" stroke="#3f3f46" strokeWidth="1" />
            <line x1="220" y1="55" x2="290" y2="150" stroke="#3f3f46" strokeWidth="1" />
            <line x1="80" y1="70" x2="150" y2="175" stroke="#3f3f46" strokeWidth="1" />
            <line x1="150" y1="175" x2="290" y2="150" stroke="#3f3f46" strokeWidth="1" />
          </svg>
          {LAYERS.map((node) => (
            <div
              key={node.name}
              className="animate-pulse-glow absolute flex items-center gap-2 rounded-md border border-border bg-black/80 px-3 py-2 text-xs text-foreground backdrop-blur"
              style={{ left: node.x, top: node.y }}
            >
              <span className={`h-2 w-2 rounded-full ${node.color}`} />
              {node.name}
            </div>
          ))}
          <p className="absolute bottom-4 left-4 text-[10px] text-muted">
            Live knowledge graph · Neo4j Aura
          </p>
        </div>
      </div>
    </section>
  );
}

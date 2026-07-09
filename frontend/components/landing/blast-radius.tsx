import Link from "next/link";
import { Button } from "@/components/ui/button";
import { CONTAINER } from "@/lib/layout";

export function BlastRadiusSection() {
  return (
    <section id="blast" className="border-y border-border/40 py-24">
      <div className={`${CONTAINER} grid items-center gap-16 md:grid-cols-2`}>
        <div className="order-2 md:order-1">
          <div className="rounded-xl border border-border bg-zinc-950 p-5 font-mono text-xs leading-6">
            <p className="text-violet-400">## TraceGraph blast-radius report</p>
            <p className="mt-2 text-foreground">
              <span className="text-emerald-400">✅ Looks good to merge</span>
              {" · risk "}
              <span className="text-amber-400">🟡 medium</span>
            </p>
            <p className="mt-3 text-muted">
              Checkout flow touched — cart screen and payment requirement at
              risk. Login requirement has no UI coverage on /settings.
            </p>
            <p className="mt-4 text-zinc-500">### UI at risk</p>
            <p className="text-muted">- Cart page · Checkout button</p>
            <p className="mt-3 text-zinc-500">### Requirements losing coverage</p>
            <p className="text-muted">- R12 Guest checkout</p>
            <p className="mt-4 text-[10px] text-zinc-600">
              Layers: ✅ Requirements · ✅ DOM/UI (8 screens) · ✅ Code
            </p>
          </div>
        </div>

        <div className="order-1 md:order-2">
          <p className="text-xs uppercase tracking-widest text-amber-400">
            Blast radius
          </p>
          <h2 className="font-heading mt-2 text-2xl tracking-tight text-foreground sm:text-3xl">
            PR reviews your QA lead can actually read
          </h2>
          <p className="mt-4 text-sm leading-7 text-muted">
            On every pull request, TraceGraph loads requirements, crawl data,
            and the code graph, reasons about the diff, and posts a structured
            comment back to GitHub — verdict, risk level, UI at risk, and
            requirements losing coverage.
          </p>
        </div>
      </div>
    </section>
  );
}

export function CtaSection() {
  return (
    <section id="cta" className="py-24">
      <div className={`${CONTAINER} text-center`}>
        <h2 className="font-heading text-2xl tracking-tight text-foreground sm:text-3xl">
          Stop guessing what your next merge breaks
        </h2>
        <p className="mx-auto mt-3 max-w-md text-sm text-muted">
          Connect GitHub, pick a repo, and build your first knowledge graph in
          minutes.
        </p>
        <Link href="/login" className="mt-8 inline-block">
          <Button size="lg">Get started free</Button>
        </Link>
      </div>
    </section>
  );
}

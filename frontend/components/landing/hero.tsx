import Image from "next/image";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { CONTAINER } from "@/lib/layout";

export function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div
        className={`${CONTAINER} grid items-center gap-12 pb-20 pt-8 md:grid-cols-2 md:pb-28 md:pt-12`}
      >
        <div className="flex flex-col gap-6">
          <span className="w-fit rounded-md border border-violet-500/30 bg-violet-500/10 px-3 py-1 text-xs text-violet-300">
            Requirements · UI · Code
          </span>
          <h1 className="font-heading text-4xl leading-[1.08] tracking-tight text-foreground sm:text-5xl lg:text-[3.25rem]">
            Every PR has a blast radius.
            <br />
            <span className="text-zinc-400">Trace it before you merge.</span>
          </h1>
          <p className="max-w-md text-base leading-7 text-muted">
            TraceGraph connects your product spec, live UI, and codebase into one
            knowledge graph — then tells your QA lead exactly what a pull request
            puts at risk.
          </p>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Link href="/login">
              <Button size="lg" className="w-full sm:w-auto">
                Get started
              </Button>
            </Link>
            <a href="#how">
              <Button variant="outline" size="lg" className="w-full sm:w-auto">
                See how it works
              </Button>
            </a>
          </div>
        </div>

        <div className="relative aspect-square w-full overflow-hidden rounded-xl">
          <Image
            src="/landing/landing.jpg"
            alt="TraceGraph knowledge graph"
            fill
            priority
            className="object-cover animate-float"
          />
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-tr from-violet-500/10 via-transparent to-cyan-500/10" />
        </div>
      </div>
    </section>
  );
}

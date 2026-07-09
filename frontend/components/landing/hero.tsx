import Image from "next/image";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="mx-auto grid max-w-6xl items-center gap-12 px-6 pb-24 pt-12 md:grid-cols-2 md:pb-32 md:pt-16">
        <div className="flex flex-col gap-6">
          <span className="w-fit rounded-full border border-border px-3 py-1 text-xs text-muted">
            Requirements · UI · Code
          </span>
          <h1 className="font-heading text-4xl leading-[1.1] tracking-tight text-foreground sm:text-5xl">
            See what a PR breaks
            <br />
            before it ships.
          </h1>
          <p className="max-w-md text-base leading-7 text-muted">
            TraceGraph crawls your live app, ingests your PRD, and maps your
            codebase into one knowledge graph — then reasons about the blast
            radius of every pull request.
          </p>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Link href="/login">
              <Button size="lg" className="w-full sm:w-auto">
                Get started
              </Button>
            </Link>
            <a href="#how">
              <Button variant="outline" size="lg" className="w-full sm:w-auto">
                How it works
              </Button>
            </a>
          </div>
        </div>

        <div className="relative aspect-square w-full overflow-hidden rounded-2xl">
          <Image
            src="/landing/landing.jpg"
            alt="TraceGraph knowledge graph"
            fill
            priority
            className="object-cover"
          />
        </div>
      </div>
    </section>
  );
}

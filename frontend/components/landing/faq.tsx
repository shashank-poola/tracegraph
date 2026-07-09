"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { CONTAINER } from "@/lib/layout";

const FAQS = [
  {
    q: "What is TraceGraph?",
    a: "TraceGraph is a knowledge-graph agent for pull request blast radius. It crawls your live web app, ingests your product requirements, maps your Python codebase into an AST, and connects all three layers in Neo4j — so you can reason about what a PR actually breaks before it merges.",
  },
  {
    q: "How is this different from RAG or a chatbot over docs?",
    a: "RAG retrieves similar text chunks. TraceGraph builds a structured graph with explicit edges between requirements, UI screens, and code symbols. It also models absence — for example, a requirement with no matching UI screen is a first-class signal, not a retrieval miss.",
  },
  {
    q: "What are the three layers?",
    a: "Requirements (from .md / .vdk docs in your repo), DOM/UI (from a hybrid crawl of your live app), and Code (from AST parsing + LLM descriptions of each file). /graph/connect links them in Neo4j so blast-radius reasoning can traverse all three.",
  },
  {
    q: "How does PR blast-radius review work?",
    a: "When you trigger /reason or a GitHub webhook fires on a pull request, TraceGraph loads the three layers from SQLite, fetches the PR diff via the GitHub App, and runs multi-stage LLM reasoning. The result is posted as a structured comment on the PR — verdict, risk level, UI at risk, flows affected, and requirements losing coverage.",
  },
  {
    q: "What is hybrid crawl mode?",
    a: "By default, a browser-use agent autonomously discovers screens and user flows on your app. Then Playwright visits each discovered URL to capture DOM, screenshots, accessibility trees, and transitions. You can also use playwright-only (explicit routes) or agent-only modes.",
  },
  {
    q: "Where is data stored?",
    a: "Neo4j Aura holds the knowledge graph (code symbols, screens, requirements, cross-layer edges). SQLite on the backend stores jobs, auth sessions, the three artifact layers per user/repo, and persisted PR review verdicts. The frontend does not need to resend giant payloads on every request.",
  },
];

export function FaqSection() {
  const [open, setOpen] = useState<number | null>(0);

  return (
    <section id="faq" className="py-24">
      <div className={CONTAINER}>
        <div className="grid items-start gap-12 lg:grid-cols-2 lg:gap-16">
          <div className="lg:sticky lg:top-24">
            <p className="faq-fade-in text-xs uppercase tracking-widest text-violet-400">
              FAQ
            </p>
            <h2 className="faq-fade-in font-heading mt-2 text-2xl tracking-tight text-foreground sm:text-3xl">
              Questions teams ask before their first graph
            </h2>
            <p
              className="faq-fade-in mt-4 text-sm leading-7 text-muted"
              style={{ animationDelay: "80ms" }}
            >
              Straight answers about how TraceGraph works — what it builds,
              how it reasons, and why a knowledge graph beats search over docs.
            </p>
          </div>

          <div className="flex flex-col gap-2">
            {FAQS.map((item, i) => {
              const isOpen = open === i;
              return (
                <div
                  key={item.q}
                  className="faq-fade-in overflow-hidden rounded-xl border border-border transition-colors hover:border-zinc-600"
                  style={{ animationDelay: `${120 + i * 60}ms` }}
                >
                  <button
                    type="button"
                    onClick={() => setOpen(isOpen ? null : i)}
                    className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
                    aria-expanded={isOpen}
                  >
                    <span className="font-heading text-sm text-foreground sm:text-base">
                      {item.q}
                    </span>
                    <ChevronDown
                      className={cn(
                        "h-4 w-4 shrink-0 text-muted transition-transform duration-300",
                        isOpen && "rotate-180 text-foreground",
                      )}
                    />
                  </button>

                  <div
                    className={cn(
                      "grid transition-[grid-template-rows] duration-300 ease-out",
                      isOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]",
                    )}
                  >
                    <div className="overflow-hidden">
                      <p
                        className={cn(
                          "px-5 pb-4 text-sm leading-7 text-muted transition-opacity duration-300",
                          isOpen ? "opacity-100" : "opacity-0",
                        )}
                      >
                        {item.a}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}

"use client";

import { useMemo, useState } from "react";
import { ArrowLeftRight, Compass, ImageOff, Search } from "lucide-react";
import { Modal } from "@/components/ui/modal";
import { cn } from "@/lib/utils";
import type { CrawlResult, ScreenInfo } from "@/lib/api";

function ScreenRow({
  screen,
  active,
  onSelect,
}: {
  screen: ScreenInfo;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "flex w-full items-center gap-3 border-b border-border px-4 py-2.5 text-left transition-colors last:border-0 hover:bg-white/[0.03]",
        active && "bg-white/[0.05]",
      )}
    >
      <div className="flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-md border border-border bg-white/[0.02]">
        {screen.screenshot_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={screen.screenshot_url}
            alt=""
            className="h-full w-full object-cover object-top"
          />
        ) : (
          <ImageOff className="h-3.5 w-3.5 text-muted" strokeWidth={1.5} />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-xs text-foreground">
          {screen.label || screen.title || screen.url}
        </p>
        <p className="truncate text-[11px] text-muted">{screen.url}</p>
      </div>
      {screen.authenticated && (
        <span className="shrink-0 rounded border border-border px-1.5 py-0.5 text-[10px] uppercase text-muted">
          Auth
        </span>
      )}
    </button>
  );
}

function ScreenDetail({
  screen,
  transitions,
  screenLabel,
}: {
  screen: ScreenInfo;
  transitions: CrawlResult["transitions"];
  screenLabel: (id: string) => string;
}) {
  const related = transitions.filter(
    (t) => t.from_screen === screen.screen_id || t.to_screen === screen.screen_id,
  );

  return (
    <div className="flex flex-col gap-4 p-4">
      <div className="overflow-hidden rounded-lg border border-border bg-white/[0.02]">
        {screen.screenshot_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={screen.screenshot_url} alt="" className="w-full object-cover" />
        ) : (
          <div className="flex h-40 items-center justify-center text-xs text-muted">
            No screenshot captured
          </div>
        )}
      </div>

      <div>
        <p className="text-sm font-medium text-foreground">
          {screen.label || screen.title || screen.url}
        </p>
        {screen.purpose && (
          <p className="mt-1 text-xs leading-5 text-muted">{screen.purpose}</p>
        )}
      </div>

      {screen.primary_actions && screen.primary_actions.length > 0 && (
        <section>
          <h4 className="text-[11px] font-medium uppercase tracking-wider text-muted">
            Primary actions
          </h4>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {screen.primary_actions.map((action) => (
              <span
                key={action}
                className="rounded-full border border-border bg-white/[0.02] px-2.5 py-1 text-[11px] text-foreground"
              >
                {action}
              </span>
            ))}
          </div>
        </section>
      )}

      {screen.key_components && screen.key_components.length > 0 && (
        <section>
          <h4 className="text-[11px] font-medium uppercase tracking-wider text-muted">
            Key components
          </h4>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {screen.key_components.map((c) => (
              <span
                key={c}
                className="rounded border border-border px-2 py-0.5 text-[11px] text-muted"
              >
                {c}
              </span>
            ))}
          </div>
        </section>
      )}

      <section>
        <h4 className="text-[11px] font-medium uppercase tracking-wider text-muted">
          Transitions ({related.length})
        </h4>
        <div className="mt-2 flex flex-col gap-1.5">
          {related.length === 0 && (
            <p className="text-[11px] text-muted">No linked transitions captured.</p>
          )}
          {related.map((t, i) => {
            const outgoing = t.from_screen === screen.screen_id;
            return (
              <div
                key={`${t.from_screen}-${t.to_screen}-${i}`}
                className="flex items-center gap-2 rounded border border-border px-2.5 py-1.5 text-[11px] text-muted"
              >
                <ArrowLeftRight className="h-3 w-3 shrink-0" />
                <span className="truncate text-foreground">
                  {outgoing ? screenLabel(t.to_screen) : screenLabel(t.from_screen)}
                </span>
                <span className="shrink-0">{t.action || "navigate"}</span>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}

export function CrawlModal({
  open,
  onClose,
  fullName,
  result,
}: {
  open: boolean;
  onClose: () => void;
  fullName: string;
  result: CrawlResult | null;
}) {
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const screens = result?.screens ?? [];
  const filtered = useMemo(() => {
    if (!query) return screens;
    const q = query.toLowerCase();
    return screens.filter((s) =>
      `${s.label ?? ""} ${s.title ?? ""} ${s.url}`.toLowerCase().includes(q),
    );
  }, [screens, query]);

  const selected = screens.find((s) => s.screen_id === selectedId) ?? screens[0] ?? null;
  const screenLabel = (id: string) => {
    const s = screens.find((sc) => sc.screen_id === id);
    return s ? s.label || s.title || s.url : id;
  };

  if (!result) return null;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Screen graph · ${fullName}`}
      icon={<Compass className="h-4 w-4 text-foreground" strokeWidth={1.5} />}
      subtitle="Screens crawled from the live application and the transitions inferred between them. Select a screen to inspect its captured response."
      className="max-w-6xl"
    >
      <div className="flex flex-wrap gap-2 border-b border-border px-6 py-3">
        <span className="rounded-full border border-border px-2.5 py-0.5 text-xs text-foreground">
          {result.screen_count.toLocaleString()} screens
        </span>
        <span className="rounded-full border border-border px-2.5 py-0.5 text-xs text-foreground">
          {result.transitions.length.toLocaleString()} transitions
        </span>
        <span className="rounded-full border border-border px-2.5 py-0.5 text-xs text-muted">
          {result.base_url}
        </span>
      </div>

      {result.capture_note && (
        <div className="border-b border-amber-500/20 bg-amber-500/5 px-6 py-3 text-xs leading-5 text-amber-200/90">
          {result.capture_note}
        </div>
      )}

      <div className="grid min-h-[420px] md:grid-cols-2">
        <div className="flex flex-col border-b border-border md:border-b-0 md:border-r">
          <div className="relative border-b border-border px-4 py-3">
            <Search className="pointer-events-none absolute left-7 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search screens…"
              className="w-full rounded-md border border-border bg-transparent py-2 pl-9 pr-3 text-xs text-foreground placeholder:text-muted focus:border-zinc-500 focus:outline-none"
            />
          </div>
          <div className="flex-1 overflow-y-auto">
            {filtered.map((screen) => (
              <ScreenRow
                key={screen.screen_id}
                screen={screen}
                active={selected?.screen_id === screen.screen_id}
                onSelect={() => setSelectedId(screen.screen_id)}
              />
            ))}
            {filtered.length === 0 && (
              <p className="px-4 py-6 text-center text-xs text-muted">
                No screens match your search.
              </p>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {selected ? (
            <ScreenDetail
              screen={selected}
              transitions={result.transitions}
              screenLabel={screenLabel}
            />
          ) : (
            <p className="flex h-full items-center justify-center text-xs text-muted">
              No screens captured for this crawl.
            </p>
          )}
        </div>
      </div>
    </Modal>
  );
}

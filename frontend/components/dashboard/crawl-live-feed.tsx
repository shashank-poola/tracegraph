"use client";

import { ImageOff, Radar } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ScreenInfo } from "@/lib/api";

/** Live-updating feed of screens as they're captured, for use while a crawl job is running. */
export function CrawlLiveFeed({
  screens,
  statusMessage,
}: {
  screens: ScreenInfo[];
  statusMessage: string;
}) {
  if (screens.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
        <Radar className="h-5 w-5 animate-pulse text-muted" strokeWidth={1.5} />
        <p className="text-xs text-muted">
          {statusMessage || "Waiting for the browser to capture the first screen…"}
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-2 overflow-y-auto">
      {screens.map((screen, i) => {
        const isLatest = i === screens.length - 1;
        return (
          <div
            key={screen.screen_id}
            className={cn(
              "flex items-center gap-3 rounded-lg border px-3 py-2 transition-colors",
              isLatest
                ? "border-cyan-400/40 bg-cyan-400/[0.04]"
                : "border-border bg-white/[0.02]",
            )}
          >
            <div className="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-md border border-border bg-white/[0.02]">
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
            {isLatest && (
              <span className="flex shrink-0 items-center gap-1 text-[10px] text-cyan-300">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-400" />
                Just captured
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

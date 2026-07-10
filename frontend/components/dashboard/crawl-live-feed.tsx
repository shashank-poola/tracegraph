"use client";

import { useState } from "react";
import { ImageOff, Radar } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ScreenInfo } from "@/lib/api";

export function Thumbnail({
  src,
  className,
}: {
  src?: string;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);

  if (!src || failed) {
    return (
      <div
        className={cn(
          "flex items-center justify-center bg-white/[0.02] text-muted",
          className,
        )}
      >
        <ImageOff className="h-3.5 w-3.5" strokeWidth={1.5} />
      </div>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt=""
      className={className}
      onError={() => setFailed(true)}
    />
  );
}

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
            key={`${screen.screen_id}-${i}`}
            className={cn(
              "flex items-center gap-3 rounded-lg border px-3 py-2 transition-colors",
              isLatest
                ? "border-cyan-400/40 bg-cyan-400/[0.04]"
                : "border-border bg-white/[0.02]",
            )}
          >
            <Thumbnail
              src={screen.screenshot_url}
              className="h-10 w-10 shrink-0 rounded-md border border-border object-cover object-top"
            />
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

export function CrawlHeroScreenshot({
  src,
  title,
  subtitle,
}: {
  src?: string;
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="overflow-hidden rounded-lg border border-border bg-white/[0.02]">
      <Thumbnail
        src={src}
        className="h-44 w-full object-cover object-top"
      />
      <div className="border-t border-border px-3 py-2.5">
        <p className="truncate text-xs font-medium text-foreground">{title}</p>
        {subtitle && (
          <p className="mt-0.5 truncate text-[11px] text-muted">{subtitle}</p>
        )}
      </div>
    </div>
  );
}

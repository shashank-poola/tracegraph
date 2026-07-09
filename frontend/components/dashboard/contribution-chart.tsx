"use client";

import { cn } from "@/lib/utils";

type Day = { date: string; count: number };

function level(count: number): string {
  if (count === 0) return "bg-zinc-900";
  if (count <= 2) return "bg-emerald-900/80";
  if (count <= 5) return "bg-emerald-700/80";
  if (count <= 9) return "bg-emerald-500/80";
  return "bg-emerald-400";
}

export function ContributionChart({
  total,
  days,
}: {
  total: number;
  days: Day[];
}) {
  const weeks: Day[][] = [];
  for (let i = 0; i < days.length; i += 7) {
    weeks.push(days.slice(i, i + 7));
  }

  return (
    <div className="flex w-full flex-col gap-2 border-t border-border pt-4">
      <div className="flex items-baseline justify-between">
        <span className="text-xs text-muted">Contributions</span>
        <span className="font-heading text-sm text-foreground">
          {total.toLocaleString()}
        </span>
      </div>
      <div
        className="grid w-full gap-[2px]"
        style={{ gridTemplateColumns: `repeat(${weeks.length}, minmax(0, 1fr))` }}
      >
        {weeks.map((week, wi) => (
          <div key={wi} className="flex min-w-0 flex-col gap-[2px]">
            {week.map((day) => (
              <div
                key={day.date}
                title={`${day.count} on ${day.date}`}
                className={cn(
                  "aspect-square w-full rounded-[2px]",
                  level(day.count),
                )}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

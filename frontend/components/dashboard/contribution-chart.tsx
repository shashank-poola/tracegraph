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
  const recent = days.slice(-91);
  const weeks: Day[][] = [];
  for (let i = 0; i < recent.length; i += 7) {
    weeks.push(recent.slice(i, i + 7));
  }

  return (
    <div className="flex flex-col gap-2 border-t border-border pt-4">
      <div className="flex items-baseline justify-between">
        <span className="text-xs text-muted">Contributions</span>
        <span className="font-heading text-sm text-foreground">
          {total.toLocaleString()}
        </span>
      </div>
      <div className="flex gap-[3px] overflow-hidden">
        {weeks.map((week, wi) => (
          <div key={wi} className="flex flex-col gap-[3px]">
            {week.map((day) => (
              <div
                key={day.date}
                title={`${day.count} on ${day.date}`}
                className={cn("h-[9px] w-[9px] rounded-[2px]", level(day.count))}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

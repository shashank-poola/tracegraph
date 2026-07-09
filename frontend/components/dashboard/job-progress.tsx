import { cn } from "@/lib/utils";
import type { JobStatus } from "@/lib/api";

export function JobProgress({ status }: { status: JobStatus }) {
  const isError = status.state === "error";
  return (
    <div className="flex flex-col gap-1.5">
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
        <div
          className={cn(
            "h-full rounded-full transition-all",
            isError ? "bg-red-500" : "bg-foreground",
          )}
          style={{ width: `${Math.max(status.progress * 100, isError ? 100 : 4)}%` }}
        />
      </div>
      <p
        className={cn(
          "text-xs",
          isError ? "text-red-400" : "text-muted",
        )}
      >
        {isError ? status.error ?? "Something went wrong" : status.message}
      </p>
    </div>
  );
}

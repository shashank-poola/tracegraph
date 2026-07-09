"use client";

import { FileText } from "lucide-react";
import { Modal } from "@/components/ui/modal";
import type { IngestResult } from "@/lib/api";

export function IngestModal({
  open,
  onClose,
  fullName,
  result,
}: {
  open: boolean;
  onClose: () => void;
  fullName: string;
  result: IngestResult | null;
}) {
  if (!result) return null;

  const docCount = result.files?.length ?? 0;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Product requirements · ${fullName}`}
      icon={<FileText className="h-4 w-4 text-foreground" strokeWidth={1.5} />}
      subtitle={`${result.requirement_count.toLocaleString()} structured requirements parsed from ${docCount} doc file${docCount === 1 ? "" : "s"} in the codebase. Persisted — restored automatically on your next visit.`}
      className="max-w-3xl"
    >
      <div className="space-y-6 px-6 py-5">
        {(result.overview || result.excerpt) && (
          <section>
            <h3 className="text-[11px] font-medium uppercase tracking-wider text-muted">
              Codebase overview
            </h3>
            <div className="mt-3 space-y-3 text-sm leading-7 text-foreground">
              {result.overview && (
                <p className="whitespace-pre-wrap">{result.overview}</p>
              )}
              {result.excerpt && (
                <div className="rounded-lg border border-border bg-white/[0.02] p-4 text-muted">
                  <p className="whitespace-pre-wrap">{result.excerpt}</p>
                </div>
              )}
            </div>
          </section>
        )}

        {result.requirements.length > 0 && (
          <section>
            <h3 className="text-[11px] font-medium uppercase tracking-wider text-muted">
              Requirements ({result.requirements.length})
            </h3>
            <div className="mt-3 divide-y divide-border rounded-lg border border-border">
              {result.requirements.slice(0, 50).map((req) => (
                <div key={req.req_id} className="px-4 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm font-medium text-foreground">
                      {req.title}
                    </p>
                    {req.priority && (
                      <span className="shrink-0 rounded border border-border px-1.5 py-0.5 text-[10px] text-muted">
                        {req.priority}
                      </span>
                    )}
                  </div>
                  {req.description && (
                    <p className="mt-1 text-xs leading-5 text-muted">
                      {req.description}
                    </p>
                  )}
                </div>
              ))}
              {result.requirements.length > 50 && (
                <p className="px-4 py-3 text-center text-xs text-muted">
                  +{result.requirements.length - 50} more requirements
                </p>
              )}
            </div>
          </section>
        )}
      </div>
    </Modal>
  );
}

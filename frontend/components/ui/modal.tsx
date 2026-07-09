"use client";

import { useEffect, type ReactNode } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

export function Modal({
  open,
  onClose,
  title,
  icon,
  subtitle,
  children,
  className,
  headerRight,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  icon?: ReactNode;
  subtitle?: string;
  children: ReactNode;
  className?: string;
  headerRight?: ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center overflow-y-auto p-4 sm:p-8">
      <button
        type="button"
        aria-label="Close"
        className="fixed inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />
      <div
        className={cn(
          "relative z-10 my-auto flex w-full max-w-5xl flex-col overflow-hidden rounded-xl border border-border bg-background shadow-2xl",
          className,
        )}
      >
        <div className="flex items-start justify-between gap-4 border-b border-border px-6 py-5">
          <div className="flex min-w-0 flex-col gap-1">
            <div className="flex items-center gap-2">
              {icon}
              <h2 className="truncate font-heading text-lg text-foreground">
                {title}
              </h2>
            </div>
            {subtitle && (
              <p className="text-sm leading-6 text-muted">{subtitle}</p>
            )}
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {headerRight}
            <button
              type="button"
              onClick={onClose}
              className="rounded-md p-1.5 text-muted transition-colors hover:bg-white/5 hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
        <div className="max-h-[min(75vh,720px)] overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}

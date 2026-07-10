"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { resolvePostAuthPath } from "@/lib/api";

export default function AuthCallbackPage() {
  const router = useRouter();

  useEffect(() => {
    resolvePostAuthPath()
      .then((path) => {
        router.replace(path === "/login" ? "/login?error=oauth_failed" : path);
      })
      .catch(() => router.replace("/login?error=oauth_failed"));
  }, [router]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 text-muted">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-foreground" />
      <p className="text-sm">Signing you in…</p>
    </div>
  );
}

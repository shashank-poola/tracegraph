"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getInstallationStatus } from "@/lib/api";
import { useCurrentUser } from "@/hooks/use-current-user";

export function AppInstallGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, loading } = useCurrentUser();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      setReady(true);
      return;
    }
    getInstallationStatus()
      .then((status) => {
        if (status.required && !status.installed) {
          router.replace("/install");
          return;
        }
        setReady(true);
      })
      .catch(() => setReady(true));
  }, [user, loading, router]);

  if (loading || (user && !ready)) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-foreground" />
      </div>
    );
  }

  return children;
}

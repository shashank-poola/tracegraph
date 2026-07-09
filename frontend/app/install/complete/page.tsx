"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUser, getInstallationStatus } from "@/lib/api";

export default function InstallCompletePage() {
  const router = useRouter();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const installationId = params.get("installation_id");
    const parsedId =
      installationId && /^\d+$/.test(installationId)
        ? Number(installationId)
        : undefined;

    getCurrentUser().then((user) => {
      if (!user) {
        router.replace("/login");
        return;
      }
      getInstallationStatus(parsedId).then((status) => {
        if (status.required && !status.installed) {
          router.replace("/install");
          return;
        }
        router.replace("/dashboard");
      });
    });
  }, [router]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 text-muted">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-foreground" />
      <p className="text-sm">Finishing setup…</p>
    </div>
  );
}

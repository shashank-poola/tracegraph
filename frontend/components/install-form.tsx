"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { getCurrentUser, getInstallationStatus, githubInstallUrl } from "@/lib/api";
import { Button } from "@/components/ui/button";

export function InstallForm() {
  const router = useRouter();

  useEffect(() => {
    getCurrentUser().then((user) => {
      if (!user) {
        router.replace("/login");
        return;
      }
      getInstallationStatus().then((status) => {
        if (!status.required || status.installed) {
          router.replace("/dashboard");
        }
      });
    });
  }, [router]);
  return (
    <div className="flex w-full flex-col items-center justify-center gap-8 px-8 py-16 sm:px-16">
      <Link href="/" className="flex items-center">
        <Image
          src="/logo.png"
          alt="TraceGraph"
          width={200}
          height={70}
          priority
          className="h-9 w-auto"
        />
      </Link>

      <div className="flex w-full max-w-sm flex-col gap-2 text-center">
        <h1 className="font-heading text-2xl tracking-tight text-foreground">
          Install on GitHub
        </h1>
        <p className="text-sm leading-6 text-muted">
          You&apos;re signed in. One more step: install the TraceGraph GitHub
          App on the repositories you want PR reviews and webhooks on.
        </p>
      </div>

      <a href={githubInstallUrl()} className="w-full max-w-sm">
        <Button size="lg" className="w-full">
          <Image src="/github.png" alt="" width={20} height={20} />
          Install GitHub App
        </Button>
      </a>

      <Link href="/install/complete" className="w-full max-w-sm">
        <Button variant="outline" size="lg" className="w-full">
          Already installed? Continue to TraceGraph
        </Button>
      </Link>

      <p className="max-w-sm text-center text-xs leading-5 text-muted">
        After you pick repositories on GitHub and click Install, you should be
        sent back here automatically. If GitHub leaves you on its settings page,
        use the button above or open{" "}
        <Link href="/install/complete" className="text-foreground underline">
          /install/complete
        </Link>
        .
      </p>
    </div>
  );
}

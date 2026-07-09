"use client";

import Image from "next/image";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { githubLoginUrl } from "@/lib/api";
import { Button } from "@/components/ui/button";

const ERROR_MESSAGES: Record<string, string> = {
  oauth_failed: "GitHub sign-in failed. Please try again.",
  access_denied: "Authorization was cancelled.",
};

export function LoginForm() {
  const params = useSearchParams();
  const error = params.get("error");

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
          Welcome back
        </h1>
        <p className="text-sm leading-6 text-muted">
          Sign in with GitHub, then install the TraceGraph app on your
          repositories for PR reviews and webhooks.
        </p>
      </div>

      {error && (
        <p className="w-full max-w-sm rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-center text-sm text-red-400">
          {ERROR_MESSAGES[error] ?? "Something went wrong. Please try again."}
        </p>
      )}

      <a href={githubLoginUrl()} className="w-full max-w-sm">
        <Button size="lg" className="w-full">
          <Image src="/github.png" alt="" width={20} height={20} />
          Continue with GitHub
        </Button>
      </a>

      <p className="max-w-sm text-center text-xs leading-5 text-muted">
        Step 1 of 2: sign in with GitHub. You&apos;ll install the TraceGraph app
        on your repos right after.
      </p>
    </div>
  );
}

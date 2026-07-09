"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { CurrentUser } from "@/lib/api";
import { logout } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { CONTAINER } from "@/lib/layout";

export function Topbar({ user }: { user: CurrentUser }) {
  const router = useRouter();

  async function handleLogout() {
    await logout();
    router.replace("/");
  }

  return (
    <header className="sticky top-0 z-50 bg-background/80 backdrop-blur">
      <div className={`${CONTAINER} flex h-16 items-center justify-between`}>
        <Link href="/dashboard" className="flex items-center">
          <Image
            src="/logo.png"
            alt="TraceGraph"
            width={160}
            height={50}
            className="h-9 w-auto"
          />
        </Link>

        <div className="flex items-center gap-3">
          <span className="hidden text-sm text-muted sm:inline">
            {user.login}
          </span>
          {user.avatar_url && (
            <Image
              src={user.avatar_url}
              alt={user.login}
              width={28}
              height={28}
              className="h-7 w-7 rounded-full border border-border"
            />
          )}
          <Button variant="outline" size="sm" onClick={handleLogout}>
            Sign out
          </Button>
        </div>
      </div>
    </header>
  );
}

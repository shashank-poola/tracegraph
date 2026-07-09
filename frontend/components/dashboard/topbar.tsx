"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { CurrentUser } from "@/lib/api";
import { logout } from "@/lib/api";
import { Button } from "@/components/ui/button";

export function Topbar({ user }: { user: CurrentUser }) {
  const router = useRouter();

  async function handleLogout() {
    await logout();
    router.replace("/");
  }

  return (
    <header className="flex h-16 items-center justify-between border-b border-border/60 px-6">
      <Link href="/dashboard" className="flex items-center">
        <Image
          src="/logo.png"
          alt="TraceGraph"
          width={110}
          height={37}
          className="h-7 w-auto"
        />
      </Link>

      <div className="flex items-center gap-3">
        <span className="text-sm text-muted">{user.login}</span>
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
    </header>
  );
}

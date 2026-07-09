import Link from "next/link";
import Image from "next/image";
import { Button } from "@/components/ui/button";

export function Navbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-border/60 bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <Link href="/" className="flex items-center">
          <Image
            src="/logo.png"
            alt="TraceGraph"
            width={200}
            height={50}
            priority
            className="h-8 w-auto"
          />
        </Link>

        <nav className="hidden items-center gap-8 text-sm text-muted md:flex">
          <a href="#layers" className="transition-colors hover:text-foreground">
            Layers
          </a>
          <a href="#how" className="transition-colors hover:text-foreground">
            How it works
          </a>
          <a
            href="https://github.com"
            target="_blank"
            rel="noreferrer"
            className="transition-colors hover:text-foreground"
          >
            GitHub
          </a>
        </nav>

        <Link href="/login">
          <Button size="sm">Sign in</Button>
        </Link>
      </div>
    </header>
  );
}

import Link from "next/link";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { CONTAINER } from "@/lib/layout";

export function Navbar() {
  return (
    <header className="sticky top-0 z-50 bg-background/80 backdrop-blur">
      <div className={`${CONTAINER} flex h-16 items-center justify-between`}>
        <Link href="/" className="flex items-center">
          <Image
            src="/logo.png"
            alt="TraceGraph"
            width={240}
            height={60}
            priority
            className="h-10 w-auto"
          />
        </Link>

        <nav className="hidden items-center gap-8 text-sm text-muted md:flex">
          <a href="#layers" className="transition-colors hover:text-foreground">
            Layers
          </a>
          <a href="#how" className="transition-colors hover:text-foreground">
            How it works
          </a>
          <a href="#faq" className="transition-colors hover:text-foreground">
            FAQ
          </a>
        </nav>

        <Link href="/login">
          <Button size="sm">Sign in</Button>
        </Link>
      </div>
    </header>
  );
}

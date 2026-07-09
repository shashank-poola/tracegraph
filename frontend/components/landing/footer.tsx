import Image from "next/image";
import { CONTAINER } from "@/lib/layout";

export function Footer() {
  return (
    <footer className="py-10">
      <div
        className={`${CONTAINER} flex flex-col items-center justify-between gap-4 text-sm text-muted sm:flex-row`}
      >
        <Image
          src="/logo.png"
          alt="TraceGraph"
          width={100}
          height={33}
          className="h-5 w-auto opacity-80"
        />
        <span>Knowledge graphs for pull request blast radius.</span>
      </div>
    </footer>
  );
}

import Image from "next/image";

export function Footer() {
  return (
    <footer className="border-t border-border/60 py-10">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 text-sm text-muted sm:flex-row">
        <Image
          src="/logo.png"
          alt="TraceGraph"
          width={150}
          height={50}
          className="h-5 w-auto opacity-80"
        />
        <span>Knowledge graphs for pull request blast radius.</span>
      </div>
    </footer>
  );
}

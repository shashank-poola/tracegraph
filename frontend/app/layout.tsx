import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "TraceGraph",
    template: "%s · TraceGraph",
  },
  description:
    "TraceGraph crawls your app, ingests your PRD, and builds a knowledge graph across requirements, UI, and code — so you know exactly what a PR breaks.",
  icons: {
    icon: [{ url: "/tglogo.jpg", type: "image/jpeg" }],
    apple: [{ url: "/tglogo.jpg", type: "image/jpeg" }],
    shortcut: "/tglogo.jpg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Geist:wght@100..900&family=Geist+Pixel&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-full bg-background font-sans text-foreground antialiased">
        {children}
      </body>
    </html>
  );
}

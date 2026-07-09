import type { Metadata } from "next";
import Image from "next/image";
import { Suspense } from "react";
import { InstallForm } from "@/components/install-form";

export const metadata: Metadata = {
  title: "Install GitHub App",
};

export default function InstallPage() {
  return (
    <div className="grid min-h-screen md:grid-cols-2">
      <Suspense fallback={null}>
        <InstallForm />
      </Suspense>

      <div className="relative hidden md:block">
        <Image
          src="/signup/signup.jpg"
          alt=""
          fill
          priority
          className="object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-background via-transparent to-transparent" />
      </div>
    </div>
  );
}

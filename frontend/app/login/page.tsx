import type { Metadata } from "next";
import Image from "next/image";
import { Suspense } from "react";
import { LoginForm } from "@/components/login-form";

export const metadata: Metadata = {
  title: "Sign in — TraceGraph",
};

export default function LoginPage() {
  return (
    <div className="grid min-h-screen md:grid-cols-2">
      <Suspense fallback={null}>
        <LoginForm />
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

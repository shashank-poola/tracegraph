import type { Metadata } from "next";
import { AppInstallGuard } from "@/components/app-install-guard";

export const metadata: Metadata = {
  title: "Repositories",
};

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AppInstallGuard>{children}</AppInstallGuard>;
}

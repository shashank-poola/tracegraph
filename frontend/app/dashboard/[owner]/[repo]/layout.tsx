import type { Metadata } from "next";

type Props = {
  params: Promise<{ owner: string; repo: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { owner, repo } = await params;
  return {
    title: `${owner}/${repo}`,
  };
}

export default function RepoLayout({ children }: { children: React.ReactNode }) {
  return children;
}

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type CurrentUser = {
  id: string;
  login: string;
  name: string;
  email: string;
  avatar_url: string;
};

export type Repo = {
  full_name: string;
  name: string;
  owner: string;
  description: string;
  private: boolean;
  language: string;
  stargazers_count: number;
  forks_count: number;
  default_branch: string;
  html_url: string;
  updated_at: string;
  tracked: boolean;
};

export type RepoDetail = Repo & {
  commit_count: number;
  pull_request_count: number;
  status: {
    has_tree: boolean;
    has_crawl: boolean;
    has_requirements: boolean;
    has_graph: boolean;
  };
};

export type PullRequestReview = {
  verdict: string;
  risk: string;
  good_enough: boolean;
  summary: string;
  comment_url: string | null;
};

export type PullRequest = {
  number: number;
  title: string;
  state: string;
  author: string;
  html_url: string;
  created_at: string;
  updated_at: string;
  head_sha: string;
  review: PullRequestReview | null;
};

export type JobState = "pending" | "running" | "done" | "error";

export type JobStatus = {
  job_id: string;
  state: JobState;
  progress: number;
  message: string;
  error: string | null;
  result?: unknown;
  crawl_result?: unknown;
  ingest_result?: unknown;
};

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    credentials: "include",
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `${path} failed (${res.status})`);
  }
  return res.json();
}

export function githubLoginUrl(): string {
  return `${API_URL}/auth/github/login`;
}

export async function getCurrentUser(): Promise<CurrentUser | null> {
  try {
    const data = await api<{ user: CurrentUser }>("/auth/me");
    return data.user;
  } catch {
    return null;
  }
}

export async function logout(): Promise<void> {
  await fetch(`${API_URL}/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
}

export type GithubProfile = {
  login: string;
  name: string;
  avatar_url: string;
  bio: string;
  location: string;
  html_url: string;
  public_repos: number;
  followers: number;
  following: number;
  tracked_count: number;
};

export function getProfile(): Promise<GithubProfile> {
  return api("/repos/profile");
}

export function listRepos(): Promise<{ repos: Repo[]; tracked_count: number }> {
  return api("/repos");
}

export function trackRepo(fullName: string): Promise<unknown> {
  return api(`/repos/${fullName}/track`, { method: "POST" });
}

export function untrackRepo(fullName: string): Promise<unknown> {
  return api(`/repos/${fullName}/track`, { method: "DELETE" });
}

export function getRepoDetail(fullName: string): Promise<RepoDetail> {
  return api(`/repos/${fullName}`);
}

export function listRepoPulls(
  fullName: string,
): Promise<{ pulls: PullRequest[] }> {
  return api(`/repos/${fullName}/pulls`);
}

export function startAnalyze(params: {
  full_name: string;
  owner: string;
  repo: string;
  ref?: string;
  build_graph?: boolean;
}): Promise<{ job_id: string; state: JobState }> {
  return api("/analyze", { method: "POST", body: JSON.stringify(params) });
}

export function startIngest(params: {
  source: string;
  source_type?: string;
  full_name?: string;
}): Promise<{ job_id: string; state: JobState }> {
  return api("/ingest", { method: "POST", body: JSON.stringify(params) });
}

export function startCrawl(params: {
  base_url: string;
  full_name?: string;
  routes?: { path: string; authenticated: boolean }[];
  crawl_mode?: string;
}): Promise<{ job_id: string; state: JobState }> {
  return api("/crawl", { method: "POST", body: JSON.stringify(params) });
}

export function getJobStatus(jobId: string): Promise<JobStatus> {
  return api(`/analyze/${jobId}`);
}

export async function pollJob(
  jobId: string,
  onUpdate: (status: JobStatus) => void,
  { intervalMs = 1500 }: { intervalMs?: number } = {},
): Promise<JobStatus> {
  while (true) {
    const status = await getJobStatus(jobId);
    onUpdate(status);
    if (status.state === "done" || status.state === "error") {
      return status;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
}

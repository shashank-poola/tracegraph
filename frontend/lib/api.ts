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
  base_ref?: string;
  head_ref?: string;
  commits?: number;
  changed_files?: number;
  additions?: number;
  deletions?: number;
  comments?: number;
  review_comments?: number;
  review: PullRequestReview | null;
};

export type RepoTree = {
  full_name: string;
  ref?: string;
  summary?: string;
  file_count?: number;
  python_file_count?: number;
  files: {
    path: string;
    language?: string;
    parsed?: boolean;
    functions: { name: string }[];
    classes: { name: string }[];
  }[];
  graph?: {
    console_url: string;
    nodes_written: number;
    relationships_written: number;
    queries: { name: string; cypher: string }[];
  } | null;
};

export type ScreenInfo = {
  screen_id: string;
  url: string;
  title?: string;
  authenticated?: boolean;
  interactive_count?: number;
  screenshot_url?: string;
  label?: string;
  purpose?: string;
  primary_actions?: string[];
  key_components?: string[];
};

export type Transition = {
  from_screen: string;
  to_screen: string;
  action?: string;
};

export type CrawlResult = {
  run_id: string;
  base_url: string;
  artifact_dir?: string;
  screen_count: number;
  screens: ScreenInfo[];
  transitions: Transition[];
  capture_note?: string;
};

export type IngestResult = {
  source: string;
  source_type?: string;
  requirement_count: number;
  requirements: {
    req_id: string;
    title: string;
    description?: string;
    priority?: string;
  }[];
  overview?: string;
  excerpt?: string;
  files?: string[];
};

export type JobState = "pending" | "running" | "done" | "error";

export type JobStatus = {
  job_id: string;
  state: JobState;
  progress: number;
  message: string;
  error: string | null;
  result?: RepoTree | null;
  crawl_result?: CrawlResult | null;
  ingest_result?: IngestResult | null;
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

export function githubInstallUrl(): string {
  return `${API_URL}/auth/github/install`;
}

export type InstallationStatus = {
  required: boolean;
  installed: boolean;
};

export async function getInstallationStatus(
  installationId?: number,
): Promise<InstallationStatus> {
  const qs =
    installationId != null ? `?installation_id=${installationId}` : "";
  return api<InstallationStatus>(`/auth/github/installation-status${qs}`);
}

export async function getRepoAppInstalled(
  fullName: string,
): Promise<{ installed: boolean; required: boolean }> {
  return api(`/repos/${fullName}/app-installed`);
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
  contributions?: {
    total: number;
    days: { date: string; count: number }[];
  };
};

export function getProfile(): Promise<GithubProfile> {
  return api("/repos/profile");
}

export function listRepos(): Promise<{ repos: Repo[]; tracked_count: number }> {
  return api("/repos");
}

export function trackRepo(
  fullName: string,
): Promise<{ status: string; full_name: string }> {
  return api(`/repos/${fullName}/track`, { method: "POST" });
}

export function untrackRepo(
  fullName: string,
): Promise<{ status: string; full_name: string }> {
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

export function getRepoTree(fullName: string): Promise<RepoTree> {
  return api(`/repos/${fullName}/tree`);
}

export function getRepoIngest(fullName: string): Promise<IngestResult> {
  return api(`/repos/${fullName}/ingest`);
}

export function getRepoCrawl(fullName: string): Promise<CrawlResult> {
  return api(`/repos/${fullName}/crawl`);
}

export function getRepoPull(
  fullName: string,
  number: number,
): Promise<PullRequest> {
  return api(`/repos/${fullName}/pulls/${number}`);
}

export function startAnalyze(params: {
  full_name: string;
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
}): Promise<{ job_id: string; state: JobState }> {
  return api("/crawl", { method: "POST", body: JSON.stringify(params) });
}

export function getJobStatus(jobId: string): Promise<JobStatus> {
  return api(`/jobs/${jobId}`);
}

export async function pollJob(
  jobId: string,
  onUpdate: (status: JobStatus) => void,
  {
    intervalMs = 1500,
    signal,
  }: { intervalMs?: number; signal?: AbortSignal } = {},
): Promise<JobStatus> {
  while (true) {
    if (signal?.aborted) {
      throw new DOMException("Polling aborted", "AbortError");
    }
    const status = await getJobStatus(jobId);
    onUpdate(status);
    if (status.state === "done" || status.state === "error") {
      return status;
    }
    await new Promise<void>((resolve, reject) => {
      const timer = setTimeout(resolve, intervalMs);
      signal?.addEventListener(
        "abort",
        () => {
          clearTimeout(timer);
          reject(new DOMException("Polling aborted", "AbortError"));
        },
        { once: true },
      );
    });
  }
}

/** After OAuth or App install, send the user to install or dashboard. */
export async function resolvePostAuthPath(
  installationId?: number,
): Promise<"/login" | "/install" | "/dashboard"> {
  const user = await getCurrentUser();
  if (!user) return "/login";
  const status = await getInstallationStatus(installationId);
  if (status.required && !status.installed) return "/install";
  return "/dashboard";
}

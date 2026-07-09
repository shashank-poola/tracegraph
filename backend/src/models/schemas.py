"""Pydantic models shared across the service."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    full_name: str = Field(..., description="owner/repo")
    owner: str
    repo: str
    ref: str = ""
    token: str = Field(..., repr=False)
    build_graph: bool = True


class FunctionInfo(BaseModel):
    name: str
    args: list[str] = []
    lineno: int = 0
    end_lineno: int = 0
    is_async: bool = False
    decorators: list[str] = []
    calls: list[str] = []
    description: str = ""


class ClassInfo(BaseModel):
    name: str
    lineno: int = 0
    end_lineno: int = 0
    bases: list[str] = []
    decorators: list[str] = []
    methods: list[FunctionInfo] = []
    description: str = ""


class ImportInfo(BaseModel):
    module: str = ""
    names: list[str] = []
    level: int = 0


class FileInfo(BaseModel):
    path: str
    language: str = "python"
    loc: int = 0
    parsed: bool = True
    parse_error: str | None = None
    imports: list[str] = []
    import_records: list[ImportInfo] = []
    functions: list[FunctionInfo] = []
    classes: list[ClassInfo] = []
    description: str = ""


class GraphQuery(BaseModel):
    name: str
    cypher: str


class GraphInfo(BaseModel):
    console_url: str = ""
    instance_name: str = ""
    database: str = ""
    nodes_written: int = 0
    relationships_written: int = 0
    sample_query: str = ""
    connector_name: str = ""
    queries: list[GraphQuery] = []


class RepoTree(BaseModel):
    full_name: str
    ref: str = ""
    summary: str = ""
    file_count: int = 0
    python_file_count: int = 0
    files: list[FileInfo] = []
    graph: GraphInfo | None = None


class GraphRequest(BaseModel):
    tree: RepoTree


class LoginConfig(BaseModel):
    login_url: str
    username: str = Field(..., repr=False)
    password: str = Field(..., repr=False)
    username_selector: str = "input[type=email], input[name=username], #user-name"
    password_selector: str = "input[type=password], #password"
    submit_selector: str = "button[type=submit], #login-button"
    logged_out_marker: str = "/login"


class RouteSpec(BaseModel):
    path: str
    authenticated: bool = False


class CrawlRequest(BaseModel):
    base_url: str
    full_name: str = Field(default="", description="owner/repo — links crawl to SQLite + graph")
    routes: list[RouteSpec] = Field(default_factory=list)
    login: LoginConfig | None = None


class InteractiveElement(BaseModel):
    kind: str = ""
    role: str = ""
    text: str = ""
    selector: str = ""
    href: str = ""


class ScreenInfo(BaseModel):
    screen_id: str
    url: str
    title: str = ""
    depth: int = 0
    discovered_from: str | None = None
    authenticated: bool = False
    interactive_count: int = 0
    dom_path: str = ""
    screenshot_path: str = ""
    a11y_path: str = ""
    screenshot_url: str = ""
    dom: str = ""
    a11y: str = ""
    elements: list[InteractiveElement] = []
    structured_dom: list[Any] = []
    label: str = ""
    purpose: str = ""
    primary_actions: list[str] = []
    key_components: list[str] = []


class Transition(BaseModel):
    from_screen: str
    to_screen: str
    action: str = "navigate"
    element_text: str = ""
    selector: str = ""


class CrawlResult(BaseModel):
    run_id: str
    base_url: str
    artifact_dir: str = ""
    screen_count: int = 0
    screens: list[ScreenInfo] = []
    transitions: list[Transition] = []


class IngestRequest(BaseModel):
    source_type: str = "url"
    source: str
    full_name: str = Field(default="", description="owner/repo — links ingest to SQLite + graph")
    token: str = Field(default="", repr=False)


class Requirement(BaseModel):
    req_id: str
    title: str
    description: str = ""
    user_action: str = ""
    expected_outcome: str = ""
    priority: str = ""
    source_anchor: str = ""


class IngestResult(BaseModel):
    source: str
    source_type: str = ""
    requirement_count: int = 0
    requirements: list[Requirement] = []
    overview: str = ""
    excerpt: str = ""
    files: list[str] = []


class JobState(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    error = "error"


class JobStatus(BaseModel):
    job_id: str
    state: JobState = JobState.pending
    progress: float = 0.0
    message: str = ""
    error: str | None = None
    result: RepoTree | None = None
    crawl_result: CrawlResult | None = None
    ingest_result: IngestResult | None = None


class JobCreated(BaseModel):
    job_id: str
    state: JobState


class ReasonRequest(BaseModel):
    full_name: str
    pr_number: int
    installation_id: int | None = None
    # Optional overrides; backend loads from SQLite when omitted.
    tree: dict[str, Any] | None = None
    crawl: dict[str, Any] | None = None
    requirements: list[dict[str, Any]] = Field(default_factory=list)


class GraphConnectRequest(BaseModel):
    full_name: str
    tree: dict[str, Any] | None = None
    crawl: dict[str, Any] | None = None
    requirements: list[dict[str, Any]] = Field(default_factory=list)

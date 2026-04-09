"""AI report schema — the structured JSON that Claude returns after analysis."""

from pydantic import BaseModel


class Finding(BaseModel):
    id: str
    title: str
    description: str
    cve_ids: list[str] = []
    cvss_score: float | None = None
    risk_level: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    owasp_category: str | None = None
    affected_asset: str
    evidence: str
    business_impact: str
    poc_description: str
    remediation_steps: list[str]
    estimated_fix_time: str
    phase: str
    tool: str


class RemediationItem(BaseModel):
    finding_id: str
    title: str
    priority: str  # quick_win, short_term, long_term
    estimated_effort: str
    steps: list[str]


class CategoryScore(BaseModel):
    category: str
    score: float
    max_score: float
    findings_count: int


class ReportSchema(BaseModel):
    # Summaries
    executive_summary: str
    technical_summary: str

    # Findings
    findings: list[Finding]

    # Scores
    overall_score: float  # 0-100
    category_scores: list[CategoryScore]

    # Remediation
    remediation_roadmap: dict[str, list[RemediationItem]]
    # {"quick_wins": [...], "short_term": [...], "long_term": [...]}

    # Metadata
    scan_id: str
    target: str
    scan_type: str
    phases_completed: list[str]
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int

    # Compliance mapping
    compliance: dict[str, list[str]] = {}
    # {"iso27001": ["A.12.6.1", ...], "nis2": [...], "soc2": [...], "gdpr": [...]}

export interface Target {
  id: string;
  name: string;
  target_type: "domain" | "ip" | "ip_range" | "url";
  value: string;
  scope: Record<string, any> | null;
  is_verified: boolean;
  verified_at: string | null;
  verification_method: string | null;
  verification_token: string | null;
  created_at: string;
}

export interface Scan {
  id: string;
  target_id: string;
  scan_type: "quick" | "full" | "custom";
  phases: string[];
  status: string;
  current_phase: string | null;
  progress: number;
  save_report: boolean;
  security_score: number | null;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  info_count: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  share_token: string | null;
}

export interface Finding {
  id: string;
  title: string;
  description: string;
  cve_ids: string[];
  cvss_score: number | null;
  risk_level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";
  owasp_category: string | null;
  affected_asset: string;
  evidence: string;
  business_impact: string;
  poc_description: string;
  remediation_steps: string[];
  estimated_fix_time: string;
  phase: string;
  tool: string;
}

export interface ReportData {
  executive_summary: string;
  technical_summary: string;
  findings: Finding[];
  overall_score: number;
  category_scores: CategoryScore[];
  remediation_roadmap: Record<string, RemediationItem[]>;
  scan_id: string;
  target: string;
  scan_type: string;
  phases_completed: string[];
  total_findings: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  info_count: number;
  compliance: Record<string, string[]>;
}

export interface CategoryScore {
  category: string;
  score: number;
  max_score: number;
  findings_count: number;
}

export interface RemediationItem {
  finding_id: string;
  title: string;
  priority: string;
  estimated_effort: string;
  steps: string[];
}

export interface ScanLiveEvent {
  type: string;
  phase?: string;
  tool?: string;
  output?: string;
  progress?: number;
  error?: string;
  timestamp: number;
}

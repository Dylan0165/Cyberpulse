const API_BASE = 'http://localhost:7823';

async function request(path: string, options: RequestInit = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers as Record<string, string> },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(2000) });
    return res.ok;
  } catch {
    return false;
  }
}

export async function getRecentScans(limit = 20): Promise<any[]> {
  return request(`/api/scans?limit=${limit}`);
}

export async function getScanData(scanId: string): Promise<any> {
  return request(`/api/scans/${scanId}`);
}

export async function startScan(params: {
  target: string;
  target_type: string;
  scan_type: string;
  scan_mode: string;
  credentials?: Record<string, string>;
  modules?: string[];
}): Promise<{ scan_id: string }> {
  return request('/api/scan/start', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function stopScan(scanId: string): Promise<void> {
  await request(`/api/scan/${scanId}/stop`, { method: 'POST' });
}

export async function getReport(scanId: string): Promise<any> {
  return request(`/api/scans/${scanId}/report`);
}

export async function downloadPdf(scanId: string): Promise<Blob> {
  const res = await fetch(`${API_BASE}/api/scans/${scanId}/pdf`);
  if (!res.ok) throw new Error('PDF download failed');
  return res.blob();
}

export async function getSettings(): Promise<any> {
  return request('/api/settings');
}

export async function saveSettings(settings: Record<string, any>): Promise<void> {
  await request('/api/settings', {
    method: 'PUT',
    body: JSON.stringify(settings),
  });
}

export async function checkTools(): Promise<Record<string, boolean>> {
  return request('/api/tools/check');
}

export function createScanStream(scanId: string): EventSource {
  return new EventSource(`${API_BASE}/api/scan/${scanId}/stream`);
}

export function createAnalysisStream(scanId: string): EventSource {
  return new EventSource(`${API_BASE}/api/scan/${scanId}/analysis/stream`);
}

export async function getAvailableTools(): Promise<any> {
  return request('/api/tools/available');
}

export async function getToolProfiles(): Promise<any[]> {
  return request('/api/tools/profiles');
}

export async function startToolScan(params: {
  target: string;
  profile?: string;
  tool_names?: string[];
  options?: Record<string, any>;
}): Promise<{ scan_id: string; tools: string[] }> {
  return request('/api/tools/scan', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

// ── Assets ────────────────────────────────────────────────────────────────────
export async function getAssets(): Promise<any[]> {
  return request('/api/assets');
}

// ── Schedules ─────────────────────────────────────────────────────────────────
export async function getSchedules(): Promise<any[]> {
  return request('/api/schedules');
}

export async function createSchedule(data: {
  target: string; scan_type?: string; scan_mode?: string;
  target_type?: string; interval?: string; enabled?: boolean;
}): Promise<any> {
  return request('/api/schedules', { method: 'POST', body: JSON.stringify(data) });
}

export async function deleteSchedule(id: string): Promise<void> {
  await request(`/api/schedules/${id}`, { method: 'DELETE' });
}

export async function toggleSchedule(id: string, enabled: boolean): Promise<any> {
  return request(`/api/schedules/${id}/toggle?enabled=${enabled}`, { method: 'PATCH' });
}

// ── Finding marks ─────────────────────────────────────────────────────────────
export async function markFinding(scanId: string, idx: number, status: 'confirmed' | 'false_positive' | 'accepted_risk'): Promise<any> {
  return request(`/api/scans/${scanId}/findings/${idx}/mark?status=${status}`, { method: 'POST' });
}

export async function getFindingMarks(scanId: string): Promise<Record<string, any>> {
  return request(`/api/scans/${scanId}/findings/marks`);
}

// ── AI Chat ───────────────────────────────────────────────────────────────────
export async function chatWithScan(scanId: string, message: string, history?: any[]): Promise<{ answer: string }> {
  return request(`/api/scans/${scanId}/chat`, {
    method: 'POST',
    body: JSON.stringify({ message, history }),
  });
}

export async function getChatHistory(scanId: string): Promise<any[]> {
  return request(`/api/scans/${scanId}/chat/history`);
}

// ── Compare scans ─────────────────────────────────────────────────────────────
export async function compareScans(scanA: string, scanB: string): Promise<any> {
  return request(`/api/scans/compare?scan_a=${scanA}&scan_b=${scanB}`);
}

// ── Webhooks ──────────────────────────────────────────────────────────────────
export async function getWebhooks(): Promise<any[]> {
  return request('/api/webhooks');
}

export async function createWebhook(data: { url: string; events: string[]; enabled?: boolean }): Promise<any> {
  return request('/api/webhooks', { method: 'POST', body: JSON.stringify(data) });
}

export async function deleteWebhook(id: string): Promise<void> {
  await request(`/api/webhooks/${id}`, { method: 'DELETE' });
}

// ── API Keys ──────────────────────────────────────────────────────────────────
export async function getApiKeys(): Promise<any[]> {
  return request('/api/keys');
}

export async function createApiKey(data: { name: string; scope?: string }): Promise<any> {
  return request('/api/keys', { method: 'POST', body: JSON.stringify(data) });
}

export async function deleteApiKey(id: string): Promise<void> {
  await request(`/api/keys/${id}`, { method: 'DELETE' });
}

// ── Audit log ─────────────────────────────────────────────────────────────────
export async function getAuditLog(limit = 100): Promise<any[]> {
  return request(`/api/audit?limit=${limit}`);
}

// ── Notifications ─────────────────────────────────────────────────────────────
export async function getNotifications(limit = 30): Promise<any[]> {
  return request(`/api/notifications?limit=${limit}`);
}

export async function getUnreadCount(): Promise<{ count: number }> {
  return request('/api/notifications/unread-count');
}

export async function markNotificationRead(id: string): Promise<any> {
  return request(`/api/notifications/${id}/read`, { method: 'POST' });
}

export async function markAllRead(): Promise<void> {
  await request('/api/notifications/read-all', { method: 'POST' });
}

export async function clearNotifications(): Promise<void> {
  await request('/api/notifications/all', { method: 'DELETE' });
}

// ── Authorizations ────────────────────────────────────────────────────────────
export async function createAuthorization(data: {
  target: string; authorized_by: string; organization: string; confirmed: boolean;
}): Promise<any> {
  return request('/api/authorizations', { method: 'POST', body: JSON.stringify(data) });
}

export async function checkAuthorization(target: string): Promise<{ authorized: boolean }> {
  return request(`/api/authorizations/${encodeURIComponent(target)}`);
}

// ── Compliance ────────────────────────────────────────────────────────────────
export async function getComplianceScore(scanId: string): Promise<any> {
  return request(`/api/compliance/score/${scanId}`);
}

export async function getComplianceMapping(): Promise<any> {
  return request('/api/compliance/mapping');
}

// ── Exports ───────────────────────────────────────────────────────────────────
export async function downloadDocx(scanId: string): Promise<Blob> {
  const res = await fetch(`${API_BASE}/api/scans/${scanId}/docx`);
  if (!res.ok) throw new Error('DOCX download mislukt');
  return res.blob();
}

export async function downloadCsv(scanId: string): Promise<Blob> {
  const res = await fetch(`${API_BASE}/api/scans/${scanId}/csv`);
  if (!res.ok) throw new Error('CSV download mislukt');
  return res.blob();
}

// ── Deduplication ─────────────────────────────────────────────────────────────
export async function deduplicateFindings(scanId: string): Promise<any> {
  return request(`/api/scans/${scanId}/deduplicate`, { method: 'POST' });
}

// ── Pause / Resume ────────────────────────────────────────────────────────────
export async function pauseScan(scanId: string): Promise<void> {
  await request(`/api/scan/${scanId}/pause`, { method: 'POST' });
}

export async function resumeScan(scanId: string): Promise<void> {
  await request(`/api/scan/${scanId}/resume`, { method: 'POST' });
}

// ── Threat intelligence ───────────────────────────────────────────────────────
export async function getThreatIntel(cveId: string): Promise<any> {
  return request(`/api/threat-intel/${cveId}`);
}

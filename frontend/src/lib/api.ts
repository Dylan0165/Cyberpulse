import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_BACKEND_URL || "/api",
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (d: any) => api.post("/auth/register", d),
  login: (d: any) => api.post("/auth/login", d),
  logout: () => api.post("/auth/logout"),
  me: () => api.get("/auth/me"),
  completeOnboarding: () => api.post("/auth/complete-onboarding"),
  acceptTerms: (version = "1.0") => api.post("/auth/accept-terms", { version }),
};

// ── Users ─────────────────────────────────────────────────────────────────────
export const usersApi = {
  updateMe: (d: any) => api.patch("/users/me", d),
  regenerateApiKey: () => api.post("/users/me/regenerate-api-key"),
  plan: () => api.get("/users/me/plan"),
};

// ── Billing (Stripe) ───────────────────────────────────────────────────────────
export const billingApi = {
  checkout: (plan: string, interval: string) =>
    api.post("/billing/checkout", { plan, interval }),
  portal: () => api.get("/billing/portal"),
};

// ── Admin ──────────────────────────────────────────────────────────────────────
export const adminApi = {
  stats: () => api.get("/admin/stats"),
  users: (params?: { search?: string; plan?: string; sort?: string }) =>
    api.get("/admin/users", { params }),
  user: (id: string) => api.get(`/admin/users/${id}`),
  createUser: (d: any) => api.post("/admin/users", d),
  updateUser: (id: string, d: any) => api.patch(`/admin/users/${id}`, d),
  deleteUser: (id: string) => api.delete(`/admin/users/${id}`),
  resetPassword: (id: string) => api.post(`/admin/users/${id}/reset-password`),
  suspend: (id: string) => api.post(`/admin/users/${id}/suspend`),
  activate: (id: string) => api.post(`/admin/users/${id}/activate`),
  init: (d: { email: string; password: string; secret: string }) =>
    api.post("/admin/init", d),
};

// API functions
export const targetsApi = {
  list: () => api.get("/targets"),
  get: (id: string) => api.get(`/targets/${id}`),
  create: (data: any) => api.post("/targets", data),
  delete: (id: string) => api.delete(`/targets/${id}`),
  verify: (id: string, method: "dns" | "file" = "dns") =>
    api.post(`/targets/${id}/verify`, { method }),
};

export const scansApi = {
  list: (page = 1, pageSize = 20) =>
    api.get(`/scans?page=${page}&page_size=${pageSize}`),
  get: (id: string) => api.get(`/scans/${id}`),
  create: (data: any) => api.post("/scans", data),
  start: (id: string) => api.post(`/scans/${id}/start`),
  cancel: (id: string) => api.post(`/scans/${id}/cancel`),
  getReport: (id: string) => api.get(`/scans/${id}/report`),
};

export const reportsApi = {
  downloadPdf: (scanId: string) =>
    api.get(`/reports/${scanId}/pdf`, { responseType: "blob" }),
  downloadJson: (scanId: string) =>
    api.get(`/reports/${scanId}/json`, { responseType: "blob" }),
  downloadCsv: (scanId: string) =>
    api.get(`/reports/${scanId}/csv`, { responseType: "blob" }),
  downloadXml: (scanId: string) =>
    api.get(`/reports/${scanId}/xml`, { responseType: "blob" }),
  downloadNis2: (scanId: string) =>
    api.get(`/reports/${scanId}/nis2`, { responseType: "blob" }),
  downloadSecureSolution: (scanId: string) =>
    api.get(`/reports/${scanId}/secure-solution`, { responseType: "blob", timeout: 120000 }),
};

export const toolsApi = {
  available: () => api.get("/tools/available"),
  profiles: () => api.get("/tools/profiles"),
  startScan: (data: { target: string; tools?: string[]; profile?: string; scan_mode?: string }) =>
    api.post("/tools/scan", data),
  streamUrl: (scanId: string) => `/api/tools/scan/${scanId}/stream`,
  check: () => api.get("/tools/available"),
};

export default api;

// Named wrapper used by dashboard pages
export const dashboardApi = {
  listScans: (page = 1, pageSize = 20) =>
    scansApi.list(page, pageSize)
      .then((r) => {
        const d = r.data;
        // Backend returns { scans: [...], total, page, page_size }
        // Normalise to { items: [...], total } so all pages use the same shape.
        return { items: d.scans ?? d.items ?? [], total: d.total ?? 0 };
      })
      .catch(() => ({ items: [], total: 0 })),
  listTargets: () =>
    targetsApi.list().then((r) => r.data).catch(() => []),
};

// ── Assets ────────────────────────────────────────────────────────────────────
export const assetsApi = {
  list: (): Promise<any[]> => api.get('/assets').then(r => r.data).catch(() => []),
};

// ── Schedules ─────────────────────────────────────────────────────────────────
export const schedulesApi = {
  list: (): Promise<any[]> => api.get('/schedule').then(r => r.data).catch(() => []),
  create: (data: any): Promise<any> => api.post('/schedule', data).then(r => r.data),
  remove: (id: string): Promise<void> => api.delete(`/schedule/${id}`).then(() => {}),
  // Backend PATCH /schedule/{id} toggles is_active (no query param needed)
  toggle: (id: string, _enabled?: boolean): Promise<any> =>
    api.patch(`/schedule/${id}`).then(r => r.data),
};

// ── AI Chat ───────────────────────────────────────────────────────────────────
export const chatApi = {
  history: (scanId: string): Promise<any[]> =>
    api.get(`/scans/${scanId}/chat/history`).then(r => r.data).catch(() => []),
  send: (scanId: string, message: string, history?: any[]): Promise<{ answer: string }> =>
    api.post(`/scans/${scanId}/chat`, { message, history }).then(r => r.data),
};

// ── Compliance ────────────────────────────────────────────────────────────────
export const complianceApi = {
  score: (scanId: string): Promise<any> =>
    api.get(`/compliance/score/${scanId}`).then(r => r.data),
  mapping: (): Promise<any> => api.get('/compliance/mapping').then(r => r.data),
};

// ── Compare ───────────────────────────────────────────────────────────────────
export const compareApi = {
  compare: (scanA: string, scanB: string): Promise<any> =>
    api.get(`/scans/compare?scan_a=${scanA}&scan_b=${scanB}`).then(r => r.data),
};

// ── Webhooks ──────────────────────────────────────────────────────────────────
export const webhooksApi = {
  list: (): Promise<any[]> => api.get('/webhooks').then(r => r.data).catch(() => []),
  create: (data: { url: string; events: string[]; enabled?: boolean }): Promise<any> =>
    api.post('/webhooks', data).then(r => r.data),
  remove: (id: string): Promise<void> => api.delete(`/webhooks/${id}`).then(() => {}),
};

// ── API Keys ──────────────────────────────────────────────────────────────────
export const apiKeysApi = {
  list: (): Promise<any[]> => api.get('/keys').then(r => r.data).catch(() => []),
  create: (data: { name: string; scope?: string }): Promise<any> =>
    api.post('/keys', data).then(r => r.data),
  remove: (id: string): Promise<void> => api.delete(`/keys/${id}`).then(() => {}),
};

// ── Audit Log ─────────────────────────────────────────────────────────────────
export const auditApi = {
  list: (limit = 100): Promise<any[]> =>
    api.get(`/audit?limit=${limit}`).then(r => r.data).catch(() => []),
};

// ── Notifications ─────────────────────────────────────────────────────────────
export const notificationsApi = {
  list: (limit = 30): Promise<any[]> =>
    api.get(`/notifications?limit=${limit}`).then(r => r.data).catch(() => []),
  unreadCount: (): Promise<{ count: number }> =>
    api.get('/notifications/unread-count').then(r => r.data).catch(() => ({ count: 0 })),
  markRead: (id: string): Promise<any> =>
    api.post(`/notifications/${id}/read`).then(r => r.data),
  markAllRead: (): Promise<void> => api.post('/notifications/read-all').then(() => {}),
  clear: (): Promise<void> => api.delete('/notifications/all').then(() => {}),
};

// ── Scans (flat array — for new feature pages) ─────────────────────────────────
// The standard scansApi returns axios responses. This helper returns plain arrays.
export const scansListApi = {
  list: (limit = 30): Promise<any[]> =>
    api.get(`/scans?page=1&page_size=${limit}`).then(r => {
      const d = r.data;
      return Array.isArray(d) ? d : (d?.items ?? d?.scans ?? []);
    }).catch(() => []),
};

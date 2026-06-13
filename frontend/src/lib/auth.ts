// Client-side auth helpers. All SSR-safe (guarded on `typeof window`).

const TOKEN_KEY = "cp_token";
const MAX_AGE = 7 * 24 * 3600; // 7 days in seconds

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(t: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(TOKEN_KEY, t);
  } catch {
    /* ignore storage failures */
  }
  document.cookie = `${TOKEN_KEY}=${t}; path=/; max-age=${MAX_AGE}; samesite=lax`;
}

export function clearToken(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore storage failures */
  }
  document.cookie = `${TOKEN_KEY}=; path=/; max-age=0; samesite=lax`;
}

function decodePayload(token: string): any | null {
  try {
    const part = token.split(".")[1];
    if (!part) return null;
    const base64 = part.replace(/-/g, "+").replace(/_/g, "/");
    const json = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    return JSON.parse(json);
  } catch {
    return null;
  }
}

export function isAuthenticated(): boolean {
  if (typeof window === "undefined") return false;
  const token = getToken();
  if (!token) return false;
  const payload = decodePayload(token);
  if (!payload) return true; // decode failed → treat presence as authenticated
  if (typeof payload.exp === "number") {
    return payload.exp * 1000 > Date.now();
  }
  return true;
}

export function decodeUser(): { sub?: string; email?: string } | null {
  if (typeof window === "undefined") return null;
  const token = getToken();
  if (!token) return null;
  const payload = decodePayload(token);
  if (!payload) return null;
  return { sub: payload.sub, email: payload.email };
}

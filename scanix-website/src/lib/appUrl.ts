// Base URL of the Scanix app (dashboard + API), used by marketing-site CTAs.
// Domain-free default for test/netlab (nginx on the IP); set
// NEXT_PUBLIC_APP_API_URL to https://app.scanix.nl in production.
export const APP_URL = (process.env.NEXT_PUBLIC_APP_API_URL || "http://192.168.121.40").replace(/\/$/, "");

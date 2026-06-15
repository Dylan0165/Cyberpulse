import createMiddleware from "next-intl/middleware";
import { locales, defaultLocale } from "./lib/i18n";

export default createMiddleware({
  locales,
  defaultLocale,
  // nl at the root (scanix.nl/), other languages prefixed (/en, /fr, /de)
  localePrefix: "as-needed",
});

export const config = {
  matcher: ["/((?!api|_next|_vercel|.*\\..*).*)"],
};

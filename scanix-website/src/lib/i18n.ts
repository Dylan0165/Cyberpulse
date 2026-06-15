import { getRequestConfig } from "next-intl/server";

export const locales = ["nl", "en", "fr", "de"] as const;
export const defaultLocale = "nl";
export type Locale = (typeof locales)[number];

export default getRequestConfig(async ({ requestLocale }) => {
  let locale = await requestLocale;

  if (!locale || !locales.includes(locale as Locale)) {
    locale = defaultLocale;
  }

  return {
    locale,
    messages: (await import(`../../messages/${locale}.json`)).default,
  };
});

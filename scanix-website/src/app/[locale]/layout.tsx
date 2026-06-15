import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getMessages, getTranslations, setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";
import { Space_Grotesk, Inter } from "next/font/google";
import { locales, type Locale } from "@/lib/i18n";
import "../globals.css";

const display = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

const body = Inter({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
});

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

const PATHS: Record<Locale, string> = {
  nl: "/",
  en: "/en",
  fr: "/fr",
  de: "/de",
};

export async function generateMetadata({
  params: { locale },
}: {
  params: { locale: string };
}): Promise<Metadata> {
  const t = await getTranslations({ locale, namespace: "meta" });
  return {
    metadataBase: new URL("https://scanix.nl"),
    title: t("title"),
    description: t("description"),
    alternates: {
      canonical: PATHS[locale as Locale] ?? "/",
      languages: {
        nl: "/",
        en: "/en",
        fr: "/fr",
        de: "/de",
        "x-default": "/",
      },
    },
    openGraph: {
      title: t("title"),
      description: t("description"),
      type: "website",
      locale,
    },
  };
}

export default async function LocaleLayout({
  children,
  params: { locale },
}: {
  children: React.ReactNode;
  params: { locale: string };
}) {
  if (!locales.includes(locale as Locale)) notFound();
  setRequestLocale(locale);
  const messages = await getMessages();

  return (
    <html lang={locale} className={`${display.variable} ${body.variable}`}>
      <body className="bg-bg font-body text-ink antialiased">
        <NextIntlClientProvider messages={messages}>
          <div className="grid-bg" aria-hidden />
          <div className="relative z-10">{children}</div>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}

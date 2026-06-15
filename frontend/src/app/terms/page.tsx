import Link from "next/link";
import { ShieldCheck, ArrowLeft } from "lucide-react";

export const metadata = {
  title: "Gebruiksvoorwaarden — Scanix",
};

const SECTIONS: { title: string; body?: string; intro?: string; bullets?: string[] }[] = [
  {
    title: "1. TOEGESTAAN GEBRUIK",
    body:
      "Scanix mag uitsluitend worden gebruikt voor het testen van systemen waarvan u aantoonbaar eigenaar bent of waarvoor u schriftelijke toestemming heeft ontvangen van de eigenaar.",
  },
  {
    title: "2. VERBODEN GEBRUIK",
    intro: "Het is strikt verboden om Scanix te gebruiken voor:",
    bullets: [
      "Het testen van systemen zonder toestemming van de eigenaar",
      "Het verstoren of beschadigen van systemen",
      "Het verkrijgen van ongeautoriseerde toegang",
      "Activiteiten die in strijd zijn met Nederlandse of Europese wet- en regelgeving",
    ],
  },
  {
    title: "3. AANSPRAKELIJKHEID",
    body:
      "Scanix en haar ontwikkelaars zijn niet aansprakelijk voor schade die voortvloeit uit het gebruik van het platform. De gebruiker is volledig verantwoordelijk voor alle acties die worden uitgevoerd via het platform.",
  },
  {
    title: "4. EIGENDOMSVERIFICATIE",
    body:
      "Voor het uitvoeren van scans dient u eigendom of toestemming te kunnen aantonen. Scanix behoudt zich het recht voor om accounts te blokkeren bij vermoedens van misbruik.",
  },
  {
    title: "5. GEGEVENSVERWERKING",
    body:
      "Scanresultaten worden opgeslagen op beveiligde servers binnen de Europese Unie. Gegevens worden na 90 dagen automatisch verwijderd tenzij anders overeengekomen.",
  },
  {
    title: "6. TOEPASSELIJK RECHT",
    body:
      "Op deze voorwaarden is Nederlands recht van toepassing. Geschillen worden voorgelegd aan de bevoegde rechter in Nederland.",
  },
];

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-app px-6 py-10 text-ink">
      <div className="mx-auto max-w-3xl">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between gap-4 border-b border-grid pb-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-cyan/40 bg-cyan/10 shadow-glow-cyan">
              <ShieldCheck className="h-5 w-5 text-cyan" />
            </div>
            <span className="font-display text-xl font-bold tracking-[0.04em] text-cyan">
              Scanix
            </span>
          </div>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 rounded-lg border border-grid bg-card2 px-4 py-2 text-[12px] font-medium text-ink-muted transition-colors hover:border-cyan/40 hover:text-ink"
          >
            <ArrowLeft className="h-4 w-4" />
            Terug naar dashboard
          </Link>
        </div>

        {/* Title */}
        <div className="mb-10">
          <h1 className="font-display text-3xl font-bold tracking-[0.01em] text-ink">
            Gebruiksvoorwaarden Scanix
          </h1>
          <p className="mt-2 font-mono text-[12px] uppercase tracking-[0.12em] text-ink-muted">
            Versie 1.0 — Juni 2026
          </p>
        </div>

        {/* Document */}
        <div className="rounded-lg border border-grid bg-panel p-8">
          <div className="space-y-8">
            {SECTIONS.map((section) => (
              <section key={section.title}>
                <h2 className="font-display text-[15px] font-semibold tracking-[0.06em] text-cyan">
                  {section.title}
                </h2>
                {section.body && (
                  <p className="mt-3 text-[14px] leading-relaxed text-ink-muted">
                    {section.body}
                  </p>
                )}
                {section.intro && (
                  <p className="mt-3 text-[14px] leading-relaxed text-ink-muted">
                    {section.intro}
                  </p>
                )}
                {section.bullets && (
                  <ul className="mt-3 space-y-2">
                    {section.bullets.map((b) => (
                      <li
                        key={b}
                        className="flex items-start gap-2.5 text-[14px] leading-relaxed text-ink-muted"
                      >
                        <span className="mt-2 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-cyan" />
                        <span>{b}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            ))}
          </div>

          <div className="mt-10 border-t border-grid pt-6">
            <p className="text-[13px] italic leading-relaxed text-ink">
              Door gebruik te maken van Scanix gaat u akkoord met deze voorwaarden.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

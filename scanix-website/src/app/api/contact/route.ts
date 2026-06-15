import { NextResponse } from "next/server";

export const runtime = "nodejs";

const RECIPIENT = "info@scanix.nl";

type ContactBody = {
  name?: string;
  company?: string;
  email?: string;
  phone?: string;
  target?: string;
  message?: string;
};

export async function POST(request: Request) {
  let body: ContactBody;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ ok: false, error: "invalid_json" }, { status: 400 });
  }

  const { name, company, email, target } = body;
  if (!name || !company || !email || !target) {
    return NextResponse.json({ ok: false, error: "missing_fields" }, { status: 422 });
  }

  const lines = [
    `Nieuwe scan-aanvraag voor ${RECIPIENT}`,
    `Naam:      ${name}`,
    `Bedrijf:   ${company}`,
    `E-mail:    ${email}`,
    `Telefoon:  ${body.phone || "-"}`,
    `Systeem:   ${target}`,
    `Bericht:   ${body.message || "-"}`,
  ].join("\n");

  // Always log server-side so submissions are never lost.
  console.log("[contact]\n" + lines);

  // Optional delivery: set CONTACT_WEBHOOK_URL (e.g. an email API / Make / Zapier
  // hook) to actually forward the lead. Wire SMTP/nodemailer here if preferred.
  const webhook = process.env.CONTACT_WEBHOOK_URL;
  if (webhook) {
    try {
      await fetch(webhook, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ to: RECIPIENT, subject: `Scanix scan-aanvraag — ${company}`, text: lines, lead: body }),
      });
    } catch (err) {
      // Don't fail the user's submission if the webhook is down — it's logged above.
      console.error("[contact] webhook forward failed:", err);
    }
  }

  return NextResponse.json({ ok: true });
}

import { createTransport, type Transporter } from "nodemailer";
import { config } from "./config.js";
import type { Opportunity } from "./scraper.js";

let transporter: Transporter | null = null;

function getTransporter(): Transporter | null {
  if (!config.smtp.host) return null;
  transporter ??= createTransport({
    host: config.smtp.host,
    port: config.smtp.port,
    secure: config.smtp.port === 465,
    auth: config.smtp.user ? { user: config.smtp.user, pass: config.smtp.pass } : undefined,
  });
  return transporter;
}

export async function sendOpportunityMail(o: Opportunity): Promise<void> {
  const subject = `Nuova opportunita Kode: ${o.title}`;
  const text = `${o.title}\n${o.url}\n`;
  const t = getTransporter();
  if (!t) {
    console.log(
      `[dry-run] SMTP non configurato, email non inviata. A: ${config.mailTo || "(MAIL_TO non impostato)"} | Oggetto: ${subject} | ${text}`,
    );
    return;
  }
  if (!config.mailTo || !config.mailFrom) {
    throw new Error("MAIL_TO e MAIL_FROM sono richiesti per inviare email");
  }
  await t.sendMail({ from: config.mailFrom, to: config.mailTo, subject, text });
  console.log(`Email inviata a ${config.mailTo}: ${subject}`);
}

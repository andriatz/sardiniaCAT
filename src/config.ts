import dotenv from "dotenv";

dotenv.config();

export const config = {
  port: Number(process.env.PORT ?? 3000),
  host: process.env.HOST ?? "127.0.0.1",
  mistralApiKey: process.env.MISTRAL_API_KEY ?? "",
  mistralModel: process.env.MISTRAL_MODEL ?? "mistral-small-latest",
  enableScraper: (process.env.ENABLE_SCRAPER ?? "false") === "true",
  opportunitiesUrl: process.env.OPPORTUNITIES_URL ?? "",
  opportunitiesFilter: process.env.OPPORTUNITIES_FILTER ?? "",
  pollMinutes: Number(process.env.POLL_MINUTES ?? 60),
  runOnStart: (process.env.RUN_ON_START ?? "false") === "true",
  stateFile: process.env.STATE_FILE ?? "data/seen.json",
  smtp: {
    host: process.env.SMTP_HOST ?? "",
    port: Number(process.env.SMTP_PORT ?? 587),
    user: process.env.SMTP_USER ?? "",
    pass: process.env.SMTP_PASS ?? "",
  },
  mailFrom: process.env.MAIL_FROM ?? "",
  mailTo: process.env.MAIL_TO ?? "",
};

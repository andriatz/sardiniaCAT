import { config } from "./config.js";
import { findNewOpportunities, markSeen } from "./scraper.js";
import { sendOpportunityMail } from "./mailer.js";

export async function runOnce(): Promise<number> {
  const { fresh, state } = await findNewOpportunities();
  if (fresh.length === 0) {
    console.log(`[${new Date().toISOString()}] Nessuna nuova opportunita.`);
    return 0;
  }
  console.log(`[${new Date().toISOString()}] ${fresh.length} nuova/e opportunita:`);
  for (const o of fresh) {
    console.log(` - ${o.title} (${o.url})`);
    await sendOpportunityMail(o);
  }
  await markSeen(fresh, state);
  return fresh.length;
}

export function startScheduler(): void {
  const everyMs = Math.max(1, config.pollMinutes) * 60_000;
  console.log(
    `Watcher attivo su ${config.opportunitiesUrl || "(OPPORTUNITIES_URL non impostata)"} ogni ${config.pollMinutes} min.`,
  );
  if (config.runOnStart) {
    void runOnce().catch((e) => console.error("Errore watcher:", e));
  }
  setInterval(() => {
    void runOnce().catch((e) => console.error("Errore watcher:", e));
  }, everyMs);
}

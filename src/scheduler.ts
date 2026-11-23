import { config } from "./config.js";
import { findNewOpportunities, markSeen, type Opportunity } from "./scraper.js";
import { sendOpportunityMail } from "./mailer.js";

export async function runOnce(): Promise<number> {
  const { fresh, state } = await findNewOpportunities();
  if (fresh.length === 0) {
    console.log(`[${new Date().toISOString()}] Nessuna nuova opportunita.`);
    return 0;
  }
  console.log(`[${new Date().toISOString()}] ${fresh.length} nuova/e opportunita:`);
  const sent: Opportunity[] = [];
  for (const o of fresh) {
    console.log(` - ${o.title} (${o.url})`);
    if (await sendOpportunityMail(o)) sent.push(o);
  }
  if (sent.length > 0) {
    await markSeen(sent, state);
  } else {
    console.log("Dry-run: nessuna email inviata davvero, opportunita non marcate come viste.");
  }
  return sent.length;
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

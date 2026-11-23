import express from "express";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { config } from "./config.js";
import { chatComplete, type ChatMessageInput } from "./chat.js";
import { startScheduler } from "./scheduler.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const publicDir = path.join(here, "..", "public");

const app = express();
app.use(express.json({ limit: "256kb" }));
app.use(express.static(publicDir));

app.get("/api/health", (_req, res) => {
  res.json({ ok: true, model: config.mistralModel, scraper: config.enableScraper });
});

const ROLES = new Set(["system", "user", "assistant"]);

app.post("/api/chat", async (req, res) => {
  const messages = req.body?.messages;
  if (!Array.isArray(messages) || messages.length === 0) {
    return res.status(400).json({ error: "Body atteso: { messages: [{ role, content }] }" });
  }
  const cleaned: ChatMessageInput[] = [];
  for (const m of messages) {
    if (typeof m?.content !== "string" || typeof m?.role !== "string" || !ROLES.has(m.role)) {
      return res.status(400).json({
        error: "Ogni messaggio deve avere role (system|user|assistant) e content (string)",
      });
    }
    cleaned.push({ role: m.role as ChatMessageInput["role"], content: m.content });
  }
  try {
    const reply = await chatComplete(cleaned);
    res.json({ reply });
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Errore sconosciuto";
    const status = /MISTRAL_API_KEY/.test(msg) ? 500 : 502;
    res.status(status).json({ error: msg });
  }
});

app.listen(config.port, config.host, () => {
  console.log(`Server in ascolto su http://${config.host}:${config.port}`);
  if (config.enableScraper) {
    startScheduler();
  }
});

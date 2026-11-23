import * as cheerio from "cheerio";
import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { config } from "./config.js";

export interface Opportunity {
  title: string;
  url: string;
}

interface SeenState {
  seen: string[];
}

function keyOf(o: Opportunity): string {
  return createHash("sha256").update(`${o.url}|${o.title}`).digest("hex");
}

async function loadState(): Promise<SeenState> {
  try {
    const raw = await readFile(config.stateFile, "utf8");
    return JSON.parse(raw) as SeenState;
  } catch {
    return { seen: [] };
  }
}

async function saveState(state: SeenState): Promise<void> {
  await mkdir(path.dirname(config.stateFile), { recursive: true });
  await writeFile(config.stateFile, JSON.stringify(state, null, 2), "utf8");
}

function extractFromHtml(html: string, baseUrl: string): Opportunity[] {
  const $ = cheerio.load(html);
  const out: Opportunity[] = [];
  const seenUrls = new Set<string>();
  $("a[href]").each((_i, el) => {
    const href = $(el).attr("href") ?? "";
    const title = $(el).text().replace(/\s+/g, " ").trim();
    if (!href || !title) return;
    let url: string;
    try {
      url = new URL(href, baseUrl).toString();
    } catch {
      return;
    }
    if (config.opportunitiesFilter && !url.toLowerCase().includes(config.opportunitiesFilter.toLowerCase())) {
      return;
    }
    if (seenUrls.has(url)) return;
    seenUrls.add(url);
    out.push({ title, url });
  });
  return out;
}

function extractFromJson(raw: string): Opportunity[] {
  const data = JSON.parse(raw) as unknown;
  const items: Record<string, unknown>[] = Array.isArray(data)
    ? (data as Record<string, unknown>[])
    : Array.isArray((data as { jobs?: unknown[] })?.jobs)
      ? ((data as { jobs: Record<string, unknown>[] }).jobs)
      : [];
  const out: Opportunity[] = [];
  for (const it of items) {
    const title = String(it.title ?? it.name ?? "").trim();
    const rawUrl = String(it.url ?? it.href ?? it.link ?? it.absolute_url ?? it.hostedUrl ?? "").trim();
    if (!title || !rawUrl) continue;
    try {
      out.push({ title, url: new URL(rawUrl, config.opportunitiesUrl).toString() });
    } catch {
      continue;
    }
  }
  return out;
}

export async function fetchOpportunities(): Promise<Opportunity[]> {
  if (!config.opportunitiesUrl) {
    throw new Error("OPPORTUNITIES_URL non configurata (impostala in .env)");
  }
  const res = await fetch(config.opportunitiesUrl, {
    headers: {
      "User-Agent": "kode-opportunita-watch/1.0",
      Accept: "text/html,application/json",
    },
  });
  if (!res.ok) {
    throw new Error(`Fetch fallito: HTTP ${res.status} per ${config.opportunitiesUrl}`);
  }
  const body = await res.text();
  const type = res.headers.get("content-type") ?? "";
  const trimmed = body.trimStart();
  if (type.includes("json") || trimmed.startsWith("{") || trimmed.startsWith("[")) {
    return extractFromJson(body);
  }
  return extractFromHtml(body, config.opportunitiesUrl);
}

export async function findNewOpportunities(): Promise<{ fresh: Opportunity[]; state: SeenState }> {
  const state = await loadState();
  const all = await fetchOpportunities();
  const fresh = all.filter((o) => !state.seen.includes(keyOf(o)));
  return { fresh, state };
}

export async function markSeen(fresh: Opportunity[], state: SeenState): Promise<void> {
  const keys = new Set(state.seen);
  for (const o of fresh) keys.add(keyOf(o));
  await saveState({ seen: [...keys] });
}

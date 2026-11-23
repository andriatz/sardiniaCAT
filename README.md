# Kode Opportunities Watch + Chat Mistral

App web minima in Node.js + TypeScript con due funzioni:

1. **Chat** — interfaccia web semplice che chiama l'API Mistral con l'SDK ufficiale
   `@mistralai/mistralai`, modello `mistral-small-latest`.
2. **Watcher opportunità** — controlla periodicamente una pagina pubblica di opportunità
   Kode e invia **una email al tuo indirizzo** per ogni nuova opportunità trovata.

`MISTRAL_API_KEY` e le credenziali SMTP vivono **solo sul server** (`.env`, mai nel client;
il browser parla solo con `POST /api/chat`).

## Requisiti

- Node.js >= 20 (usa `fetch` globale, nessuna build frontend)

## Installazione

```bash
npm install
```

## Configurazione

```bash
cp .env.example .env
```

Compila `.env`:

| Variabile | Descrizione |
|---|---|
| `MISTRAL_API_KEY` | chiave API Mistral (server only) |
| `MISTRAL_MODEL` | default `mistral-small-latest` |
| `PORT` / `HOST` | default `3000` / `127.0.0.1` |
| `ENABLE_SCRAPER` | `true` per attivare il watcher all'avvio del server |
| `OPPORTUNITIES_URL` | pagina pubblica delle opportunità Kode (HTML o JSON, es. board Greenhouse/Lever) |
| `OPPORTUNITIES_FILTER` | opzionale: tieni solo link il cui URL contiene questa stringa (es. `/job`) |
| `POLL_MINUTES` | intervallo tra i controlli (default 60) |
| `RUN_ON_START` | default `true`: primo controllo immediato all'avvio, poi ogni `POLL_MINUTES` |
| `STATE_FILE` | file con le opportunità già viste (default `data/seen.json`) |
| `SMTP_HOST/PORT/USER/PASS`, `MAIL_FROM`, `MAIL_TO` | invio email. Senza `SMTP_HOST` le email sono solo stampate a log (dry-run) e **non** vengono marcate come viste: configurando SMTP in seguito partono davvero |

## Esecuzione locale

```bash
npm run dev        # sviluppo con hot reload -> http://127.0.0.1:3000
```

Produzione:

```bash
npm run build
npm start          # serve dist/ -> http://127.0.0.1:3000
```

Test puntuale del watcher (senza avviare il server, utile per verificare URL/filtro/email):

```bash
npm run scrape:once
```

## Struttura

```
src/server.ts       Express: static UI + POST /api/chat + avvio watcher
src/chat.ts         SDK @mistralai/mistralai, modello mistral-small-latest
src/scraper.ts      fetch pagina, estrazione link/JSON, dedupe su hash
src/mailer.ts       invio email via SMTP (nodemailer), dry-run se non configurato
src/scheduler.ts    poll periodico + una email per ogni nuova opportunità
src/scrape-once.ts  esecuzione singola del controllo (npm run scrape:once)
public/index.html   UI chat minimale (vanilla JS)
```

## Note

- Lo scraper legge solo pagine **pubbliche**: rispetta `robots.txt` e i Termini di Servizio
  del sito e tieni `POLL_MINUTES` ragionevole (consigliato >= 15). Preferisci API/JSON
  ufficiali della job board quando disponibili.
- Le opportunità già notificate sono salvate in `data/seen.json`: niente email duplicate.
- `.env` è in `.gitignore`: non committare mai chiavi.

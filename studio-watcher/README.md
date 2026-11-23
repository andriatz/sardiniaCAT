# kode-studio-watcher (Mistral Studio)

Progetto [Mistral Workflows](https://docs.mistral.ai/studio/workflows/) dentro `sardiniaCAT`,
deployato come **managed deployment** nel workspace Studio dell'organizzazione Kode.

## Workflow inclusi

| Workflow | Cosa fa | Input principale |
|---|---|---|
| `kode-opportunities-watch` | Legge le opportunità recenti dal portale EU Funding & Tenders (SEARCH API pubblica, apiKey `SEDIA`, filtro Horizon Europe come il digest partner-search) e **manda una email via connettore gmail per ogni nuova opportunità** | `{ "mode": "once" \| "watch", "interval_minutes": 60, "days_lookback": 2, "max_items": 50, "recipient": "a.zedda@kode-solutions.net", "dry_run": false }` |
| `kode-chat` | Chat con `mistral-small-latest` tramite il plugin Mistral del worker (nessuna API key nel codice) | `{ "message": "..." }` oppure `{ "messages": [...] }` |

- `mode: "once"` = un controllo e termina (utile per testare). `mode: "watch"` = resta in
esecuzione e ricontrolla ogni `interval_minutes` (stato di dedupe in memoria: ogni opportunità
viene notificata una sola volta per esecuzione).
- I workflow sono `on_behalf_of=True`: girano con l'identità dell'utente che li avvia, quindi
  il connettore gmail usa il suo OAuth (già configurato). **Le run schedulate via cron non hanno
  un utente**: per quelle servono credenziali workspace; qui l'automazione continua è l'esecuzione
  `watch` long-running, visibile in Studio → Executions.

## Test locali

```bash
cd studio-watcher
uv sync --all-packages
uv run --all-packages python -m pytest apps/worker/tests -q
```

## Deploy (già fatto via MCP)

Deployment managed `kode-watch` (hardened, OBO) che builda il commit pushato di questo repo,
`build_directory=studio-watcher`, `dockerfile=deploy/docker/Dockerfile.worker`.
Avvio esecuzioni: `mistral_mcp_execute_workflow` con `workflow_identifier` e input JSON.

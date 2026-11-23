"""Kode — watcher opportunità (EU Funding & Tenders Portal) con notifica email via connettore gmail.

Fonte: SEARCH API pubblica del portale (apiKey pubblica SEDIA), stessi filtri Horizon Europe
dei partner search announcements usati dal digest. Ogni nuova opportunità (mai vista in questa
esecuzione) genera una email al recipient tramite il connettore gmail dell'utente (OBO).
"""

import json
from datetime import UTC, timedelta
from typing import Any, Literal

import pydantic
from mistralai import workflows
from mistralai.workflows import Depends
from mistralai.workflows.plugins.mistralai.connectors import (
    ToolCallClient,
    connector,
    uses_connectors,
)

SEARCH_API = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
API_KEY = "SEDIA"
HORIZON_EUROPE = "43108390"
PORTAL_URL = "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search"
PAGE_SIZE = 50
DEFAULT_RECIPIENT = "a.zedda@kode-solutions.net"

gmail_connector = connector("gmail", auto_auth=False)


class WatchInput(pydantic.BaseModel):
    mode: Literal["once", "watch"] = "once"
    interval_minutes: int = 60
    days_lookback: int = 2
    max_items: int = 50
    recipient: str = DEFAULT_RECIPIENT
    dry_run: bool = False


class Opportunity(pydantic.BaseModel):
    key: str
    title: str
    url: str
    last_modified: str = ""


def _search_body(page: int) -> dict:
    query = {
        "bool": {
            "must": [
                {"term": {"frameworkProgramme": HORIZON_EUROPE}},
                {"terms": {"type": ["ORGANISATION", "PERSON"]}},
            ]
        }
    }
    return {
        "sort": json.dumps({"order": "DESC", "field": "lastModified"}),
        "query": json.dumps(query),
        "languages": json.dumps(["en"]),
        "displayFields": json.dumps([
            "type", "identifier", "reference", "title", "status", "country",
            "description", "lastModified", "deadlineDate", "frameworkProgramme", "keywords",
        ]),
        "pageNumber": str(page),
        "pageSize": str(PAGE_SIZE),
    }


def _extract_docs(body: Any) -> list:
    if isinstance(body, dict):
        for key in ("results", "items", "documents", "docs", "data"):
            value = body.get(key)
            if isinstance(value, list):
                return value
        for key in ("response", "result"):
            nested = body.get(key)
            if isinstance(nested, dict):
                sub = _extract_docs(nested)
                if sub:
                    return sub
    return []


def _to_opportunity(doc: dict) -> Opportunity:
    title = str(doc.get("title") or doc.get("name") or "Senza titolo")
    reference = str(doc.get("reference") or doc.get("identifier") or "")
    url = str(doc.get("url") or "").strip() or (
        f"{PORTAL_URL}?reference={reference}" if reference else PORTAL_URL
    )
    key = reference or f"{title}|{doc.get('lastModified', '')}"
    return Opportunity(
        key=key, title=title, url=url, last_modified=str(doc.get("lastModified") or "")
    )


@workflows.activity(name="fetch-opportunities", start_to_close_timeout=timedelta(seconds=180))
async def fetch_opportunities(days_lookback: int, max_items: int) -> list[dict]:
    from datetime import datetime

    import httpx

    cutoff = datetime.now(UTC) - timedelta(days=days_lookback)
    items: list[dict] = []
    async with httpx.AsyncClient(timeout=60) as client:
        for page in range(1, 21):
            r = await client.post(
                SEARCH_API,
                params={"apiKey": API_KEY, "text": "***", "pageSize": PAGE_SIZE, "pageNumber": page},
                data=_search_body(page),
            )
            r.raise_for_status()
            docs = _extract_docs(r.json())
            if not docs:
                break
            for doc in docs:
                last_modified = str(doc.get("lastModified") or "")
                try:
                    ts = datetime.fromisoformat(last_modified.replace("Z", "+00:00"))
                except Exception:
                    items.append(doc)
                    continue
                if ts >= cutoff:
                    items.append(doc)
            if len(items) >= max_items:
                break
    return [_to_opportunity(d).model_dump() for d in items[:max_items]]


@workflows.activity(name="send-opportunity-email", start_to_close_timeout=timedelta(seconds=60))
async def send_opportunity_email(
    to: str,
    subject: str,
    body: str,
    gmail: ToolCallClient = Depends(gmail_connector),
) -> dict:
    return await gmail.call_tool(
        tool_name="send_email",
        arguments={"to": [to], "subject": subject, "body": body},
    )


@workflows.workflow.define(name="kode-opportunities-watch", on_behalf_of=True)
@uses_connectors(gmail_connector)
class KodeOpportunitiesWatch:
    def __init__(self) -> None:
        self.seen: set[str] = set()

    @workflows.workflow.entrypoint
    async def run(self, data: WatchInput) -> dict:
        while True:
            fetched = await fetch_opportunities(data.days_lookback, data.max_items)
            fresh = [op for op in fetched if op["key"] not in self.seen]
            sent = 0
            for op in fresh:
                if not data.dry_run:
                    await send_opportunity_email(
                        to=data.recipient,
                        subject=f"Nuova opportunita Kode: {op['title']}",
                        body=(
                            f"{op['title']}\n{op['url']}\n"
                            f"ultimo aggiornamento: {op.get('last_modified', '')}"
                        ),
                    )
                    self.seen.add(op["key"])
                sent += 1
            summary = {
                "fetched": len(fetched),
                "new": len(fresh),
                "notified": 0 if data.dry_run else sent,
                "dry_run": data.dry_run,
                "mode": data.mode,
            }
            if data.mode == "once":
                return summary
            await workflows.workflow.sleep(data.interval_minutes * 60)

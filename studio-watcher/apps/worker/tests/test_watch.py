import asyncio
from datetime import timedelta

import worker.workflows.opportunities_watch as ow
from mistralai import workflows
from mistralai.workflows.testing import create_test_worker
from worker.workflows.opportunities_watch import (
    KodeOpportunitiesWatch,
    _extract_docs,
    _to_opportunity,
)

WORKFLOW_EXECUTION_TIMEOUT = timedelta(seconds=10)

FAKE = [
    {"key": "REF-1", "title": "Partner search A", "url": "https://example.org/a", "last_modified": "2026-11-20T00:00:00Z"},
    {"key": "REF-2", "title": "Partner search B", "url": "https://example.org/b", "last_modified": "2026-11-21T00:00:00Z"},
]


@workflows.activity(name="fetch-opportunities")
async def mock_fetch(days_lookback: int, max_items: int) -> list[dict]:
    return FAKE


sent_calls: list[dict] = []


@workflows.activity(name="send-opportunity-email")
async def mock_send(to: str, subject: str, body: str) -> dict:
    sent_calls.append({"to": to, "subject": subject, "body": body})
    return {"id": "mock"}


async def _run_once(temporal_env, monkeypatch, input_data: dict, run_id: str) -> dict:
    monkeypatch.setattr(ow, "fetch_opportunities", mock_fetch)
    monkeypatch.setattr(ow, "send_opportunity_email", mock_send)
    async with create_test_worker(
        temporal_env,
        workflows=[KodeOpportunitiesWatch],
        activities=[mock_fetch, mock_send],
    ):
        handle = await temporal_env.client.start_workflow(
            "kode-opportunities-watch",
            input_data,
            id=run_id,
            task_queue="test-task-queue",
            execution_timeout=WORKFLOW_EXECUTION_TIMEOUT,
        )
        raw = await asyncio.wait_for(handle.result(), timeout=15)
        return raw["result"] if isinstance(raw, dict) and "result" in raw else raw


async def test_once_mode_notifies_each_new_opportunity(temporal_env, monkeypatch) -> None:
    sent_calls.clear()
    result = await _run_once(temporal_env, monkeypatch, {"mode": "once", "days_lookback": 1, "recipient": "a@b.c"}, "t-once")
    assert result["new"] == 2
    assert result["notified"] == 2
    assert len(sent_calls) == 2
    assert all(c["to"] == "a@b.c" for c in sent_calls)


async def test_once_mode_dry_run_sends_nothing(temporal_env, monkeypatch) -> None:
    sent_calls.clear()
    result = await _run_once(temporal_env, monkeypatch, {"mode": "once", "dry_run": True}, "t-dry")
    assert result["new"] == 2
    assert result["notified"] == 0
    assert sent_calls == []


def test_extract_docs_and_to_opportunity() -> None:
    docs = _extract_docs({"results": [{"title": "X", "reference": "REF-9"}]})
    assert len(docs) == 1
    op = _to_opportunity({"title": "X", "reference": "REF-9", "lastModified": "2026-11-20"})
    assert op.key == "REF-9"
    assert "REF-9" in op.url

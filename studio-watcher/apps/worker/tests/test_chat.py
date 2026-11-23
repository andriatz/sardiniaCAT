import asyncio
from datetime import timedelta

import worker.workflows.kode_chat as kc
from mistralai.workflows.testing import create_test_worker
from worker.workflows.kode_chat import KodeChat

WORKFLOW_EXECUTION_TIMEOUT = timedelta(seconds=10)


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


class _FakeChat:
    async def complete_async(self, model: str, messages: list[dict]) -> _FakeResponse:
        return _FakeResponse(f"mock-reply[{model}]:{messages[-1]['content']}")


class _FakeClient:
    def __init__(self) -> None:
        self.chat = _FakeChat()


async def _run(temporal_env, monkeypatch, input_data: dict, run_id: str) -> dict:
    monkeypatch.setattr(kc, "get_mistral_client", lambda *a, **k: _FakeClient())
    async with create_test_worker(
        temporal_env,
        workflows=[KodeChat],
        activities=[kc.chat_complete],
    ):
        handle = await temporal_env.client.start_workflow(
            "kode-chat",
            input_data,
            id=run_id,
            task_queue="test-task-queue",
            execution_timeout=WORKFLOW_EXECUTION_TIMEOUT,
        )
        raw = await asyncio.wait_for(handle.result(), timeout=15)
        return raw["result"] if isinstance(raw, dict) and "result" in raw else raw


async def test_chat_returns_reply(temporal_env, monkeypatch) -> None:
    result = await _run(temporal_env, monkeypatch, {"message": "ciao"}, "c1")
    assert result["model"] == "mistral-small-latest"
    assert result["reply"] == "mock-reply[mistral-small-latest]:ciao"
    assert result["messages"][-1]["role"] == "assistant"


async def test_chat_requires_a_message(temporal_env, monkeypatch) -> None:
    result = await _run(temporal_env, monkeypatch, {}, "c2")
    assert "error" in result

"""Chat con il modello mistral-small-latest tramite il plugin Mistral del worker.

Visibile in Studio come workflow `kode-chat`: input `{"message": "..."}` (oppure `messages`
con la cronologia completa), output `{"reply": "..."}`. OBO: usa l'identità dell'utente che
avvia l'esecuzione, nessuna API key nel codice.
"""

from datetime import timedelta

import pydantic
from mistralai import workflows
from mistralai.workflows.plugins.mistralai import get_mistral_client


class ChatInput(pydantic.BaseModel):
    message: str = ""
    messages: list[dict] = pydantic.Field(default_factory=list)
    model: str = "mistral-small-latest"


@workflows.activity(name="chat-complete", start_to_close_timeout=timedelta(seconds=120))
async def chat_complete(model: str, messages: list[dict]) -> str:
    client = get_mistral_client()
    resp = await client.chat.complete_async(model=model, messages=messages)
    content = resp.choices[0].message.content
    if isinstance(content, str):
        return content
    return "".join(getattr(part, "text", "") for part in content)


@workflows.workflow.define(name="kode-chat", on_behalf_of=True)
class KodeChat:
    @workflows.workflow.entrypoint
    async def run(self, data: ChatInput) -> dict:
        messages = [dict(m) for m in data.messages]
        if data.message:
            messages.append({"role": "user", "content": data.message})
        if not messages:
            return {"error": "passa 'message' oppure 'messages'"}
        reply = await chat_complete(data.model, messages)
        messages.append({"role": "assistant", "content": reply})
        return {"model": data.model, "reply": reply, "messages": messages}

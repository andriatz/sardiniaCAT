import { Mistral } from "@mistralai/mistralai";
import { config } from "./config.js";

export type ChatRole = "system" | "user" | "assistant";

export interface ChatMessageInput {
  role: ChatRole;
  content: string;
}

let client: Mistral | null = null;

function getClient(): Mistral {
  if (!config.mistralApiKey) {
    throw new Error("MISTRAL_API_KEY non configurata sul server (impostala in .env)");
  }
  client ??= new Mistral({ apiKey: config.mistralApiKey });
  return client;
}

function contentToString(content: unknown): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .map((part) => {
        if (typeof part === "string") return part;
        if (part && typeof part === "object" && "text" in part) {
          return String((part as { text?: unknown }).text ?? "");
        }
        return "";
      })
      .join("");
  }
  return String(content ?? "");
}

export async function chatComplete(messages: ChatMessageInput[]): Promise<string> {
  const res = await getClient().chat.complete({
    model: config.mistralModel,
    messages: messages.map((m) => ({ role: m.role, content: m.content })),
  });
  const choice = res.choices?.[0];
  if (!choice?.message) {
    throw new Error("Risposta vuota dall'API Mistral");
  }
  return contentToString(choice.message.content);
}

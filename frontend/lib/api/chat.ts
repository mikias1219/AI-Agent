import { ApiError, api, apiUrl } from "./client";
import type { ChatMessage, ChatStreamEvent, ChatTurnResponse, ConversationSummary } from "./types";

export type SendChatInput = {
  message: string;
  sessionId?: string;
};

export type SendChatOptions = {
  onDelta?: (text: string) => void;
  signal?: AbortSignal;
};

export class ChatStreamError extends Error {
  readonly received: boolean;

  constructor(message: string, received: boolean) {
    super(message);
    this.name = "ChatStreamError";
    this.received = received;
  }
}

export async function listConversations(limit = 50): Promise<ConversationSummary[]> {
  return api<ConversationSummary[]>(`/conversations?limit=${limit}`);
}

export async function listMessages(sessionId: string, limit = 100): Promise<ChatMessage[]> {
  return api<ChatMessage[]>(
    `/conversations/${encodeURIComponent(sessionId)}/messages?limit=${limit}`,
  );
}

export async function sendChat(
  input: SendChatInput,
  options: SendChatOptions = {},
): Promise<ChatTurnResponse> {
  const text = input.message.trim();
  if (!text) {
    throw new ApiError("Message is required.", 400);
  }
  const payload: { text: string; session_id?: string } = { text };
  if (input.sessionId) payload.session_id = input.sessionId;
  const body = JSON.stringify(payload);

  try {
    return await postChatStream(body, options);
  } catch (error) {
    if (isAbort(error) || !shouldFallback(error)) throw error;
    return api<ChatTurnResponse>("/chat", {
      method: "POST",
      body,
      signal: options.signal,
    });
  }
}

function shouldFallback(error: unknown): boolean {
  if (error instanceof ChatStreamError) return false;
  if (error instanceof ApiError) {
    return error.status === 404 || error.status === 405 || error.status === 501;
  }
  return error instanceof TypeError;
}

function isAbort(error: unknown): boolean {
  return error instanceof Error && error.name === "AbortError";
}

async function postChatStream(body: string, options: SendChatOptions): Promise<ChatTurnResponse> {
  let response: Response;
  try {
    response = await fetch(apiUrl("/chat/stream"), {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body,
      signal: options.signal,
    });
  } catch (error) {
    if (isAbort(error)) throw error;
    throw error;
  }

  if (!response.ok) {
    throw await errorFromResponse(response);
  }
  if (!response.body) {
    throw new ChatStreamError("The agent reply could not be streamed.", false);
  }

  try {
    return await readNdjson(response.body, options.onDelta);
  } catch (error) {
    if (error instanceof ChatStreamError || isAbort(error)) throw error;
    throw new ChatStreamError(
      error instanceof Error ? error.message : "The agent reply could not be streamed.",
      true,
    );
  }
}

async function errorFromResponse(response: Response): Promise<ApiError> {
  let data: unknown = null;
  try {
    data = await response.json();
  } catch {
    return new ApiError("The backend returned an unreadable response.", response.status);
  }
  const detail = (data as { detail?: string | { msg: string }[] })?.detail;
  const message = Array.isArray(detail)
    ? detail.map((item) => item.msg).join(". ")
    : typeof detail === "string"
      ? detail
      : `Request failed (${response.status}).`;
  return new ApiError(message, response.status);
}

async function readNdjson(
  body: ReadableStream<Uint8Array>,
  onDelta?: (text: string) => void,
): Promise<ChatTurnResponse> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let received = false;

  const consume = (line: string): ChatTurnResponse | null => {
    const trimmed = line.trim();
    if (!trimmed) return null;
    let event: ChatStreamEvent;
    try {
      event = JSON.parse(trimmed) as ChatStreamEvent;
    } catch {
      throw new ChatStreamError("The agent returned an unreadable update.", received);
    }
    if (event.type === "delta") {
      received = true;
      if (event.text) onDelta?.(event.text);
      return null;
    }
    if (event.type === "error") {
      throw new ChatStreamError(
        event.detail || "The agent could not complete this reply.",
        received,
      );
    }
    if (event.type === "done") {
      return { session_id: event.session_id, reply: event.reply };
    }
    return null;
  };

  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      let newline = buffer.indexOf("\n");
      while (newline >= 0) {
        const finished = consume(buffer.slice(0, newline));
        buffer = buffer.slice(newline + 1);
        if (finished) return finished;
        newline = buffer.indexOf("\n");
      }
      if (done) {
        const finished = consume(buffer);
        if (finished) return finished;
        break;
      }
    }
  } finally {
    reader.releaseLock();
  }

  throw new ChatStreamError("The model connection ended before the answer was complete.", received);
}

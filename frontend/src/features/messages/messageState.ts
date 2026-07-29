import type { Message, RealtimeEvent } from "../../api/types";

function messageTime(message: Message): number {
  return new Date(
    message.sent_at ?? message.created_at ?? message.scheduled_for ?? 0,
  ).getTime();
}

export function sortMessages(messages: Message[]): Message[] {
  return [...messages].sort((a, b) => messageTime(a) - messageTime(b));
}

export function mergeMessage(messages: Message[], incoming: Message): Message[] {
  const index = messages.findIndex((message) => message.id === incoming.id);
  if (index === -1) return sortMessages([...messages, incoming]);

  const next = [...messages];
  next[index] = { ...next[index], ...incoming };
  return sortMessages(next);
}

export function applyMessageEvent(
  messages: Message[],
  event: RealtimeEvent,
): Message[] {
  if (
    event.type === "message.created" ||
    event.type === "message.updated" ||
    event.type === "scheduled_message.sent"
  ) {
    const payload = event.payload as Message | { message: Message };
    return mergeMessage(
      messages,
      "message" in payload ? payload.message : payload,
    );
  }

  if (event.type === "message.deleted") {
    const payload = event.payload as { id?: string; message_id?: string };
    const deletedId = payload.id ?? payload.message_id;
    return messages.filter((message) => message.id !== deletedId);
  }

  return messages;
}

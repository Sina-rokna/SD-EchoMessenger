import { describe, expect, it } from "vitest";

import type { Message, RealtimeEvent, User } from "../../api/types";
import { applyMessageEvent, mergeMessage } from "./messageState";

const sender: User = { id: "user-1", username: "Sina" };

function message(id: string, text: string, sentAt: string): Message {
  return {
    id,
    space: "space-1",
    sender,
    text,
    attachments: [],
    status: "SENT",
    sent_at: sentAt,
    is_edited: false,
    failure_reason: "",
    created_at: sentAt,
  };
}

function event(
  type: RealtimeEvent["type"],
  payload: unknown,
): RealtimeEvent {
  return {
    type,
    event_id: crypto.randomUUID(),
    occurred_at: "2026-07-29T10:00:00Z",
    payload,
  };
}

describe("message state", () => {
  it("sorts new messages and de-duplicates a matching WebSocket event", () => {
    const later = message("2", "Later", "2026-07-29T10:02:00Z");
    const earlier = message("1", "Earlier", "2026-07-29T10:01:00Z");

    const firstMerge = mergeMessage([later], earlier);
    const duplicateMerge = applyMessageEvent(
      firstMerge,
      event("message.created", later),
    );

    expect(duplicateMerge.map((item) => item.id)).toEqual(["1", "2"]);
    expect(duplicateMerge).toHaveLength(2);
  });

  it("updates and removes committed messages", () => {
    const original = message("1", "Before", "2026-07-29T10:01:00Z");
    const updated = {
      ...original,
      text: "After",
      edited_at: "now",
      is_edited: true,
    };

    const afterUpdate = applyMessageEvent(
      [original],
      event("message.updated", { message: updated }),
    );
    const afterDelete = applyMessageEvent(
      afterUpdate,
      event("message.deleted", { message_id: "1" }),
    );

    expect(afterUpdate[0].text).toBe("After");
    expect(afterDelete).toEqual([]);
  });
});

import { beforeEach, describe, expect, it, vi } from "vitest";

const { apiRequestMock } = vi.hoisted(() => ({
  apiRequestMock: vi.fn(),
}));

vi.mock("./client", () => ({
  apiRequest: apiRequestMock,
}));

import { messagesApi, spacesApi } from "./endpoints";
import { noPermissions } from "./types";

describe("API endpoint contract", () => {
  beforeEach(() => {
    apiRequestMock.mockReset();
  });

  it("uses the backend topic query key for history and search", async () => {
    apiRequestMock.mockResolvedValue([]);

    await messagesApi.list("space-1", "topic-1");
    await messagesApi.search("space-1", "release plan", "topic-1");

    expect(apiRequestMock.mock.calls[0][0]).toBe(
      "/spaces/space-1/messages/?topic=topic-1",
    );
    expect(apiRequestMock.mock.calls[1][0]).toBe(
      "/spaces/space-1/messages/search/?q=release+plan&topic=topic-1",
    );
  });

  it("sends message text and attachments with the serializer field names", async () => {
    apiRequestMock.mockResolvedValue({});
    const attachment = new File(["notes"], "notes.txt", {
      type: "text/plain",
    });

    await messagesApi.create("space-1", {
      text: "Hello",
      topic_id: "topic-1",
      attachments: [attachment],
      scheduled_for: "2026-07-30T09:00:00.000Z",
      client_nonce: "45c176d0-ab0a-4aca-8ece-2248803e4c08",
    });

    const options = apiRequestMock.mock.calls[0][1] as {
      method: string;
      body: FormData;
    };
    expect(options.method).toBe("POST");
    expect(options.body.get("text")).toBe("Hello");
    expect(options.body.get("content")).toBeNull();
    expect(options.body.get("topic_id")).toBe("topic-1");
    expect(options.body.get("attachments")).toBe(attachment);
  });

  it("writes flat role permissions and adds selected members one at a time", async () => {
    apiRequestMock.mockResolvedValue({});

    await spacesApi.createRole("space-1", "Reader", noPermissions);
    await spacesApi.addMembers("space-1", ["user-1", "user-2"]);

    expect(apiRequestMock.mock.calls[0]).toEqual([
      "/spaces/space-1/roles/",
      {
        method: "POST",
        body: { name: "Reader", ...noPermissions },
      },
    ]);
    expect(apiRequestMock.mock.calls.slice(1)).toEqual([
      [
        "/spaces/space-1/members/",
        { method: "POST", body: { user_id: "user-1" } },
      ],
      [
        "/spaces/space-1/members/",
        { method: "POST", body: { user_id: "user-2" } },
      ],
    ]);
  });
});

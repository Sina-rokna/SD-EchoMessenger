import { afterEach, describe, expect, it, vi } from "vitest";

import { apiRequest, resetCsrfToken } from "./client";

describe("apiRequest", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    resetCsrfToken();
  });

  it("uses same-origin credentials and a CSRF token for unsafe requests", async () => {
    const fetchMock = vi
      .spyOn(window, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ csrf_token: "secure-token" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ id: "message-1" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );

    await apiRequest("/messages/", {
      method: "POST",
      body: { text: "Hello" },
    });

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      credentials: "include",
    });

    const writeOptions = fetchMock.mock.calls[1][1] as RequestInit;
    const headers = writeOptions.headers as Headers;
    expect(writeOptions.credentials).toBe("include");
    expect(headers.get("X-CSRFToken")).toBe("secure-token");
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(writeOptions.body).toBe(JSON.stringify({ text: "Hello" }));
  });

  it("turns server validation details into a readable ApiError", async () => {
    vi.spyOn(window, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "You are not a member." }), {
        status: 403,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(apiRequest("/spaces/private/")).rejects.toMatchObject({
      name: "ApiError",
      status: 403,
      message: "You are not a member.",
    });
  });
});

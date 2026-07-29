import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { MessageComposer } from "./MessageComposer";

describe("MessageComposer", () => {
  it("sends plain text with Enter and keeps Shift+Enter available", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn().mockResolvedValue(undefined);

    render(
      <MessageComposer
        targetName="#general"
        allowMedia
        sending={false}
        onSend={onSend}
      />,
    );

    const input = screen.getByLabelText("Message #general");
    await user.type(input, "Hello team{shift>}{enter}{/shift}Second line");
    expect(input).toHaveValue("Hello team\nSecond line");

    await user.type(input, "{enter}");
    expect(onSend).toHaveBeenCalledWith(
      "Hello team\nSecond line",
      [],
      undefined,
    );
  });

  it("supports multiple safe attachments and rejects files larger than 10 MiB", async () => {
    const user = userEvent.setup();
    render(
      <MessageComposer
        targetName="Design group"
        allowMedia
        sending={false}
        onSend={vi.fn()}
      />,
    );

    const input = screen.getByLabelText("Choose attachments");
    const first = new File(["first"], "brief.txt", { type: "text/plain" });
    const second = new File(["second"], "notes.txt", { type: "text/plain" });
    await user.upload(input, [first, second]);

    expect(screen.getByText("brief.txt")).toBeInTheDocument();
    expect(screen.getByText("notes.txt")).toBeInTheDocument();

    const oversized = new File(
      [new Uint8Array(10 * 1024 * 1024 + 1)],
      "too-large.bin",
    );
    await user.upload(input, oversized);

    expect(screen.getByRole("alert")).toHaveTextContent(
      "too-large.bin is larger than 10 MiB.",
    );
  });
});

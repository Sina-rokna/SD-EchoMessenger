import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Button, IconButton, Modal } from "./ui";

describe("Modal", () => {
  it("has dialog semantics and closes with Escape", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    render(
      <Modal open title="Channel settings" onClose={onClose}>
        <button>Focusable action</button>
      </Modal>,
    );

    expect(
      screen.getByRole("dialog", { name: "Channel settings" }),
    ).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledOnce();
  });
});

describe("button defaults", () => {
  it("keeps action buttons from submitting a surrounding form", () => {
    render(
      <form>
        <Button>Action</Button>
        <IconButton label="Icon action">I</IconButton>
        <IconButton label="Submit action" type="submit">
          S
        </IconButton>
      </form>,
    );

    expect(screen.getByRole("button", { name: "Action" })).toHaveAttribute(
      "type",
      "button",
    );
    expect(
      screen.getByRole("button", { name: "Icon action" }),
    ).toHaveAttribute("type", "button");
    expect(
      screen.getByRole("button", { name: "Submit action" }),
    ).toHaveAttribute("type", "submit");
  });
});

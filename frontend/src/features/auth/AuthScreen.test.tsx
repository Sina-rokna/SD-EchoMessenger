import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthScreen } from "./AuthScreen";

const login = vi.fn();
const register = vi.fn();

vi.mock("./AuthContext", () => ({
  useAuth: () => ({
    login,
    register,
  }),
}));

describe("AuthScreen", () => {
  beforeEach(() => {
    login.mockReset();
    register.mockReset();
  });

  it("submits login credentials without offering fake SSO", async () => {
    const user = userEvent.setup();
    render(<AuthScreen />);

    await user.type(screen.getByLabelText("Email address"), "sina@example.com");
    await user.type(screen.getByLabelText("Password"), "safe-password");
    await user.click(screen.getByRole("button", { name: "Log in" }));

    expect(login).toHaveBeenCalledWith("sina@example.com", "safe-password");
    expect(screen.queryByText(/SSO/i)).not.toBeInTheDocument();
  });

  it("validates matching passwords before registration", async () => {
    const user = userEvent.setup();
    render(<AuthScreen />);

    await user.click(
      screen.getByRole("button", { name: "Create an account" }),
    );
    await user.type(screen.getByLabelText("Username"), "Sina");
    await user.type(screen.getByLabelText("Email address"), "sina@example.com");
    await user.type(screen.getByLabelText("Password"), "safe-password");
    await user.type(
      screen.getByLabelText("Confirm password"),
      "different-password",
    );
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(register).not.toHaveBeenCalled();
    expect(
      screen.getByText("The two passwords do not match."),
    ).toBeInTheDocument();
  });
});

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { authApiMock } = vi.hoisted(() => ({
  authApiMock: {
    me: vi.fn(),
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  },
}));

vi.mock("../../api/endpoints", () => ({
  authApi: authApiMock,
}));

vi.mock("../../api/client", async (importOriginal) => {
  const original = await importOriginal<typeof import("../../api/client")>();
  return {
    ...original,
    resetCsrfToken: vi.fn(),
  };
});

import { ApiError, resetCsrfToken } from "../../api/client";
import { AuthProvider, useAuth } from "./AuthContext";

function AuthHarness({ action }: { action: "login" | "register" }) {
  const { user, loading, login, register } = useAuth();

  if (loading) return <span>Loading</span>;
  if (user) return <span>{user.username}</span>;

  return (
    <button
      onClick={() => {
        if (action === "login") {
          void login("sina@example.com", "secret");
        } else {
          void register("sina", "sina@example.com", "secret");
        }
      }}
    >
      Authenticate
    </button>
  );
}

describe("AuthProvider CSRF lifecycle", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authApiMock.me.mockRejectedValue(new ApiError("Not authenticated", 401));
  });

  it.each(["login", "register"] as const)(
    "clears the pre-authentication token after successful %s",
    async (action) => {
      const authenticatedUser = { id: "user-1", username: "sina" };
      authApiMock[action].mockResolvedValue(authenticatedUser);
      const user = userEvent.setup();

      render(
        <AuthProvider>
          <AuthHarness action={action} />
        </AuthProvider>,
      );

      await user.click(
        await screen.findByRole("button", { name: "Authenticate" }),
      );

      await waitFor(() => {
        expect(screen.getByText("sina")).toBeInTheDocument();
      });
      expect(resetCsrfToken).toHaveBeenCalledTimes(1);
    },
  );
});

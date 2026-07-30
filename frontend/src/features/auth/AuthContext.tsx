import {
  createContext,
  type PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { ApiError, resetCsrfToken } from "../../api/client";
import { authApi } from "../../api/endpoints";
import type { User } from "../../api/types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  updateUser: (user: User) => void;
  retry: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    authApi
      .me()
      .then((currentUser) => {
        if (active) setUser(currentUser);
      })
      .catch((reason: unknown) => {
        if (!active) return;
        if (reason instanceof ApiError && [401, 403].includes(reason.status)) {
          setUser(null);
        } else {
          setError(
            reason instanceof Error
              ? reason.message
              : "Could not reach EchoMessenger.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [attempt]);

  useEffect(() => {
    const handleUnauthorized = () => setUser(null);
    window.addEventListener("echo:unauthorized", handleUnauthorized);
    return () =>
      window.removeEventListener("echo:unauthorized", handleUnauthorized);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const authenticatedUser = await authApi.login(email, password);
    // Django rotates the CSRF token when login() creates the authenticated
    // session. Force the next write to fetch that new token.
    resetCsrfToken();
    setUser(authenticatedUser);
  }, []);

  const register = useCallback(
    async (username: string, email: string, password: string) => {
      const authenticatedUser = await authApi.register(
        username,
        email,
        password,
      );
      // Registration logs the new user in and rotates CSRF for the same reason.
      resetCsrfToken();
      setUser(authenticatedUser);
    },
    [],
  );

  const logout = useCallback(async () => {
    await authApi.logout();
    resetCsrfToken();
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      error,
      login,
      register,
      logout,
      updateUser: setUser,
      retry: () => setAttempt((value) => value + 1),
    }),
    [error, loading, login, logout, register, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider.");
  return value;
}

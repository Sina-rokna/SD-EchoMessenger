const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

let csrfToken: string | null = null;

export class ApiError extends Error {
  status: number;
  details: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

function readCookie(name: string): string | null {
  const prefix = `${name}=`;
  const cookie = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(prefix));

  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : null;
}

async function loadCsrfToken(): Promise<string> {
  const response = await fetch(`${API_BASE}/auth/csrf/`, {
    credentials: "include",
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new ApiError("Could not establish a secure session.", response.status);
  }

  const data = (await response.json().catch(() => ({}))) as Record<string, string>;
  csrfToken =
    data.csrf_token ??
    data.csrfToken ??
    readCookie("csrftoken") ??
    response.headers.get("X-CSRFToken");

  if (!csrfToken) {
    throw new ApiError("The server did not provide a CSRF token.", 500);
  }

  return csrfToken;
}

function messageFromError(data: unknown, fallback: string): string {
  if (!data || typeof data !== "object") return fallback;
  const record = data as Record<string, unknown>;

  if (typeof record.detail === "string") return record.detail;
  if (typeof record.message === "string") return record.message;

  const firstEntry = Object.entries(record)[0];
  if (!firstEntry) return fallback;
  const [field, value] = firstEntry;
  const text = Array.isArray(value) ? value.join(" ") : String(value);
  return `${field.replaceAll("_", " ")}: ${text}`;
}

export interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const unsafe = !["GET", "HEAD", "OPTIONS"].includes(method);
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");

  if (unsafe) {
    headers.set("X-CSRFToken", csrfToken ?? (await loadCsrfToken()));
  }

  let body: BodyInit | undefined;
  if (options.body instanceof FormData) {
    body = options.body;
  } else if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.body);
  }

  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const response = await fetch(url, {
    ...options,
    method,
    headers,
    body,
    credentials: "include",
  });

  if (response.status === 401) {
    window.dispatchEvent(new CustomEvent("echo:unauthorized"));
  }

  if (!response.ok) {
    const details = await response.json().catch(() => null);
    throw new ApiError(
      messageFromError(details, `Request failed with status ${response.status}.`),
      response.status,
      details,
    );
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function resetCsrfToken(): void {
  csrfToken = null;
}

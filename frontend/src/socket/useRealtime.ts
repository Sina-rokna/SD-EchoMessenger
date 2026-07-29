import { useEffect, useRef, useState } from "react";

import type { RealtimeEvent } from "../api/types";

export type ConnectionState = "idle" | "connecting" | "connected" | "offline";

export const HEARTBEAT_INTERVAL_MS = 30_000;

function websocketUrl(path: string): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}${path}`;
}

export function isTerminalCloseCode(code: number): boolean {
  return [4001, 4003, 4401, 4403].includes(code);
}

export function useRealtime(
  path: string | null,
  onEvent: (event: RealtimeEvent) => void,
) {
  const handlerRef = useRef(onEvent);
  const [connectionState, setConnectionState] =
    useState<ConnectionState>("idle");

  useEffect(() => {
    handlerRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    if (!path) {
      setConnectionState("idle");
      return;
    }

    let socket: WebSocket | null = null;
    let retryTimer: number | null = null;
    let heartbeatTimer: number | null = null;
    let attempts = 0;
    let disposed = false;

    function clearHeartbeat() {
      if (heartbeatTimer !== null) {
        window.clearInterval(heartbeatTimer);
        heartbeatTimer = null;
      }
    }

    function connect() {
      if (disposed) return;
      clearHeartbeat();
      setConnectionState("connecting");
      socket = new WebSocket(websocketUrl(path!));

      socket.addEventListener("open", () => {
        attempts = 0;
        setConnectionState("connected");
        heartbeatTimer = window.setInterval(() => {
          if (socket?.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: "ping" }));
          }
        }, HEARTBEAT_INTERVAL_MS);
      });

      socket.addEventListener("message", (message) => {
        try {
          const frame = JSON.parse(message.data) as {
            type?: string;
            payload?: unknown;
          };
          if (frame.type === "pong") return;
          if (frame.type && frame.payload !== undefined) {
            handlerRef.current(frame as RealtimeEvent);
          }
        } catch {
          // Ignore malformed frames; the next committed event remains usable.
        }
      });

      socket.addEventListener("close", (event) => {
        clearHeartbeat();
        if (disposed) return;
        if (isTerminalCloseCode(event.code)) {
          setConnectionState("offline");
          return;
        }

        setConnectionState("offline");
        const delay = Math.min(1000 * 2 ** attempts, 15_000);
        attempts += 1;
        retryTimer = window.setTimeout(connect, delay);
      });

      socket.addEventListener("error", () => socket?.close());
    }

    connect();

    return () => {
      disposed = true;
      clearHeartbeat();
      if (retryTimer !== null) window.clearTimeout(retryTimer);
      socket?.close(1000, "View changed");
    };
  }, [path]);

  return connectionState;
}

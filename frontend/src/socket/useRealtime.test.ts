import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  HEARTBEAT_INTERVAL_MS,
  isTerminalCloseCode,
  useRealtime,
} from "./useRealtime";

class FakeWebSocket {
  static readonly OPEN = 1;
  static readonly CLOSED = 3;
  static instances: FakeWebSocket[] = [];

  readonly send = vi.fn();
  readyState = 0;
  private readonly listeners = new Map<
    string,
    Array<(event: Record<string, unknown>) => void>
  >();

  constructor(readonly url: string) {
    FakeWebSocket.instances.push(this);
  }

  addEventListener(
    type: string,
    listener: (event: Record<string, unknown>) => void,
  ) {
    const listeners = this.listeners.get(type) ?? [];
    listeners.push(listener);
    this.listeners.set(type, listeners);
  }

  emit(type: string, event: Record<string, unknown> = {}) {
    this.listeners.get(type)?.forEach((listener) => listener(event));
  }

  close() {
    this.readyState = FakeWebSocket.CLOSED;
  }
}

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  FakeWebSocket.instances = [];
});

describe("WebSocket close handling", () => {
  it("does not reconnect after authentication or membership rejection", () => {
    expect([4001, 4003, 4401, 4403].every(isTerminalCloseCode)).toBe(true);
    expect(isTerminalCloseCode(1006)).toBe(false);
  });

  it("heartbeats an open socket, ignores pong, and clears the timer on close", () => {
    vi.useFakeTimers();
    vi.stubGlobal("WebSocket", FakeWebSocket);
    const onEvent = vi.fn();

    const { unmount } = renderHook(() =>
      useRealtime("/ws/spaces/space-1/", onEvent),
    );
    const socket = FakeWebSocket.instances[0];

    act(() => {
      vi.advanceTimersByTime(HEARTBEAT_INTERVAL_MS);
    });
    expect(socket.send).not.toHaveBeenCalled();

    socket.readyState = FakeWebSocket.OPEN;
    act(() => {
      socket.emit("open");
      vi.advanceTimersByTime(HEARTBEAT_INTERVAL_MS);
    });
    expect(socket.send).toHaveBeenCalledOnce();
    expect(socket.send).toHaveBeenCalledWith('{"type":"ping"}');

    act(() => {
      socket.emit("message", { data: '{"type":"pong"}' });
      socket.emit("message", {
        data: JSON.stringify({
          type: "message.deleted",
          event_id: "event-1",
          occurred_at: "2026-07-29T12:00:00Z",
          payload: { id: "message-1" },
        }),
      });
    });
    expect(onEvent).toHaveBeenCalledOnce();

    socket.readyState = FakeWebSocket.CLOSED;
    act(() => {
      socket.emit("close", { code: 4403 });
      vi.advanceTimersByTime(HEARTBEAT_INTERVAL_MS * 2);
    });
    expect(socket.send).toHaveBeenCalledOnce();
    expect(FakeWebSocket.instances).toHaveLength(1);

    unmount();
  });
});

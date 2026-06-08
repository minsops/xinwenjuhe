import { useEffect, useState } from "react";

export type LiveEventMessage = {
  type?: string;
  event_id?: string;
  payload?: unknown;
};

export function useEventSocket(eventId?: string) {
  const [message, setMessage] = useState<LiveEventMessage | undefined>();
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!eventId || eventId === "demo") return;
    let socket: WebSocket | undefined;
    let retry: number | undefined;
    let closed = false;
    const base = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";

    function connect() {
      socket = new WebSocket(`${base}/api/v1/ws/events/${eventId}`);
      socket.onopen = () => setConnected(true);
      socket.onmessage = (event) => {
        try {
          setMessage(JSON.parse(event.data));
        } catch {
          setMessage({ type: "message", payload: event.data });
        }
      };
      socket.onclose = () => {
        setConnected(false);
        if (!closed) retry = window.setTimeout(connect, 2000);
      };
      socket.onerror = () => {
        socket?.close();
      };
    }

    connect();
    return () => {
      closed = true;
      if (retry) window.clearTimeout(retry);
      socket?.close();
    };
  }, [eventId]);

  return { connected, message };
}


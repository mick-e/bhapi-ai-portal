"use client";

import { useEffect, useRef, useCallback, useState } from "react";

interface AlertEvent {
  id: string;
  group_id: string;
  severity: string;
  title: string;
  created_at: string;
}

interface UseAlertStreamOptions {
  groupId: string;
  enabled?: boolean;
  onAlert?: (alert: AlertEvent) => void;
}

export function useAlertStream({ groupId, enabled = true, onAlert }: UseAlertStreamOptions) {
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<AlertEvent | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();

  const connect = useCallback(() => {
    if (!groupId || !enabled) return;

    const url = `/api/v1/alerts/stream?group_id=${groupId}`;
    const es = new EventSource(url, { withCredentials: true });

    es.onopen = () => setConnected(true);

    es.addEventListener("new_alert", (event) => {
      try {
        const data: AlertEvent = JSON.parse(event.data);
        setLastEvent(data);
        onAlert?.(data);
      } catch {
        // ignore parse errors
      }
    });

    es.onerror = () => {
      setConnected(false);
      es.close();
      // Reconnect after 5 seconds
      reconnectTimeoutRef.current = setTimeout(connect, 5000);
    };

    eventSourceRef.current = es;
  }, [groupId, enabled, onAlert]);

  useEffect(() => {
    connect();
    return () => {
      eventSourceRef.current?.close();
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  return { connected, lastEvent };
}

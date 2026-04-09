"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { ScanLiveEvent } from "@/types";

export function useScanWebSocket(scanId: string | null) {
  const [events, setEvents] = useState<ScanLiveEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (!scanId) return;

    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000"}/ws/scan/${scanId}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => setConnected(true);

    ws.onmessage = (event) => {
      try {
        const data: ScanLiveEvent = JSON.parse(event.data);
        setEvents((prev) => [...prev, data]);
      } catch {
        // Ignore invalid messages
      }
    };

    ws.onclose = () => {
      setConnected(false);
    };

    ws.onerror = () => {
      setConnected(false);
    };

    wsRef.current = ws;
  }, [scanId]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
  }, []);

  return { events, connected, disconnect };
}

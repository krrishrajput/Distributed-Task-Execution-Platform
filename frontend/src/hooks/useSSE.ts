import { useState, useEffect, useCallback, useRef } from 'react';
import { SystemEvent } from '../types';

export function useSSE(url: string = '/api/v1/events', maxEvents: number = 100) {
  const [events, setEvents] = useState<SystemEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const bufferRef = useRef<SystemEvent[]>([]);

  useEffect(() => {
    const eventSource = new EventSource(url);

    eventSource.onopen = () => {
      setIsConnected(true);
    };

    eventSource.onmessage = (e) => {
      if (e.data === ': ping' || e.data === ': connected') return;
      try {
        const data = JSON.parse(e.data) as SystemEvent;
        if (!data.event_id) {
          data.event_id = `evt-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
        }
        bufferRef.current.push(data);
      } catch (err) {
        console.error("Failed to parse SSE message:", err);
      }
    };

    eventSource.onerror = () => {
      setIsConnected(false);
    };

    // Batch flush the buffer to React state at exactly 10Hz (100ms)
    // This prevents main thread lockups during high-frequency task bursts
    const flushInterval = setInterval(() => {
      if (bufferRef.current.length > 0) {
        setEvents(prev => {
          const newEvents = [...bufferRef.current.reverse(), ...prev];
          return newEvents.slice(0, maxEvents);
        });
        bufferRef.current = []; // clear buffer after flush
      }
    }, 100);

    return () => {
      clearInterval(flushInterval);
      eventSource.close();
    };
  }, [url, maxEvents]);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  return { events, isConnected, clearEvents };
}

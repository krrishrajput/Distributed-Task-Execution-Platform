import { useState, useEffect, useCallback } from 'react';
import { SystemEvent } from '../types';

export function useSSE(url: string = '/api/v1/events', maxEvents: number = 100) {
  const [events, setEvents] = useState<SystemEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const eventSource = new EventSource(url);

    eventSource.onopen = () => {
      setIsConnected(true);
    };

    eventSource.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as SystemEvent;
        if (!data.event_id) {
          data.event_id = `evt-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
        }
        setEvents(prev => {
          const newEvents = [data, ...prev];
          if (newEvents.length > maxEvents) {
            return newEvents.slice(0, maxEvents);
          }
          return newEvents;
        });
      } catch (err) {
        console.error("Failed to parse SSE message:", err);
      }
    };

    eventSource.onerror = () => {
      setIsConnected(false);
    };

    return () => {
      eventSource.close();
    };
  }, [url, maxEvents]);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  return { events, isConnected, clearEvents };
}

import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { SystemEvent } from '../types';

interface SSEContextType {
  events: SystemEvent[];
  isConnected: boolean;
  clearEvents: () => void;
}

const SSEContext = createContext<SSEContextType>({
  events: [],
  isConnected: false,
  clearEvents: () => {},
});

export const SSEProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [events, setEvents] = useState<SystemEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const bufferRef = useRef<SystemEvent[]>([]);

  useEffect(() => {
    const eventSource = new EventSource('/api/v1/events');

    eventSource.onopen = () => setIsConnected(true);
    eventSource.onerror = () => setIsConnected(false);

    eventSource.onmessage = (e) => {
      if (e.data === ': ping' || e.data === ': connected') return;
      try {
        const data = JSON.parse(e.data) as SystemEvent;
        if (!data.event_id) {
          data.event_id = `evt-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
        }
        bufferRef.current.push(data);
      } catch (err) {}
    };

    const flushInterval = setInterval(() => {
      if (bufferRef.current.length > 0) {
        setEvents(prev => {
          const newEvents = [...bufferRef.current.reverse(), ...prev];
          return newEvents.slice(0, 500); // Keep max 500 in global state
        });
        bufferRef.current = [];
      }
    }, 100);

    return () => {
      clearInterval(flushInterval);
      eventSource.close();
    };
  }, []);

  const clearEvents = () => setEvents([]);

  return (
    <SSEContext.Provider value={{ events, isConnected, clearEvents }}>
      {children}
    </SSEContext.Provider>
  );
};

export const useGlobalSSE = () => useContext(SSEContext);

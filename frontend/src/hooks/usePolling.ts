import { useState, useEffect, useCallback } from 'react';

export function usePolling<T>(
  fetchFn: () => Promise<T>,
  interval: number = 5000,
  deps: any[] = []
) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchData = useCallback(async (isMounted: boolean) => {
    try {
      const result = await fetchFn();
      if (isMounted) {
        setData(result);
        setError(null);
      }
    } catch (err) {
      if (isMounted) setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      if (isMounted) setIsLoading(false);
    }
  }, [fetchFn]); // Careful with fetchFn changes

  useEffect(() => {
    let isMounted = true;
    
    // Initial fetch
    fetchData(isMounted);
    
    // Setup interval
    const timer = setInterval(() => fetchData(isMounted), interval);

    return () => {
      isMounted = false;
      clearInterval(timer);
    };
  }, [interval, fetchData, ...deps]);

  return { data, error, isLoading, refetch: () => fetchData(true) };
}

import { useState, useEffect, useRef, useCallback } from 'react';

export function usePolling<T>(
  fetchFn: () => Promise<T>,
  intervalMs: number = 5000,
  deps: any[] = []
) {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  
  const fetchFnRef = useRef(fetchFn);
  const isMounted = useRef(true);
  const activeRequest = useRef<Promise<T> | null>(null);

  useEffect(() => {
    fetchFnRef.current = fetchFn;
  }, [fetchFn]);

  const fetchData = useCallback(async (isInitial = false) => {
    if (!isMounted.current) return;
    if (activeRequest.current) return; // Prevent overlapping requests

    if (isInitial) setIsLoading(true);
    else setIsRefreshing(true);

    try {
      activeRequest.current = fetchFnRef.current();
      const result = await activeRequest.current;
      if (isMounted.current) {
        setData(result);
        setError(null);
      }
    } catch (err) {
      if (isMounted.current) {
        setError(err as Error);
      }
    } finally {
      if (isMounted.current) {
        setIsLoading(false);
        setIsRefreshing(false);
      }
      activeRequest.current = null;
    }
  }, []); // fetchData itself has stable identity

  useEffect(() => {
    isMounted.current = true;
    
    // Initial fetch on mount or deps change
    fetchData(true);

    // Setup polling interval
    const interval = setInterval(() => {
      fetchData(false);
    }, intervalMs);

    return () => {
      isMounted.current = false;
      clearInterval(interval);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, intervalMs]); 

  return { data, isLoading, isRefreshing, error, refetch: () => fetchData(false) };
}

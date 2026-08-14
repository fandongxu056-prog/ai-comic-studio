/** Shared hook — fetch real stage data from API, fall back to mock. */

import { useEffect, useState } from "react";

interface StageDataOptions<T> {
  mock: T;
  /** Async function that fetches real data from the API */
  fetch?: () => Promise<T>;
  /** Whether real data is considered "present" (otherwise use mock) */
  hasData?: (data: T) => boolean;
}

export function useStageData<T>(options: StageDataOptions<T>) {
  const [data, setData] = useState<T>(options.mock);
  const [loading, setLoading] = useState(true);
  const [isMock, setIsMock] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    if (!options.fetch) {
      setLoading(false);
      setIsMock(true);
      return;
    }
    setLoading(true);
    try {
      const result = await options.fetch();
      if (options.hasData ? options.hasData(result) : result) {
        setData(result);
        setIsMock(false);
      } else {
        setData(options.mock);
        setIsMock(true);
      }
      setError("");
    } catch {
      setData(options.mock);
      setIsMock(true);
      setError("");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  return { data, loading, isMock, error, reload: load };
}

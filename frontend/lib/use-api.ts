"use client";

import { useCallback, useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

export interface ApiResource<T> {
  data: T | null;
  error: Error | null;
  loading: boolean;
  refresh: () => void;
}

export function useApi<T>(path: string | null): ApiResource<T> {
  const [resource, setResource] = useState<
    | { key: string; data: T }
    | { key: string; error: Error }
    | null
  >(null);
  const [generation, setGeneration] = useState(0);
  const key = path === null ? null : `${path}::${generation}`;
  const refresh = useCallback(() => setGeneration((value) => value + 1), []);

  useEffect(() => {
    if (path === null) return;
    const controller = new AbortController();
    apiRequest<T>(path, { signal: controller.signal })
      .then((result) => {
        if (!controller.signal.aborted) setResource({ key: `${path}::${generation}`, data: result });
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return;
        setResource({
          key: `${path}::${generation}`,
          error: reason instanceof Error ? reason : new Error("The API request failed."),
        });
      });
    return () => controller.abort();
  }, [path, generation]);

  if (key === null) return { data: null, error: null, loading: false, refresh };
  const current = resource?.key === key ? resource : null;
  return {
    data: current && "data" in current ? current.data : null,
    error: current && "error" in current ? current.error : null,
    loading: current === null,
    refresh,
  };
}

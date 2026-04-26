/**
 * Kevin — data hook
 * Fetches /api/stats/summary and /api/stats/timeline from the real backend.
 * Returns the same shape as buildMockStatsResponse() so Dashboard renders unchanged.
 */

import { useQuery } from "@tanstack/react-query";
import { fetchAPI } from "../api/client";
import type { StatsSummary, StatsResponse, TimelinePoint } from "../../../Taskin/Front-end/src/types";

export function useStats(): {
  data: StatsResponse | undefined;
  isLoading: boolean;
  isError: boolean;
} {
  const summaryQ = useQuery({
    queryKey: ["stats-summary"],
    queryFn:  () => fetchAPI<StatsSummary>("/api/stats/summary"),
    staleTime: 60_000,
  });

  const timelineQ = useQuery({
    queryKey: ["stats-timeline"],
    queryFn:  () => fetchAPI<TimelinePoint[]>("/api/stats/timeline"),
    staleTime: 60_000,
  });

  const isLoading = summaryQ.isLoading || timelineQ.isLoading;
  const isError   = summaryQ.isError   || timelineQ.isError;

  const data: StatsResponse | undefined =
    summaryQ.data && timelineQ.data
      ? { summary: summaryQ.data, timeline: timelineQ.data }
      : undefined;

  return { data, isLoading, isError };
}

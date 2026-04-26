import { fetchAPI } from "./client";
import type { StatsResponse, StatsSummary, TimelinePoint } from "../types";

export function getStatsSummary(): Promise<StatsSummary> {
  return fetchAPI<StatsSummary>("/api/stats/summary");
}

export function getStatsTimeline(): Promise<TimelinePoint[]> {
  return fetchAPI<TimelinePoint[]>("/api/stats/timeline");
}

export async function getCombinedStats(): Promise<StatsResponse> {
  const [summary, timeline] = await Promise.all([
    getStatsSummary(),
    getStatsTimeline(),
  ]);

  return { summary, timeline };
}
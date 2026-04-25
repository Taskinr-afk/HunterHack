import { fetchAPI } from "./client";
import type { StatsResponse, StatsSummary } from "../types";

export function getStats(): Promise<StatsResponse | StatsSummary> {
  return fetchAPI<StatsResponse | StatsSummary>("/stats");
}

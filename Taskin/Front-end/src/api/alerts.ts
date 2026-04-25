import { fetchAPI } from "./client";
import type { AdminRefreshResponse, AlertResponse } from "../types";

export function sendAlert(potholeId: string): Promise<AlertResponse> {
  // Public report endpoint — no API key needed from the UI
  return fetchAPI<AlertResponse>(`/alerts/report?pothole_id=${encodeURIComponent(potholeId)}`, {
    method: "POST",
  });
}

export function adminRefresh(secret = "potholeiq-dev"): Promise<AdminRefreshResponse> {
  return fetchAPI<AdminRefreshResponse>(`/admin/refresh?secret=${secret}`, {
    method: "POST",
  });
}

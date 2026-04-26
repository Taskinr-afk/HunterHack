import { fetchAPI } from "./client";
import type { AdminRefreshResponse, AlertResponse } from "../types";

const ADMIN_API_KEY = (import.meta as ImportMeta & { env: { VITE_ADMIN_API_KEY?: string } }).env.VITE_ADMIN_API_KEY || "change-me";

export function sendAlert(potholeId: string, message?: string): Promise<AlertResponse> {
  return fetchAPI<AlertResponse>("/api/alerts/send", {
    method: "POST",
    headers: {
      "x-api-key": ADMIN_API_KEY,
    },
    body: JSON.stringify({ pothole_id: potholeId, message }),
  });
}

export function getAlertHistory(limit = 100): Promise<AlertResponse[]> {
  return fetchAPI<AlertResponse[]>(`/api/alerts/history?limit=${limit}`);
}

export function adminRefresh(secret = "potholeiq-dev"): Promise<AdminRefreshResponse> {
  return fetchAPI<AdminRefreshResponse>(`/admin/refresh?secret=${secret}`, {
    method: "POST",
  });
}
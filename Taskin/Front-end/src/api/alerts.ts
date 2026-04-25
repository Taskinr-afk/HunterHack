import { fetchAPI } from "./client";
import type { AdminRefreshResponse, AlertResponse } from "../types";

export function sendAlert(potholeId: string): Promise<AlertResponse> {
  return fetchAPI<AlertResponse>("/alerts/send", {
    method: "POST",
    body: JSON.stringify({ pothole_id: potholeId }),
  });
}

export function adminRefresh(secret = "potholeiq-dev"): Promise<AdminRefreshResponse> {
  return fetchAPI<AdminRefreshResponse>(`/admin/refresh?secret=${secret}`, {
    method: "POST",
  });
}

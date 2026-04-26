import { fetchAPI } from "./client";
import type { AdminRefreshResponse, AlertResponse } from "../types";

export function sendAlert(potholeId: string): Promise<AlertResponse> {
  // Public report endpoint — no API key needed from the UI
  return fetchAPI<AlertResponse>(`/alerts/report?pothole_id=${encodeURIComponent(potholeId)}`, {
    method: "POST",
  });
}

// Admin refresh must be called from server-side or with an explicit secret.
// Never hardcode secrets in frontend code.
export function adminRefresh(secret: string): Promise<AdminRefreshResponse> {
  if (!secret) {
    throw new Error("Admin secret is required — do not call this from the browser without a key");
  }
  return fetchAPI<AdminRefreshResponse>(`/admin/refresh?secret=${encodeURIComponent(secret)}`, {
    method: "POST",
  });
}

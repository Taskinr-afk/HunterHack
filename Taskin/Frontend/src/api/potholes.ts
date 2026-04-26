import { fetchAPI } from "./client";
import type { Pothole, PotholeDetail, PotholeFeatureCollection, PotholeFilters, PredictRequest } from "../types";

function buildQuery(params: PotholeFilters): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  });
  const query = search.toString();
  return query ? `?${query}` : "";
}

function normalizeStatus(status: string | null | undefined): "open" | "closed" {
  if (!status) return "open";
  return status.toLowerCase() === "closed" ? "closed" : "open";
}

function mapGeoJSONProperties(props: Record<string, unknown>, coordinates?: [number, number]): Pothole {
  const lat = coordinates ? coordinates[1] : typeof props.latitude === "number" ? props.latitude : 0;
  const lng = coordinates ? coordinates[0] : typeof props.longitude === "number" ? props.longitude : 0;
  const probHigh = typeof props.prob_high === "number" ? props.prob_high : 0;
  const probCritical = typeof props.prob_critical === "number" ? props.prob_critical : 0;

  return {
    unique_key: String(props.unique_key ?? ""),
    latitude: lat, longitude: lng,
    borough: String(props.borough ?? ""),
    status: normalizeStatus(props.status as string),
    descriptor: props.descriptor as string | null ?? null,
    street_name: props.street_name as string | null ?? null,
    age_days: typeof props.age_days === "number" ? props.age_days : null,
    risk_score: typeof props.risk_score === "number" ? props.risk_score : null,
    urgency_label: props.urgency_label as string | null ?? null,
    urgency_tier: typeof props.urgency_tier === "number" ? props.urgency_tier : null,
    nearby_crashes: typeof props.nearby_crashes === "number" ? props.nearby_crashes : null,
    traffic_volume: typeof props.traffic_volume === "number" ? props.traffic_volume : null,
    aadt: typeof props.aadt === "number" ? props.aadt : null,
    fix_days_estimate: typeof props.fix_days_estimate === "number" ? props.fix_days_estimate : null,
    accident_risk: (props.urgency_label as string)?.toUpperCase() ?? null,
    accident_risk_probability: Math.round((probHigh + probCritical) * 1000) / 1000,
    predicted_repair_days: typeof props.fix_days_estimate === "number" ? props.fix_days_estimate : null,
    prob_low: typeof props.prob_low === "number" ? props.prob_low : null,
    prob_medium: typeof props.prob_medium === "number" ? props.prob_medium : null,
    prob_high: probHigh || null,
    prob_critical: probCritical || null,
    created_date: props.created_date as string | null ?? null,
    closed_date: props.closed_date as string | null ?? null,
  };
}

export async function getPotholesGeoJSON(params: PotholeFilters = {}): Promise<Pothole[]> {
  const raw = await fetchAPI<PotholeFeatureCollection>(`/potholes/geojson${buildQuery(params)}`);
  return (raw.features ?? []).map((f) =>
    mapGeoJSONProperties(f.properties as unknown as Record<string, unknown>, f.geometry?.coordinates)
  );
}

export async function getPotholeById(uniqueKey: string): Promise<PotholeDetail> {
  const raw = await fetchAPI<Record<string, unknown>>(`/api/potholes/${uniqueKey}`);
  return {
    unique_key: String(raw.unique_key ?? ""),
    borough: String(raw.borough ?? ""),
    status: normalizeStatus(raw.status as string),
    descriptor: raw.descriptor as string | null ?? null,
    street_name: raw.street_name as string | null ?? null,
    age_days: typeof raw.age_days === "number" ? raw.age_days : null,
    risk_score: typeof raw.risk_score === "number" ? raw.risk_score : null,
    urgency_label: raw.urgency_label as string | null ?? null,
    urgency_tier: typeof raw.urgency_tier === "number" ? raw.urgency_tier : null,
    nearby_crashes: typeof raw.nearby_crashes === "number" ? raw.nearby_crashes : null,
    traffic_volume: typeof raw.traffic_volume === "number" ? raw.traffic_volume : null,
    aadt: typeof raw.aadt === "number" ? raw.aadt : null,
    fix_days_estimate: typeof raw.fix_days_estimate === "number" ? raw.fix_days_estimate : null,
    accident_risk: (raw.accident_risk as string)?.toUpperCase() ?? null,
    accident_risk_probability: typeof raw.accident_risk_probability === "number" ? raw.accident_risk_probability : null,
    predicted_repair_days: typeof raw.predicted_repair_days === "number" ? raw.predicted_repair_days : null,
    prob_low: typeof raw.prob_low === "number" ? raw.prob_low : null,
    prob_medium: typeof raw.prob_medium === "number" ? raw.prob_medium : null,
    prob_high: typeof raw.prob_high === "number" ? raw.prob_high : null,
    prob_critical: typeof raw.prob_critical === "number" ? raw.prob_critical : null,
    created_date: raw.created_date as string | null ?? null,
    closed_date: raw.closed_date as string | null ?? null,
  };
}

export function predictPothole(payload: PredictRequest) {
  return fetchAPI<Record<string, unknown>>("/predict", { method: "POST", body: JSON.stringify(payload) });
}

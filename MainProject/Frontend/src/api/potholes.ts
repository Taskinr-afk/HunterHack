import { fetchAPI } from "./client";
import type {
  Pothole,
  PotholeDetail,
  PotholeFeature,
  PotholeFeatureCollection,
  PotholeFilters,
  PredictRequest,
} from "../types";
import { sanitizeText } from "../utils/map";

function buildQuery(params: PotholeFilters): string {
  const search = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      if (key === "borough" && typeof value === "string") {
        search.set(key, value.toUpperCase());
        return;
      }

      search.set(key, String(value));
    }
  });

  const query = search.toString();
  return query ? `?${query}` : "";
}

/**
 * Normalize status to lowercase so frontend types work consistently.
 * The backend returns "Open"/"Closed" (capitalized).
 */
function normalizeStatus(status: string | null | undefined): "open" | "closed" | "unverified" {
  if (!status) return "open";
  const lower = status.toLowerCase();
  if (lower === "closed") return "closed";
  if (lower === "unverified") return "unverified";
  return "open";
}

function toFiniteNumber(value: unknown): number | null {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }

  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  return null;
}

/**
 * Map a GeoJSON feature's properties to a Pothole record.
 * Backend GeoJSON uses canonical schema: age_days, nearby_crashes, etc.
 * We compute accident_risk_probability from prob_high + prob_critical.
 */
function mapGeoJSONProperties(
  props: Record<string, unknown>,
  coordinates?: [number, number],
): Pothole {
  // GeoJSON coordinates are [longitude, latitude]; fall back to properties if missing
  const lat = coordinates ? coordinates[1] : toFiniteNumber(props.latitude) ?? 0;
  const lng = coordinates ? coordinates[0] : toFiniteNumber(props.longitude) ?? 0;

  const probHigh = toFiniteNumber(props.prob_high) ?? 0;
  const probCritical = toFiniteNumber(props.prob_critical) ?? 0;
  const accidentProbability = toFiniteNumber(props.accident_probability)
    ?? Math.round((probHigh + probCritical) * 1000) / 1000;

  return {
    unique_key: String(props.unique_key ?? ""),
    latitude: lat,
    longitude: lng,
    borough: sanitizeText(typeof props.borough === "string" ? props.borough : null) ?? "UNKNOWN",
    status: normalizeStatus(props.status as string),
    descriptor: sanitizeText(typeof props.descriptor === "string" ? props.descriptor : null),
    street_name: sanitizeText(typeof props.street_name === "string" ? props.street_name : null),
    age_days: toFiniteNumber(props.age_days),
    risk_score: toFiniteNumber(props.risk_score),
    urgency_label: sanitizeText(typeof props.urgency_label === "string" ? props.urgency_label : null),
    urgency_tier: toFiniteNumber(props.urgency_tier),
    nearby_crashes: toFiniteNumber(props.nearby_crashes),
    traffic_volume: toFiniteNumber(props.traffic_volume),
    aadt: toFiniteNumber(props.aadt),
    fix_days_estimate: toFiniteNumber(props.fix_days_estimate),
    accident_risk: sanitizeText(typeof props.urgency_label === "string" ? props.urgency_label.toUpperCase() : null),
    accident_risk_probability: toFiniteNumber(props.accident_risk_probability)
      ?? Math.round((probHigh + probCritical) * 1000) / 1000,
    accident_probability: accidentProbability,
    predicted_repair_days: toFiniteNumber(props.fix_days_estimate),
    prob_low: toFiniteNumber(props.prob_low),
    prob_medium: toFiniteNumber(props.prob_medium),
    prob_high: toFiniteNumber(props.prob_high),
    prob_critical: toFiniteNumber(props.prob_critical),
    created_date: sanitizeText(typeof props.created_date === "string" ? props.created_date : null),
    closed_date: sanitizeText(typeof props.closed_date === "string" ? props.closed_date : null),
  };
}

export async function getPotholesGeoJSON(
  params: PotholeFilters = {},
): Promise<Pothole[]> {
  const raw = await fetchAPI<PotholeFeatureCollection>(
    `/potholes/geojson${buildQuery(params)}`,
  );

  return (raw.features ?? []).map((f) =>
    mapGeoJSONProperties(
      f.properties as unknown as Record<string, unknown>,
      f.geometry?.coordinates,
    ),
  );
}

export async function getPotholeById(uniqueKey: string): Promise<PotholeDetail> {
  const raw = await fetchAPI<Record<string, unknown>>(`/api/potholes/${uniqueKey}`);

  // Normalize status and ensure field names match frontend types
  return {
    unique_key: String(raw.unique_key ?? ""),
    latitude: toFiniteNumber(raw.latitude),
    longitude: toFiniteNumber(raw.longitude),
    borough: sanitizeText(typeof raw.borough === "string" ? raw.borough : null) ?? "UNKNOWN",
    status: normalizeStatus(raw.status as string),
    descriptor: sanitizeText(typeof raw.descriptor === "string" ? raw.descriptor : null),
    street_name: sanitizeText(typeof raw.street_name === "string" ? raw.street_name : null),
    age_days: toFiniteNumber(raw.age_days),
    risk_score: toFiniteNumber(raw.risk_score),
    urgency_label: sanitizeText(typeof raw.urgency_label === "string" ? raw.urgency_label : null),
    urgency_tier: toFiniteNumber(raw.urgency_tier),
    nearby_crashes: toFiniteNumber(raw.nearby_crashes),
    traffic_volume: toFiniteNumber(raw.traffic_volume),
    aadt: toFiniteNumber(raw.aadt),
    fix_days_estimate: toFiniteNumber(raw.fix_days_estimate),
    accident_risk: sanitizeText(typeof raw.accident_risk === "string" ? raw.accident_risk.toUpperCase() : null),
    accident_risk_probability: toFiniteNumber(raw.accident_risk_probability),
    accident_probability: toFiniteNumber(raw.accident_probability),
    predicted_repair_days: toFiniteNumber(raw.predicted_repair_days),
    prob_low: toFiniteNumber(raw.prob_low),
    prob_medium: toFiniteNumber(raw.prob_medium),
    prob_high: toFiniteNumber(raw.prob_high),
    prob_critical: toFiniteNumber(raw.prob_critical),
    repair_eta: (() => {
      const days = toFiniteNumber(raw.fix_days_estimate) ?? toFiniteNumber(raw.predicted_repair_days);
      if (days == null || days <= 0) return null;
      const start = raw.created_date ? new Date(raw.created_date as string) : new Date();
      if (Number.isNaN(start.getTime())) return null;
      return new Date(start.getTime() + days * 86400000).toISOString();
    })(),
    created_date: sanitizeText(typeof raw.created_date === "string" ? raw.created_date : null),
    closed_date: sanitizeText(typeof raw.closed_date === "string" ? raw.closed_date : null),
  };
}

export function predictPothole(payload: PredictRequest) {
  return fetchAPI<Record<string, unknown>>("/predict", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

import { fetchAPI } from "./client";
import type {
  PotholeDetail,
  PotholeFeatureCollection,
  PotholeFilters,
  PredictRequest,
} from "../types";

function buildQuery(params: PotholeFilters): string {
  const search = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  });

  const query = search.toString();
  return query ? `?${query}` : "";
}

export function getPotholesGeoJSON(
  params: PotholeFilters = {},
): Promise<PotholeFeatureCollection> {
  return fetchAPI<PotholeFeatureCollection>(`/potholes/geojson${buildQuery(params)}`);
}

export function getPotholeById(uniqueKey: string): Promise<PotholeDetail> {
  return fetchAPI<PotholeDetail>(`/potholes/${uniqueKey}`);
}

export function predictPothole(payload: PredictRequest) {
  return fetchAPI<Record<string, unknown>>("/predict", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

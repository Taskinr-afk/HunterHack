/**
 * Kevin — data hook
 * Wraps getPotholesGeoJSON and converts GeoJSON features → flat Pothole[]
 * so MapPage can use real data with zero UI changes.
 */

import { useQuery } from "@tanstack/react-query";
import { getPotholesGeoJSON } from "../api/potholes";
import type { Pothole, PotholeFeature, PotholeFilters } from "../../index";

export function featureToPotle(f: PotholeFeature): Pothole {
  return {
    ...f.properties,
    latitude:  f.geometry.coordinates[1],
    longitude: f.geometry.coordinates[0],
  };
}

export function usePotholes(filters: PotholeFilters = {}) {
  return useQuery({
    queryKey: ["potholes", filters],
    queryFn:  async () => {
      const fc = await getPotholesGeoJSON({ ...filters, limit: 5000 });
      return fc.features.map(featureToPotle);
    },
    staleTime: 60_000,
  });
}

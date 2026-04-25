import { useCallback, useRef, useState } from "react";
import { useMapEvents } from "react-leaflet";
import { useQuery } from "@tanstack/react-query";
import { getPotholesGeoJSON } from "../api/potholes";
import type { BoundsLike, PotholeFilters } from "../types";

interface BoundsTrackerProps {
  onBoundsChange: (bounds: BoundsLike) => void;
}

export function BoundsTracker({ onBoundsChange }: BoundsTrackerProps) {
  useMapEvents({
    moveend: (event) => onBoundsChange(event.target.getBounds()),
    zoomend: (event) => onBoundsChange(event.target.getBounds()),
  });

  return null;
}

export function useViewportPotholes(staticFilters: PotholeFilters) {
  const [bbox, setBbox] = useState<PotholeFilters | null>(null);
  const debounceTimer = useRef<number | null>(null);

  const handleBoundsChange = useCallback((bounds: BoundsLike) => {
    if (debounceTimer.current) {
      window.clearTimeout(debounceTimer.current);
    }

    debounceTimer.current = window.setTimeout(() => {
      setBbox({
        lat_min: bounds.getSouth(),
        lat_max: bounds.getNorth(),
        lng_min: bounds.getWest(),
        lng_max: bounds.getEast(),
      });
    }, 250);
  }, []);

  const params = bbox ? { ...staticFilters, ...bbox } : staticFilters;

  const query = useQuery({
    queryKey: ["potholes-geojson", params],
    queryFn: () => getPotholesGeoJSON(params),
  });

  return { query, handleBoundsChange };
}

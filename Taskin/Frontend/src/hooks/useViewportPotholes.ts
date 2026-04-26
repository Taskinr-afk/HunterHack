import { useCallback, useRef } from "react";
import { useMapEvents } from "react-leaflet";
import { useQuery } from "@tanstack/react-query";
import { getPotholesGeoJSON } from "../api/potholes";
import type { BoundsLike, PotholeFilters } from "../types";

interface BoundsTrackerProps {
  onBoundsChange: (bounds: BoundsLike) => void;
}

export function BoundsTracker({ onBoundsChange }: BoundsTrackerProps) {
  useMapEvents({
    moveend: (event: { target: { getBounds: () => BoundsLike } }) => onBoundsChange(event.target.getBounds()),
    zoomend: (event: { target: { getBounds: () => BoundsLike } }) => onBoundsChange(event.target.getBounds()),
  });
  return null;
}

export function useViewportPotholes(staticFilters: PotholeFilters) {
  const debounceTimer = useRef<number | null>(null);
  const handleBoundsChange = useCallback((_bounds: BoundsLike) => {}, []);
  const query = useQuery({
    queryKey: ["potholes-geojson", staticFilters],
    queryFn: () => getPotholesGeoJSON(staticFilters),
  });
  return { query, handleBoundsChange };
}

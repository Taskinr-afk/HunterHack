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
    moveend: (event: { target: { getBounds: () => BoundsLike } }) => onBoundsChange(event.target.getBounds()),
    zoomend: (event: { target: { getBounds: () => BoundsLike } }) => onBoundsChange(event.target.getBounds()),
  });

  return null;
}

export function useViewportPotholes(staticFilters: PotholeFilters) {
  const debounceTimer = useRef<number | null>(null);

  const handleBoundsChange = useCallback((_bounds: BoundsLike) => {
    // Bounds-based filtering is not currently supported by the backend,
    // so we just use static filters. This hook is kept for future use.
  }, []);

  const query = useQuery({
    queryKey: ["potholes-geojson", staticFilters],
    queryFn: () => getPotholesGeoJSON(staticFilters),
  });

  return { query, handleBoundsChange };
}
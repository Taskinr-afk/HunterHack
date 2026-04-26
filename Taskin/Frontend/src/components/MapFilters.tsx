import type { PotholeFilters } from "../types";
import { BOROUGHS } from "../utils/map";

interface MapFiltersProps {
  filters: PotholeFilters;
  onChange: (filters: PotholeFilters) => void;
  onUseLocation: () => void;
  locationLabel: string;
  locationStatus: string;
}

export default function MapFilters({ filters, onChange, onUseLocation, locationLabel, locationStatus }: MapFiltersProps) {
  const update = <K extends keyof PotholeFilters>(key: K, value: PotholeFilters[K]) =>
    onChange({ ...filters, [key]: value });

  return (
    <section className="filter-shell">
      <div className="filter-hero">
        <div className="eyebrow">Live browse mode</div>
        <h2 className="filter-title">NYC pothole risk intelligence</h2>
        <p className="filter-copy">3,936 potholes scored by ML risk model. Filter by borough or status — the map updates instantly.</p>
      </div>
      <div className="location-ribbon">
        <span className="location-pill">{locationLabel}</span>
        <button type="button" className="button button-secondary" onClick={onUseLocation}>
          {locationStatus === "locating" ? "Finding you..." : "Use my location"}
        </button>
      </div>
      <div className="map-filters">
        <label className="field">
          <span className="field-label">Borough</span>
          <select value={filters.borough || ""} onChange={(e) => update("borough", e.target.value || undefined)}>
            <option value="">All boroughs</option>
            {BOROUGHS.map((b) => <option key={b} value={b}>{b}</option>)}
          </select>
        </label>
        <label className="field">
          <span className="field-label">Status</span>
          <select value={filters.status || ""} onChange={(e) => update("status", (e.target.value || undefined) as PotholeFilters["status"])}>
            <option value="">All</option>
            <option value="open">Open</option>
            <option value="closed">Closed</option>
          </select>
        </label>
      </div>
    </section>
  );
}

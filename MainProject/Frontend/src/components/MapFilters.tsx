import type { PotholeFilters } from "../types";
import { BOROUGHS } from "../utils/map";

interface MapFiltersProps {
  filters: PotholeFilters;
  onChange: (filters: PotholeFilters) => void;
  onUseLocation: () => void;
  locationLabel: string;
  locationStatus: string;
}

const STATUS_OPTIONS: Array<{ label: string; value?: PotholeFilters["status"] }> = [
  { label: "All statuses" },
  { label: "Open", value: "open" },
  { label: "Closed", value: "closed" },
  { label: "Unverified", value: "unverified" },
];

export default function MapFilters({
  filters,
  onChange,
  onUseLocation,
  locationLabel,
  locationStatus,
}: MapFiltersProps) {
  const update = <K extends keyof PotholeFilters>(key: K, value: PotholeFilters[K]) => {
    onChange({ ...filters, [key]: value });
  };

  return (
    <section className="panel-filter-block">
      <div className="panel-filter-copy">
        <span className="eyebrow">Map controls</span>
        <p className="panel-filter-note">
          Keep the live map in full view while the left rail filters the city underneath it.
        </p>
      </div>

      <div className="panel-location-row">
        <span className="location-pill">{locationLabel}</span>
        <button
          type="button"
          className="button button-secondary panel-locate-button"
          onClick={onUseLocation}
        >
          {locationStatus === "locating" ? "Locating..." : "Use my location"}
        </button>
      </div>

      <div className="filter-chip-section">
        <span className="filter-chip-heading">Borough</span>
        <div className="filter-chip-group">
          <button
            type="button"
            className={!filters.borough ? "filter-chip filter-chip-active" : "filter-chip"}
            onClick={() => update("borough", undefined)}
          >
            All boroughs
          </button>
          {BOROUGHS.map((borough) => (
            <button
              key={borough}
              type="button"
              className={filters.borough === borough ? "filter-chip filter-chip-active" : "filter-chip"}
              onClick={() => update("borough", borough)}
            >
              {borough}
            </button>
          ))}
        </div>
      </div>

      <div className="filter-chip-section">
        <span className="filter-chip-heading">Status</span>
        <div className="filter-chip-group">
          {STATUS_OPTIONS.map((option) => (
            <button
              key={option.label}
              type="button"
              className={filters.status === option.value ? "filter-chip filter-chip-active" : "filter-chip"}
              onClick={() => update("status", option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

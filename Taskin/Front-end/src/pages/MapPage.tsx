import { useDeferredValue, useMemo, useState } from "react";
import { motion } from "framer-motion";
import MapFilters from "../components/MapFilters";
import PotholeDetail from "../components/PotholeDetail";
import PotholeMap from "../components/PotholeMap";
import { useUserLocation } from "../hooks/useUserLocation";
import { mockPotholes } from "../utils/mockData";
import {
  DEFAULT_CENTER,
  formatDaysOpen,
  formatNumber,
  getDistanceMiles,
  getLocationLabel,
  getRiskColor,
  matchesFilters,
  withinBounds,
} from "../utils/map";
import type { BoundsLike, Pothole, PotholeFilters } from "../types";

interface ResultCardProps {
  pothole: Pothole;
  selected: boolean;
  distance: number;
  onSelect: (key: string) => void;
}

function ResultCard({ pothole, selected, distance, onSelect }: ResultCardProps) {
  return (
    <motion.button
      type="button"
      className={selected ? "result-card result-card-active" : "result-card"}
      onClick={() => onSelect(pothole.unique_key)}
      whileHover={{ y: -4 }}
      layout
    >
      <div className="result-card-head">
        <span className="result-address">{pothole.address}</span>
        <span className="result-distance">{distance.toFixed(1)} mi</span>
      </div>
      <div className="result-meta">
        {pothole.city} | {pothole.borough} | {pothole.zip_code}
      </div>
      <div className="result-copy">{pothole.descriptor}</div>
      <div className="result-stats">
        <span style={{ color: getRiskColor(pothole.risk_score) }}>
          Risk {pothole.risk_score?.toFixed(0) || "N/A"}
        </span>
        <span>{formatDaysOpen(pothole.days_open)}</span>
        <span>{formatNumber(pothole.traffic_volume)} cars/day</span>
      </div>
    </motion.button>
  );
}

export default function MapPage() {
  const [filters, setFilters] = useState<PotholeFilters>({});
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [bounds, setBounds] = useState<BoundsLike | null>(null);
  const { location, status, requestLocation } = useUserLocation();
  const deferredFilters = useDeferredValue(filters);

  const origin = location || DEFAULT_CENTER;

  const filtered = useMemo(
    () => mockPotholes.filter((item) => matchesFilters(item, deferredFilters)),
    [deferredFilters],
  );

  const visible = useMemo(() => {
    const inBounds = filtered.filter((item) => withinBounds(item, bounds));
    const workingSet = inBounds.length ? inBounds : filtered;

    return workingSet
      .map((item) => ({
        pothole: item,
        distance: getDistanceMiles(origin, item),
      }))
      .sort((left, right) => left.distance - right.distance);
  }, [bounds, filtered, origin]);

  const selectedPothole = mockPotholes.find((item) => item.unique_key === selectedKey) || null;

  const activeCount = visible.length;
  const highRiskCount = filtered.filter((item) => (item.risk_score || 0) >= 80).length;

  return (
    <motion.section
      className="page-stack"
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45 }}
    >
      <MapFilters
        filters={filters}
        onChange={setFilters}
        onUseLocation={requestLocation}
        locationLabel={getLocationLabel(location, status)}
        locationStatus={status}
      />

      <section className="hero-summary-grid">
        <div className="hero-metric-card">
          <span className="summary-label">Visible nearby</span>
          <strong className="summary-value">{activeCount}</strong>
        </div>
        <div className="hero-metric-card">
          <span className="summary-label">High risk in scope</span>
          <strong className="summary-value">{highRiskCount}</strong>
        </div>
        <div className="hero-metric-card">
          <span className="summary-label">Closest match</span>
          <strong className="summary-value">
            {visible[0] ? `${visible[0].distance.toFixed(1)} mi` : "--"}
          </strong>
        </div>
      </section>

      <section className="explorer-shell">
        <div className="results-column">
          <div className="results-column-head">
            <div>
              <div className="eyebrow">Nearest potholes</div>
              <h3 className="results-title">Live list follows your map viewport</h3>
            </div>
            <span className="results-caption">{filtered.length} matches after filters</span>
          </div>

          <div className="results-list">
            {visible.map(({ pothole, distance }, index) => (
              <ResultCard
                key={pothole.unique_key}
                pothole={pothole}
                selected={selectedPothole?.unique_key === pothole.unique_key || (!selectedKey && index === 0)}
                distance={distance}
                onSelect={setSelectedKey}
              />
            ))}
          </div>
        </div>

        <div className="map-column">
          <PotholeMap
            potholes={visible.slice(0, 18).map((item) => item.pothole)}
            selectedKey={selectedKey}
            onSelect={setSelectedKey}
            onBoundsChange={setBounds}
            userLocation={location}
          />
        </div>
      </section>

      <PotholeDetail pothole={selectedPothole} onClose={() => setSelectedKey(null)} />
    </motion.section>
  );
}

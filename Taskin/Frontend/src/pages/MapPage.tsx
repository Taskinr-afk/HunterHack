import { useDeferredValue, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import MapFilters from "../components/MapFilters";
import PotholeDetail from "../components/PotholeDetail";
import PotholeMap from "../components/PotholeMap";
import { useUserLocation } from "../hooks/useUserLocation";
import { getPotholesGeoJSON, getPotholeById } from "../api/potholes";
import { DEFAULT_CENTER, formatAgeDays, formatNumber, getDistanceMiles, getLocationLabel, getRiskColor, matchesFilters, withinBounds } from "../utils/map";
import { mockPotholes } from "../utils/mockData";
import type { BoundsLike, Pothole, PotholeFilters } from "../types";

const listVariants = { hidden: {}, show: { transition: { staggerChildren: 0.045 } } };
const cardVariants = { hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0, transition: { duration: 0.3, ease: [0.16, 1, 0.3, 1] } } };

function ResultCard({ pothole, selected, distance, onSelect }: { pothole: Pothole; selected: boolean; distance: number; onSelect: (key: string) => void }) {
  return (
    <motion.button type="button" variants={cardVariants} className={selected ? "result-card result-card-active" : "result-card"} onClick={() => onSelect(pothole.unique_key)} whileHover={{ y: -3 }} layout>
      <div className="result-card-head">
        <span className="result-address">{pothole.street_name || pothole.borough}</span>
        <span className="result-distance">{distance.toFixed(1)} mi</span>
      </div>
      <div className="result-meta">{pothole.borough}</div>
      <div className="result-copy">{pothole.descriptor}</div>
      <div className="result-stats">
        <span style={{ color: getRiskColor(pothole.risk_score) }}>Risk {pothole.risk_score?.toFixed(0) || "N/A"}</span>
        <span>{formatAgeDays(pothole.age_days)} open</span>
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

  const { data: potholes = [], isLoading } = useQuery({
    queryKey: ["potholes-geojson", deferredFilters],
    queryFn: async () => { try { const data = await getPotholesGeoJSON(deferredFilters); return data.length > 0 ? data : mockPotholes; } catch { return mockPotholes; } },
  });

  const { data: selectedDetail } = useQuery({
    queryKey: ["pothole-detail", selectedKey],
    queryFn: () => getPotholeById(selectedKey!),
    enabled: !!selectedKey,
  });

  const filtered = useMemo(() => potholes.filter((p) => matchesFilters(p, deferredFilters)), [potholes, deferredFilters]);

  const visible = useMemo(() => {
    const inBounds = filtered.filter((p) => withinBounds(p, bounds));
    const ws = inBounds.length ? inBounds : filtered;
    return ws.map((p) => ({ pothole: p, distance: getDistanceMiles(origin, p) })).sort((a, b) => a.distance - b.distance);
  }, [bounds, filtered, origin]);

  const selectedPothole = selectedDetail ?? potholes.find((p) => p.unique_key === selectedKey) ?? null;
  const activeCount = visible.length;
  const highRiskCount = filtered.filter((p) => (p.risk_score || 0) >= 80).length;

  return (
    <motion.section className="page-stack" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}>
      <MapFilters filters={filters} onChange={setFilters} onUseLocation={requestLocation} locationLabel={getLocationLabel(location, status)} locationStatus={status} />
      <section className="hero-summary-grid">
        {[{ label: "Visible nearby", value: activeCount.toLocaleString() }, { label: "High risk in scope", value: highRiskCount.toLocaleString() }, { label: "Closest match", value: visible[0] ? `${visible[0].distance.toFixed(1)} mi` : "--" }].map(({ label, value }, i) => (
          <motion.div key={label} className="hero-metric-card" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08, duration: 0.35, ease: [0.16, 1, 0.3, 1] }}>
            <span className="summary-label">{label}</span>
            <strong className="summary-value">{value}</strong>
          </motion.div>
        ))}
      </section>
      <section className="explorer-shell">
        <div className="results-column">
          <div className="results-column-head">
            <div><div className="eyebrow">Nearest potholes</div><h3 className="results-title">Live list follows your map view</h3></div>
            <span className="results-caption">{filtered.length} after filters</span>
          </div>
          <motion.div className="results-list" variants={listVariants} initial="hidden" animate="show">
            {isLoading ? <div className="result-card">Loading potholes...</div> : visible.map(({ pothole, distance }, index) => (
              <ResultCard key={pothole.unique_key} pothole={pothole} selected={selectedPothole?.unique_key === pothole.unique_key || (!selectedKey && index === 0)} distance={distance} onSelect={setSelectedKey} />
            ))}
          </motion.div>
        </div>
        <div className="map-column">
          <PotholeMap potholes={visible.slice(0, 18).map((v) => v.pothole)} selectedKey={selectedKey} onSelect={setSelectedKey} onBoundsChange={setBounds} userLocation={location} />
        </div>
      </section>
      <PotholeDetail pothole={selectedPothole as Pothole | null} onClose={() => setSelectedKey(null)} />
    </motion.section>
  );
}

import { useEffect } from "react";
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from "react-leaflet";
import { motion } from "framer-motion";
import { BoundsTracker } from "../hooks/useViewportPotholes";
import {
  DEFAULT_CENTER,
  formatDaysOpen,
  getMarkerColor,
  getRiskColor,
} from "../utils/map";
import type { BoundsLike, Pothole, UserLocation } from "../types";
import "leaflet/dist/leaflet.css";

const TILE_URL = import.meta.env.VITE_TILE_URL || "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
const TILE_ATTRIBUTION = "&copy; OpenStreetMap contributors &copy; CARTO";

interface PotholeMapProps {
  potholes: Pothole[];
  selectedKey: string | null;
  onSelect: (uniqueKey: string | null) => void;
  onBoundsChange: (bounds: BoundsLike) => void;
  userLocation: UserLocation | null;
}

function MapFocusController({
  selectedPothole,
  userLocation,
}: {
  selectedPothole: Pothole | null;
  userLocation: UserLocation | null;
}) {
  const map = useMap();

  useEffect(() => {
    if (selectedPothole) {
      map.flyTo([selectedPothole.latitude, selectedPothole.longitude], 14, { duration: 0.8 });
      return;
    }

    if (userLocation) {
      map.flyTo([userLocation.latitude, userLocation.longitude], 12, { duration: 0.8 });
    }
  }, [map, selectedPothole, userLocation]);

  return null;
}

export default function PotholeMap({
  potholes,
  selectedKey,
  onSelect,
  onBoundsChange,
  userLocation,
}: PotholeMapProps) {
  const selectedPothole = potholes.find((item) => item.unique_key === selectedKey) || null;
  const center: [number, number] = userLocation
    ? [userLocation.latitude, userLocation.longitude]
    : [DEFAULT_CENTER.latitude, DEFAULT_CENTER.longitude];

  return (
    <div className="map-shell">
      <div className="map-overlay map-overlay-right">
        <div className="count-pill">{potholes.length.toLocaleString()} nearby markers</div>
      </div>

      <MapContainer center={center} zoom={11} className="leaflet-map" scrollWheelZoom>
        <TileLayer attribution={TILE_ATTRIBUTION} url={TILE_URL} />
        <BoundsTracker onBoundsChange={onBoundsChange} />
        <MapFocusController selectedPothole={selectedPothole} userLocation={userLocation} />

        {potholes.map((pothole) => {
          const color = getMarkerColor(pothole);
          const isSelected = pothole.unique_key === selectedKey;

          return (
            <CircleMarker
              key={pothole.unique_key}
              center={[pothole.latitude, pothole.longitude]}
              radius={isSelected ? 11 : pothole.risk_score && pothole.risk_score > 75 ? 8.5 : 7}
              pathOptions={{
                color,
                fillColor: color,
                fillOpacity: pothole.status === "closed" ? 0.35 : 0.88,
                weight: isSelected ? 3 : 1.5,
              }}
              eventHandlers={{
                click: () => onSelect(pothole.unique_key),
              }}
            >
              <Tooltip direction="top" offset={[0, -8]}>
                <div className="map-tooltip">
                  <div className="map-tooltip-title">{pothole.address || pothole.street_name}</div>
                  <div className="map-tooltip-copy">
                    {pothole.borough} | {formatDaysOpen(pothole.days_open)} open
                  </div>
                  <div
                    className="map-tooltip-risk"
                    style={{ color: getRiskColor(pothole.risk_score) }}
                  >
                    Risk score: {pothole.risk_score?.toFixed(0) || "N/A"}
                  </div>
                </div>
              </Tooltip>
            </CircleMarker>
          );
        })}
      </MapContainer>

      <motion.div
        className="map-legend"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <span className="legend-label">Map signal</span>
        <div className="legend-item">
          <span className="legend-dot legend-dot-green" />
          low pressure
        </div>
        <div className="legend-item">
          <span className="legend-dot legend-dot-amber" />
          watch closely
        </div>
        <div className="legend-item">
          <span className="legend-dot legend-dot-red" />
          high risk
        </div>
      </motion.div>
    </div>
  );
}

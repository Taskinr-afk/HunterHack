import { useEffect } from "react";
import L from "leaflet";
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import { motion } from "framer-motion";
import { BoundsTracker } from "../hooks/useViewportPotholes";
import {
  DEFAULT_CENTER,
  formatAgeDays,
  getMarkerColor,
  getRiskColor,
} from "../utils/map";
import type { BoundsLike, Pothole, UserLocation } from "../types";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";

const TILE_URL = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
const TILE_ATTRIBUTION = "&copy; OpenStreetMap contributors &copy; CARTO";

function createClusterIcon(cluster: L.MarkerCluster) {
  const count = cluster.getChildCount();
  let size: "sm" | "md" | "lg" = "sm";
  if (count >= 50) size = "lg";
  else if (count >= 15) size = "md";

  const dim = size === "lg" ? 52 : size === "md" ? 44 : 36;
  return L.divIcon({
    html: `<div class="cluster-icon cluster-icon-${size}"><span>${count}</span></div>`,
    className: "cluster-container",
    iconSize: L.point(dim, dim),
  });
}

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

        <MarkerClusterGroup
          chunkedLoading
          maxClusterRadius={50}
          spiderfyOnMaxZoom
          showCoverageOnHover={false}
          iconCreateFunction={createClusterIcon}
        >
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
                    <div className="map-tooltip-title">{pothole.street_name || pothole.borough}</div>
                    <div className="map-tooltip-copy">
                      {pothole.borough} | {formatAgeDays(pothole.age_days)} open
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
        </MarkerClusterGroup>
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

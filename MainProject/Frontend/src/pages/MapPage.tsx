import {
  AnimatePresence,
  motion,
  useReducedMotion,
} from "framer-motion";
import {
  startTransition,
  useDeferredValue,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useQuery } from "@tanstack/react-query";
import DataSourceBanner from "../components/DataSourceBanner";
import MapFilters from "../components/MapFilters";
import PotholeDetail from "../components/PotholeDetail";
import PotholeMap from "../components/PotholeMap";
import { getPotholeById, getPotholesGeoJSON } from "../api/potholes";
import { useUserLocation } from "../hooks/useUserLocation";
import type { BoundsLike, Pothole, PotholeFilters } from "../types";
import {
  DEFAULT_CENTER,
  formatAgeDays,
  formatBorough,
  formatNumber,
  getDistanceMiles,
  getLocationLabel,
  getRiskColor,
  getStreetLabel,
  matchesFilters,
  withinBounds,
} from "../utils/map";
import { mockPotholes } from "../utils/mockData";

interface ResultCardProps {
  pothole: Pothole;
  selected: boolean;
  distance: number;
  onSelect: (key: string) => void;
}

interface ReportDraft {
  reporterName: string;
  latitude: string;
  longitude: string;
  imageName: string;
  notes: string;
}

const RESULT_LIMIT = 100;
const DROP_LINES = Array.from({ length: 24 }, (_, index) => ({
  left: `${4 + index * 4}%`,
  height: `${14 + ((index * 7) % 16)}vh`,
  delay: (index % 8) * 0.08,
  duration: 0.9 + (index % 5) * 0.18,
  width: index % 3 === 0 ? "2px" : "1px",
}));
const EMPTY_REPORT_DRAFT: ReportDraft = {
  reporterName: "",
  latitude: "",
  longitude: "",
  imageName: "",
  notes: "",
};

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
        <span className="result-address">{getStreetLabel(pothole)}</span>
        <span className="result-distance">{distance.toFixed(1)} mi</span>
      </div>
      <div className="result-meta">{formatBorough(pothole.borough)}</div>
      <div className="result-copy">{pothole.descriptor}</div>
      <div className="result-stats">
        <span style={{ color: getRiskColor(pothole.risk_score) }}>
          Risk {pothole.risk_score?.toFixed(0) || "N/A"}
        </span>
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
  const [hasEnteredMap, setHasEnteredMap] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const [reportDraft, setReportDraft] = useState<ReportDraft>(EMPTY_REPORT_DRAFT);
  const [reportNotice, setReportNotice] = useState<string | null>(null);
  const { location, status, requestLocation } = useUserLocation();
  const deferredFilters = useDeferredValue(filters);
  const shouldReduceMotion = useReducedMotion();
  const touchStartY = useRef<number | null>(null);

  const origin = location || DEFAULT_CENTER;

  useEffect(() => {
    const previousBodyOverflow = document.body.style.overflow;
    const previousHtmlOverflow = document.documentElement.style.overflow;
    document.body.style.overflow = "hidden";
    document.documentElement.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = previousBodyOverflow;
      document.documentElement.style.overflow = previousHtmlOverflow;
    };
  }, []);

  const { data: realPotholes, isLoading, error, refetch } = useQuery({
    queryKey: ["potholes-geojson", deferredFilters],
    queryFn: () => getPotholesGeoJSON(deferredFilters),
  });

  const isMockData = !!error;
  const potholes = isMockData ? mockPotholes : (realPotholes ?? []);

  const { data: selectedDetail } = useQuery({
    queryKey: ["pothole-detail", selectedKey],
    queryFn: () => getPotholeById(selectedKey!),
    enabled: !!selectedKey,
  });

  const filtered = useMemo(
    () => potholes.filter((item) => matchesFilters(item, deferredFilters)),
    [potholes, deferredFilters],
  );

  const mapPotholes = useMemo(() => {
    const inBounds = filtered.filter((item) => withinBounds(item, bounds));
    return inBounds.length ? inBounds : filtered;
  }, [bounds, filtered]);

  const visible = useMemo(() => {
    return mapPotholes
      .map((item) => ({
        pothole: item,
        distance: getDistanceMiles(origin, item),
      }))
      .sort((left, right) => left.distance - right.distance);
  }, [mapPotholes, origin]);

  const visibleResults = useMemo(() => visible.slice(0, RESULT_LIMIT), [visible]);

  const geojsonMatch = potholes.find((item) => item.unique_key === selectedKey);
  const selectedPothole: Pothole | null = selectedDetail
    ? {
        ...geojsonMatch,
        ...selectedDetail,
        latitude: geojsonMatch?.latitude ?? selectedDetail.latitude ?? DEFAULT_CENTER.latitude,
        longitude: geojsonMatch?.longitude ?? selectedDetail.longitude ?? DEFAULT_CENTER.longitude,
      }
    : geojsonMatch ?? null;

  const activeCount = mapPotholes.length;
  const highRiskCount = filtered.filter((item) => (item.risk_score || 0) >= 80).length;
  const resultsCaption = activeCount > RESULT_LIMIT
    ? `Showing ${visibleResults.length} of ${activeCount.toLocaleString()} visible matches`
    : `${activeCount.toLocaleString()} matches after filters`;
  const closestDistance = visible[0] ? `${visible[0].distance.toFixed(1)} mi` : "--";

  const enterLiveMap = () => {
    if (hasEnteredMap) {
      return;
    }

    startTransition(() => {
      setHasEnteredMap(true);
    });
  };

  const openReportDrawer = () => {
    setSelectedKey(null);
    setReportNotice(null);
    setReportDraft((current) => ({
      ...current,
      latitude: current.latitude || (location ? location.latitude.toFixed(6) : ""),
      longitude: current.longitude || (location ? location.longitude.toFixed(6) : ""),
    }));
    setReportOpen(true);
  };

  const closeReportDrawer = () => {
    setReportOpen(false);
    setReportNotice(null);
  };

  const updateReportDraft = <K extends keyof ReportDraft>(key: K, value: ReportDraft[K]) => {
    setReportDraft((current) => ({ ...current, [key]: value }));
  };

  const handleIntroWheel = (event: React.WheelEvent<HTMLElement>) => {
    if (event.deltaY > 8) {
      event.preventDefault();
      enterLiveMap();
    }
  };

  const handleIntroTouchStart = (event: React.TouchEvent<HTMLElement>) => {
    touchStartY.current = event.touches[0]?.clientY ?? null;
  };

  const handleIntroTouchEnd = (event: React.TouchEvent<HTMLElement>) => {
    if (touchStartY.current === null) {
      return;
    }

    const endY = event.changedTouches[0]?.clientY ?? touchStartY.current;
    if (touchStartY.current - endY > 24) {
      enterLiveMap();
    }
    touchStartY.current = null;
  };

  const handleReportSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setReportNotice("Draft captured in the frontend only. Backend reporting will plug in next.");
  };

  return (
    <>
      <AnimatePresence mode="wait">
        {!hasEnteredMap ? (
          <motion.section
            key="landing"
            className="landing-page landing-page-locked"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.35 }}
            onWheel={handleIntroWheel}
            onTouchStart={handleIntroTouchStart}
            onTouchEnd={handleIntroTouchEnd}
          >
            <section className="landing-hero">
              <div className="landing-drop-field" aria-hidden="true">
                {DROP_LINES.map((line) => (
                  <span
                    key={line.left}
                    className="landing-drop-line"
                    style={{
                      left: line.left,
                      height: line.height,
                      width: line.width,
                      animationDelay: `${line.delay}s`,
                      animationDuration: `${line.duration}s`,
                    }}
                  />
                ))}
              </div>

              <motion.div
                className="landing-drop-core"
                initial={shouldReduceMotion ? undefined : { y: -180, opacity: 0, scale: 0.72 }}
                animate={shouldReduceMotion ? undefined : { y: 0, opacity: 1, scale: 1 }}
                transition={
                  shouldReduceMotion
                    ? undefined
                    : { duration: 3, ease: [0.16, 1, 0.3, 1] }
                }
              />

              <motion.div
                className="landing-copy"
                initial={shouldReduceMotion ? undefined : { y: -110, opacity: 0, scale: 0.94 }}
                animate={shouldReduceMotion ? undefined : { y: 0, opacity: 1, scale: 1 }}
                transition={
                  shouldReduceMotion
                    ? undefined
                    : { duration: 3, ease: [0.16, 1, 0.3, 1] }
                }
              >
                <span className="landing-project">PotholeIQ NYC</span>
                <h2 className="landing-question">Are you ready to spot some potholes?</h2>
                <p className="landing-subcopy">
                  Drop into the city grid, then scroll once to enter the live map and stay there.
                </p>
              </motion.div>

              <div className="landing-scroll-anchor">
                <motion.button
                  type="button"
                  className="landing-scroll-cue"
                  onClick={enterLiveMap}
                  initial={shouldReduceMotion ? undefined : { opacity: 0, y: 18 }}
                  animate={shouldReduceMotion ? undefined : { opacity: 1, y: 0 }}
                  transition={
                    shouldReduceMotion
                      ? undefined
                      : { delay: 2.25, duration: 0.7, ease: "easeOut" }
                  }
                >
                  <span>Scroll down</span>
                </motion.button>
              </div>
            </section>
          </motion.section>
        ) : (
          <motion.section
            key="live-map"
            className="page-stack page-stack-fullscreen"
            initial={{ opacity: 0, scale: 1.01 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.35 }}
          >
            <section className="fullscreen-map-shell">
              <DataSourceBanner isMock={isMockData} onRetry={() => refetch()} />

              <div className="floating-data-panel">
                <div className="floating-data-panel-head">
                  <div>
                    <div className="eyebrow">Street intelligence</div>
                    <h3 className="floating-data-title">Live borough risk rail</h3>
                  </div>
                  <button
                    type="button"
                    className="button button-danger floating-report-trigger"
                    onClick={openReportDrawer}
                  >
                    Report pothole
                  </button>
                </div>

                <div className="floating-panel-summary">
                  <div className="floating-stat">
                    <span className="summary-label">Nearby</span>
                    <strong className="summary-value">{activeCount.toLocaleString()}</strong>
                  </div>
                  <div className="floating-stat">
                    <span className="summary-label">High risk</span>
                    <strong className="summary-value">{highRiskCount.toLocaleString()}</strong>
                  </div>
                  <div className="floating-stat">
                    <span className="summary-label">Closest</span>
                    <strong className="summary-value">{closestDistance}</strong>
                  </div>
                </div>

                <MapFilters
                  filters={filters}
                  onChange={setFilters}
                  onUseLocation={requestLocation}
                  locationLabel={getLocationLabel(location, status)}
                  locationStatus={status}
                />

                <div className="floating-panel-feed-head">
                  <div>
                    <div className="eyebrow">Viewport feed</div>
                    <div className="floating-panel-feed-title">Live pothole list</div>
                  </div>
                  <span className="floating-data-caption">{resultsCaption}</span>
                </div>

                <div className="floating-data-list">
                  {isLoading ? (
                    <div className="floating-data-loading">
                      <div className="spinner" style={{ margin: "0 auto 0.5rem" }} />
                      <span className="status-copy">Loading live potholes...</span>
                    </div>
                  ) : visibleResults.map(({ pothole, distance }, index) => (
                    <ResultCard
                      key={pothole.unique_key}
                      pothole={pothole}
                      selected={
                        selectedPothole?.unique_key === pothole.unique_key ||
                        (!selectedKey && index === 0)
                      }
                      distance={distance}
                      onSelect={setSelectedKey}
                    />
                  ))}
                </div>
              </div>

              <PotholeMap
                potholes={mapPotholes}
                selectedKey={selectedKey}
                onSelect={setSelectedKey}
                onBoundsChange={setBounds}
                userLocation={location}
              />
            </section>

            <PotholeDetail pothole={selectedPothole as Pothole | null} onClose={() => setSelectedKey(null)} />
          </motion.section>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {reportOpen ? (
          <>
            <motion.button
              type="button"
              className="report-backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={closeReportDrawer}
              aria-label="Close report panel"
            />

            <motion.aside
              className="report-panel"
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", stiffness: 240, damping: 28 }}
            >
              <div className="detail-header">
                <div>
                  <div className="eyebrow">Community report</div>
                  <h2>Report an unregistered pothole</h2>
                </div>
                <button type="button" className="icon-button" onClick={closeReportDrawer}>
                  Close
                </button>
              </div>

              <form className="report-form" onSubmit={handleReportSubmit}>
                <label className="report-field">
                  <span className="field-label">Your name</span>
                  <input
                    type="text"
                    value={reportDraft.reporterName}
                    onChange={(event) => updateReportDraft("reporterName", event.target.value)}
                    placeholder="Reporter name"
                  />
                </label>

                <div className="report-field-grid">
                  <label className="report-field">
                    <span className="field-label">Latitude</span>
                    <input
                      type="text"
                      value={reportDraft.latitude}
                      onChange={(event) => updateReportDraft("latitude", event.target.value)}
                      placeholder="40.712800"
                    />
                  </label>

                  <label className="report-field">
                    <span className="field-label">Longitude</span>
                    <input
                      type="text"
                      value={reportDraft.longitude}
                      onChange={(event) => updateReportDraft("longitude", event.target.value)}
                      placeholder="-74.006000"
                    />
                  </label>
                </div>

                <label className="report-field">
                  <span className="field-label">Pothole image</span>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(event) => updateReportDraft("imageName", event.target.files?.[0]?.name ?? "")}
                  />
                  <span className="report-file-meta">
                    {reportDraft.imageName || "No image selected yet"}
                  </span>
                </label>

                <label className="report-field">
                  <span className="field-label">Notes</span>
                  <textarea
                    value={reportDraft.notes}
                    onChange={(event) => updateReportDraft("notes", event.target.value)}
                    rows={6}
                    placeholder="Add street context, severity, or anything the city should know."
                  />
                </label>

                <p className="report-inline-note">
                  Frontend-only for now. The backend reporting connection will be wired in next.
                </p>

                <button type="submit" className="button button-danger button-block">
                  Save frontend draft
                </button>

                {reportNotice ? (
                  <p className="success-copy">{reportNotice}</p>
                ) : null}
              </form>
            </motion.aside>
          </>
        ) : null}
      </AnimatePresence>
    </>
  );
}

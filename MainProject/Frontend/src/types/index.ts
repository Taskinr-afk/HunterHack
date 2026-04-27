export type PotholeStatus = "open" | "closed" | "unverified";

export interface PotholeRecord {
  unique_key: string;
  borough: string;
  status: PotholeStatus;
  descriptor?: string | null;
  street_name?: string | null;
  age_days?: number | null;
  risk_score?: number | null;
  urgency_label?: string | null;
  urgency_tier?: number | null;
  nearby_crashes?: number | null;
  traffic_volume?: number | null;
  aadt?: number | null;
  fix_days_estimate?: number | null;
  accident_risk?: string | null;
  accident_risk_probability?: number | null;
  accident_probability?: number | null;
  predicted_repair_days?: number | null;
  prob_low?: number | null;
  prob_medium?: number | null;
  prob_high?: number | null;
  prob_critical?: number | null;
  created_date?: string | null;
  closed_date?: string | null;
}

export interface Pothole extends PotholeRecord {
  latitude: number;
  longitude: number;
}

export interface PotholeDetail extends PotholeRecord {
  latitude?: number | null;
  longitude?: number | null;
  repair_eta?: string | null;
}

export interface PointGeometry {
  type: "Point";
  coordinates: [number, number];
}

export interface PotholeFeature {
  type: "Feature";
  geometry: PointGeometry;
  properties: PotholeRecord & {
    pavement_crash_nearby?: number | null;
    accident_probability?: number | null;
  };
}

export interface PotholeFeatureCollection {
  type: "FeatureCollection";
  features: PotholeFeature[];
  meta?: { count?: number };
}

export interface PotholeFilters {
  borough?: string;
  status?: PotholeStatus;
  min_risk?: string;
  urgency?: string;
  limit?: number;
}

export interface BoroughStats {
  open_count: number;
  closed_count: number;
  avg_age_days: number;
  total_collisions?: number;
}

export interface StatsSummary {
  total_open: number;
  total_closed: number;
  avg_days_open: number;
  by_borough: Record<string, BoroughStats>;
}

export interface TimelinePoint {
  week: string;
  opened: number;
  closed: number;
}

export interface StatsResponse {
  summary: StatsSummary;
  timeline: TimelinePoint[];
}

export interface AlertResponse {
  id?: number | string;
  pothole_id?: string;
  sent_date?: string;
  status?: string;
  message?: string;
}

export interface AdminRefreshResponse {
  status?: string;
  rows_upserted?: number;
}

export interface PredictRequest {
  potholes: Record<string, unknown>[];
}

export interface BoundsLike {
  getSouth(): number;
  getNorth(): number;
  getWest(): number;
  getEast(): number;
}

export interface UserLocation {
  latitude: number;
  longitude: number;
  label: string;
}

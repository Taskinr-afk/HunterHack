export type PotholeStatus = "open" | "closed";

export interface PotholeRecord {
  unique_key: string;
  borough: string;
  city?: string;
  zip_code?: string;
  address?: string;
  status: PotholeStatus;
  descriptor?: string | null;
  street_name?: string | null;
  days_open?: number | null;
  risk_score?: number | null;
  impact_score?: number | null;
  nearby_collision_count?: number | null;
  traffic_volume?: number | null;
  accident_risk?: string | null;
  accident_risk_probability?: number | null;
  predicted_repair_days?: number | null;
  repair_eta?: string | null;
  created_date?: string | null;
  closed_date?: string | null;
  urgency_tier?: number | null;
}

export interface Pothole extends PotholeRecord {
  latitude: number;
  longitude: number;
}

export interface PotholeDetail extends PotholeRecord {}

export interface PointGeometry {
  type: "Point";
  coordinates: [number, number];
}

export interface PotholeFeature {
  type: "Feature";
  geometry: PointGeometry;
  properties: PotholeRecord;
}

export interface PotholeFeatureCollection {
  type: "FeatureCollection";
  features: PotholeFeature[];
}

export interface PotholeFilters {
  address?: string;
  zipCode?: string;
  city?: string;
  borough?: string;
  status?: PotholeStatus;
  min_risk?: string;
  urgency?: string;
  limit?: number;
  lat_min?: number;
  lat_max?: number;
  lng_min?: number;
  lng_max?: number;
}

export interface BoroughStats {
  open_count: number;
  closed_count: number;
  avg_days_open: number;
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
  summary?: StatsSummary;
  timeline?: TimelinePoint[];
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
  message?: string;
}

export interface PredictRequest {
  unique_key?: string;
  borough?: string;
  days_open?: number;
  nearby_collision_count?: number | null;
  traffic_volume?: number | null;
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

import type { Pothole, PotholeFilters, UserLocation } from "../types";

export const BOROUGHS = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"];

export const DEFAULT_CENTER: UserLocation = {
  latitude: 40.7128,
  longitude: -74.006,
  label: "Lower Manhattan fallback",
};

export function getMarkerColor(record: Partial<Pothole>): string {
  if (record.status === "closed") {
    return "#5fd8a7";
  }

  const risk = record.risk_score ?? 0;

  if (risk >= 80) {
    return "#ff6b57";
  }

  if (risk >= 55) {
    return "#ffb347";
  }

  return "#74e6c3";
}

export function getRiskColor(score?: number | null): string {
  if ((score ?? 0) >= 80) {
    return "#ff6b57";
  }

  if ((score ?? 0) >= 55) {
    return "#ffb347";
  }

  return "#74e6c3";
}

export function getUrgencyLabel(tier?: number | null): string {
  return {
    0: "Low",
    1: "Moderate",
    2: "High",
    3: "Critical",
  }[tier ?? -1] || "Unknown";
}

export function formatAgeDays(days?: number | null): string {
  if (days === null || days === undefined) {
    return "Unknown";
  }

  if (days === 1) {
    return "1 day";
  }

  if (days < 7) {
    return `${days} days`;
  }

  if (days < 30) {
    return `${Math.floor(days / 7)} weeks`;
  }

  return `${Math.floor(days / 30)} months`;
}

export function formatNumber(value?: number | null): string {
  if (value === null || value === undefined) {
    return "N/A";
  }

  return value.toLocaleString();
}

export function formatDate(value?: string | null): string {
  if (!value) {
    return "Unknown";
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
}

export function toRadians(value: number): number {
  return (value * Math.PI) / 180;
}

export function getDistanceMiles(
  from: Pick<UserLocation, "latitude" | "longitude">,
  to: Pick<Pothole, "latitude" | "longitude">,
): number {
  const earthRadiusMiles = 3958.8;
  const dLat = toRadians(to.latitude - from.latitude);
  const dLng = toRadians(to.longitude - from.longitude);
  const lat1 = toRadians(from.latitude);
  const lat2 = toRadians(to.latitude);

  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return earthRadiusMiles * c;
}

export function withinBounds(pothole: Pothole, bounds?: { getSouth(): number; getNorth(): number; getWest(): number; getEast(): number } | null): boolean {
  if (!bounds) {
    return true;
  }

  return (
    pothole.latitude >= bounds.getSouth() &&
    pothole.latitude <= bounds.getNorth() &&
    pothole.longitude >= bounds.getWest() &&
    pothole.longitude <= bounds.getEast()
  );
}

export function matchesFilters(pothole: Pothole, filters: PotholeFilters): boolean {
  if (filters.borough && pothole.borough !== filters.borough) {
    return false;
  }

  if (filters.status && pothole.status !== filters.status) {
    return false;
  }

  return true;
}

export function getLocationLabel(location: UserLocation | null, status: string): string {
  if (location) {
    return location.label;
  }

  if (status === "locating") {
    return "Requesting your location";
  }

  if (status === "denied") {
    return "Location denied, using NYC fallback";
  }

  return DEFAULT_CENTER.label;
}
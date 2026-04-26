import type { Pothole, StatsResponse, StatsSummary, TimelinePoint } from "../types";

type MockSeed = {
  borough: string;
  street_name: string;
  latitude: number;
  longitude: number;
  status: "open" | "closed";
  age_days: number;
  risk_score: number;
  nearby_crashes: number;
  traffic_volume: number;
};

const seeds: MockSeed[] = [
  { borough: "Manhattan", street_name: "1st Ave", latitude: 40.7312, longitude: -73.9816, status: "open", age_days: 34, risk_score: 88, nearby_crashes: 11, traffic_volume: 28750 },
  { borough: "Manhattan", street_name: "125th St", latitude: 40.8086, longitude: -73.9477, status: "open", age_days: 26, risk_score: 77, nearby_crashes: 8, traffic_volume: 23990 },
  { borough: "Manhattan", street_name: "W 36th St", latitude: 40.7501, longitude: -73.9877, status: "closed", age_days: 9, risk_score: 38, nearby_crashes: 2, traffic_volume: 19880 },
  { borough: "Brooklyn", street_name: "Flatbush Ave", latitude: 40.6767, longitude: -73.9734, status: "open", age_days: 41, risk_score: 92, nearby_crashes: 13, traffic_volume: 30120 },
  { borough: "Brooklyn", street_name: "Bedford Ave", latitude: 40.7172, longitude: -73.9563, status: "open", age_days: 18, risk_score: 64, nearby_crashes: 5, traffic_volume: 16210 },
  { borough: "Brooklyn", street_name: "Tillary St", latitude: 40.6963, longitude: -73.9866, status: "open", age_days: 12, risk_score: 54, nearby_crashes: 4, traffic_volume: 21200 },
  { borough: "Queens", street_name: "Queens Plaza S", latitude: 40.7487, longitude: -73.9388, status: "open", age_days: 22, risk_score: 71, nearby_crashes: 6, traffic_volume: 27540 },
  { borough: "Queens", street_name: "Roosevelt Ave", latitude: 40.7598, longitude: -73.8303, status: "open", age_days: 30, risk_score: 82, nearby_crashes: 9, traffic_volume: 25670 },
  { borough: "Queens", street_name: "31st St", latitude: 40.7605, longitude: -73.9273, status: "closed", age_days: 7, risk_score: 29, nearby_crashes: 2, traffic_volume: 14400 },
  { borough: "Bronx", street_name: "Grand Concourse", latitude: 40.8618, longitude: -73.8988, status: "open", age_days: 44, risk_score: 95, nearby_crashes: 15, traffic_volume: 33210 },
  { borough: "Bronx", street_name: "E 149th St", latitude: 40.8178, longitude: -73.9278, status: "open", age_days: 16, risk_score: 59, nearby_crashes: 7, traffic_volume: 22870 },
  { borough: "Bronx", street_name: "Riverdale Ave", latitude: 40.9064, longitude: -73.8963, status: "closed", age_days: 5, risk_score: 24, nearby_crashes: 1, traffic_volume: 9870 },
  { borough: "Staten Island", street_name: "Bay St", latitude: 40.6437, longitude: -74.0721, status: "open", age_days: 28, risk_score: 73, nearby_crashes: 4, traffic_volume: 11820 },
  { borough: "Staten Island", street_name: "Victory Blvd", latitude: 40.6135, longitude: -74.1442, status: "open", age_days: 13, risk_score: 48, nearby_crashes: 3, traffic_volume: 13240 },
  { borough: "Staten Island", street_name: "Hylan Blvd", latitude: 40.5679, longitude: -74.1158, status: "closed", age_days: 6, risk_score: 27, nearby_crashes: 1, traffic_volume: 14520 },
  { borough: "Manhattan", street_name: "10th Ave", latitude: 40.7615, longitude: -73.9952, status: "open", age_days: 20, risk_score: 67, nearby_crashes: 6, traffic_volume: 22150 },
  { borough: "Brooklyn", street_name: "4th Ave", latitude: 40.6705, longitude: -73.9894, status: "open", age_days: 24, risk_score: 69, nearby_crashes: 5, traffic_volume: 19400 },
  { borough: "Queens", street_name: "Junction Blvd", latitude: 40.7497, longitude: -73.8692, status: "open", age_days: 32, risk_score: 84, nearby_crashes: 10, traffic_volume: 26580 },
  { borough: "Bronx", street_name: "Bruckner Blvd", latitude: 40.8114, longitude: -73.9112, status: "open", age_days: 27, risk_score: 79, nearby_crashes: 8, traffic_volume: 24780 },
  { borough: "Brooklyn", street_name: "Broadway", latitude: 40.7014, longitude: -73.9425, status: "closed", age_days: 11, risk_score: 35, nearby_crashes: 2, traffic_volume: 17120 },
];

function buildPothole(seed: MockSeed, index: number): Pothole {
  const urgencyLabel = seed.risk_score >= 75 ? "Critical" : seed.risk_score >= 50 ? "High" : seed.risk_score >= 25 ? "Medium" : "Low";
  const urgencyTier = seed.risk_score >= 75 ? 3 : seed.risk_score >= 50 ? 2 : seed.risk_score >= 25 ? 1 : 0;
  const createdDay = (index % 20) + 1;

  return {
    unique_key: `mock-${1000 + index}`,
    borough: seed.borough,
    street_name: seed.street_name,
    latitude: seed.latitude,
    longitude: seed.longitude,
    status: seed.status,
    descriptor:
      seed.status === "open"
        ? "Surface collapse with lane vibration and standing water nearby."
        : "Recently patched section with pending quality verification.",
    age_days: seed.age_days,
    risk_score: seed.risk_score,
    urgency_label: urgencyLabel,
    urgency_tier: urgencyTier,
    nearby_crashes: seed.nearby_crashes,
    traffic_volume: seed.traffic_volume,
    accident_risk: urgencyLabel.toUpperCase(),
    accident_risk_probability: Number(Math.min(seed.risk_score / 100 + 0.05, 0.99).toFixed(2)),
    predicted_repair_days: seed.status === "open" ? Math.max(2, Math.round(seed.age_days / 5)) : 0,
    fix_days_estimate: seed.status === "open" ? Math.max(2, Math.round(seed.age_days / 5)) : 0,
    created_date: `2026-03-${String(createdDay).padStart(2, "0")}`,
    closed_date:
      seed.status === "closed"
        ? `2026-04-${String((createdDay + 10) % 28 || 1).padStart(2, "0")}`
        : null,
  };
}

export const mockPotholes: Pothole[] = seeds.map(buildPothole);

export const mockTimeline: TimelinePoint[] = [
  { week: "Mar 03", opened: 34, closed: 21 },
  { week: "Mar 10", opened: 42, closed: 25 },
  { week: "Mar 17", opened: 38, closed: 29 },
  { week: "Mar 24", opened: 49, closed: 33 },
  { week: "Mar 31", opened: 41, closed: 35 },
  { week: "Apr 07", opened: 46, closed: 40 },
  { week: "Apr 14", opened: 39, closed: 31 },
  { week: "Apr 21", opened: 52, closed: 37 },
];

export function buildMockSummary(potholes: Pothole[]): StatsSummary {
  const by_borough = potholes.reduce<StatsSummary["by_borough"]>((acc, pothole) => {
    const bucket = acc[pothole.borough] || {
      open_count: 0,
      closed_count: 0,
      avg_days_open: 0,
      total_collisions: 0 as number,
    };

    if (pothole.status === "open") {
      bucket.open_count += 1;
    } else {
      bucket.closed_count += 1;
    }

    bucket.avg_days_open += pothole.age_days || 0;
    (bucket as { total_collisions: number }).total_collisions += pothole.nearby_crashes || 0;
    acc[pothole.borough] = bucket;
    return acc;
  }, {});

  Object.values(by_borough).forEach((bucket) => {
    const total = bucket.open_count + bucket.closed_count;
    bucket.avg_days_open = total ? Number((bucket.avg_days_open / total).toFixed(1)) : 0;
  });

  const total_open = potholes.filter((item) => item.status === "open").length;
  const total_closed = potholes.length - total_open;
  const avg_days_open = Number(
    (potholes.reduce((sum, item) => sum + (item.age_days || 0), 0) / potholes.length).toFixed(1),
  );

  return {
    total_open,
    total_closed,
    avg_days_open,
    by_borough,
  };
}

export function buildMockStatsResponse(): StatsResponse {
  return {
    summary: buildMockSummary(mockPotholes),
    timeline: mockTimeline,
  };
}
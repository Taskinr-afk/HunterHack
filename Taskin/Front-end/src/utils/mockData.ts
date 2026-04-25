import type { Pothole, StatsResponse, StatsSummary, TimelinePoint } from "../types";

type MockSeed = {
  borough: Pothole["borough"];
  city: string;
  zip_code: string;
  street_name: string;
  address: string;
  latitude: number;
  longitude: number;
  status: Pothole["status"];
  days_open: number;
  risk_score: number;
  nearby_collision_count: number;
  traffic_volume: number;
};

const seeds: MockSeed[] = [
  {
    borough: "Manhattan",
    city: "New York",
    zip_code: "10003",
    street_name: "1st Ave",
    address: "245 1st Ave",
    latitude: 40.7312,
    longitude: -73.9816,
    status: "open",
    days_open: 34,
    risk_score: 88,
    nearby_collision_count: 11,
    traffic_volume: 28750,
  },
  {
    borough: "Manhattan",
    city: "New York",
    zip_code: "10027",
    street_name: "125th St",
    address: "180 W 125th St",
    latitude: 40.8086,
    longitude: -73.9477,
    status: "open",
    days_open: 26,
    risk_score: 77,
    nearby_collision_count: 8,
    traffic_volume: 23990,
  },
  {
    borough: "Manhattan",
    city: "New York",
    zip_code: "10018",
    street_name: "W 36th St",
    address: "33 W 36th St",
    latitude: 40.7501,
    longitude: -73.9877,
    status: "closed",
    days_open: 9,
    risk_score: 38,
    nearby_collision_count: 2,
    traffic_volume: 19880,
  },
  {
    borough: "Brooklyn",
    city: "Brooklyn",
    zip_code: "11217",
    street_name: "Flatbush Ave",
    address: "625 Flatbush Ave",
    latitude: 40.6767,
    longitude: -73.9734,
    status: "open",
    days_open: 41,
    risk_score: 92,
    nearby_collision_count: 13,
    traffic_volume: 30120,
  },
  {
    borough: "Brooklyn",
    city: "Brooklyn",
    zip_code: "11211",
    street_name: "Bedford Ave",
    address: "181 Bedford Ave",
    latitude: 40.7172,
    longitude: -73.9563,
    status: "open",
    days_open: 18,
    risk_score: 64,
    nearby_collision_count: 5,
    traffic_volume: 16210,
  },
  {
    borough: "Brooklyn",
    city: "Brooklyn",
    zip_code: "11201",
    street_name: "Tillary St",
    address: "345 Tillary St",
    latitude: 40.6963,
    longitude: -73.9866,
    status: "open",
    days_open: 12,
    risk_score: 54,
    nearby_collision_count: 4,
    traffic_volume: 21200,
  },
  {
    borough: "Queens",
    city: "Queens",
    zip_code: "11101",
    street_name: "Queens Plaza S",
    address: "24-02 Queens Plaza S",
    latitude: 40.7487,
    longitude: -73.9388,
    status: "open",
    days_open: 22,
    risk_score: 71,
    nearby_collision_count: 6,
    traffic_volume: 27540,
  },
  {
    borough: "Queens",
    city: "Queens",
    zip_code: "11354",
    street_name: "Roosevelt Ave",
    address: "136-19 Roosevelt Ave",
    latitude: 40.7598,
    longitude: -73.8303,
    status: "open",
    days_open: 30,
    risk_score: 82,
    nearby_collision_count: 9,
    traffic_volume: 25670,
  },
  {
    borough: "Queens",
    city: "Queens",
    zip_code: "11106",
    street_name: "31st St",
    address: "34-18 31st St",
    latitude: 40.7605,
    longitude: -73.9273,
    status: "closed",
    days_open: 7,
    risk_score: 29,
    nearby_collision_count: 2,
    traffic_volume: 14400,
  },
  {
    borough: "Bronx",
    city: "Bronx",
    zip_code: "10458",
    street_name: "Grand Concourse",
    address: "2450 Grand Concourse",
    latitude: 40.8618,
    longitude: -73.8988,
    status: "open",
    days_open: 44,
    risk_score: 95,
    nearby_collision_count: 15,
    traffic_volume: 33210,
  },
  {
    borough: "Bronx",
    city: "Bronx",
    zip_code: "10451",
    street_name: "E 149th St",
    address: "120 E 149th St",
    latitude: 40.8178,
    longitude: -73.9278,
    status: "open",
    days_open: 16,
    risk_score: 59,
    nearby_collision_count: 7,
    traffic_volume: 22870,
  },
  {
    borough: "Bronx",
    city: "Bronx",
    zip_code: "10471",
    street_name: "Riverdale Ave",
    address: "5800 Riverdale Ave",
    latitude: 40.9064,
    longitude: -73.8963,
    status: "closed",
    days_open: 5,
    risk_score: 24,
    nearby_collision_count: 1,
    traffic_volume: 9870,
  },
  {
    borough: "Staten Island",
    city: "Staten Island",
    zip_code: "10301",
    street_name: "Bay St",
    address: "125 Bay St",
    latitude: 40.6437,
    longitude: -74.0721,
    status: "open",
    days_open: 28,
    risk_score: 73,
    nearby_collision_count: 4,
    traffic_volume: 11820,
  },
  {
    borough: "Staten Island",
    city: "Staten Island",
    zip_code: "10314",
    street_name: "Victory Blvd",
    address: "1880 Victory Blvd",
    latitude: 40.6135,
    longitude: -74.1442,
    status: "open",
    days_open: 13,
    risk_score: 48,
    nearby_collision_count: 3,
    traffic_volume: 13240,
  },
  {
    borough: "Staten Island",
    city: "Staten Island",
    zip_code: "10306",
    street_name: "Hylan Blvd",
    address: "2626 Hylan Blvd",
    latitude: 40.5679,
    longitude: -74.1158,
    status: "closed",
    days_open: 6,
    risk_score: 27,
    nearby_collision_count: 1,
    traffic_volume: 14520,
  },
  {
    borough: "Manhattan",
    city: "New York",
    zip_code: "10019",
    street_name: "10th Ave",
    address: "530 10th Ave",
    latitude: 40.7615,
    longitude: -73.9952,
    status: "open",
    days_open: 20,
    risk_score: 67,
    nearby_collision_count: 6,
    traffic_volume: 22150,
  },
  {
    borough: "Brooklyn",
    city: "Brooklyn",
    zip_code: "11215",
    street_name: "4th Ave",
    address: "450 4th Ave",
    latitude: 40.6705,
    longitude: -73.9894,
    status: "open",
    days_open: 24,
    risk_score: 69,
    nearby_collision_count: 5,
    traffic_volume: 19400,
  },
  {
    borough: "Queens",
    city: "Queens",
    zip_code: "11368",
    street_name: "Junction Blvd",
    address: "95-14 Junction Blvd",
    latitude: 40.7497,
    longitude: -73.8692,
    status: "open",
    days_open: 32,
    risk_score: 84,
    nearby_collision_count: 10,
    traffic_volume: 26580,
  },
  {
    borough: "Bronx",
    city: "Bronx",
    zip_code: "10455",
    street_name: "Bruckner Blvd",
    address: "540 Bruckner Blvd",
    latitude: 40.8114,
    longitude: -73.9112,
    status: "open",
    days_open: 27,
    risk_score: 79,
    nearby_collision_count: 8,
    traffic_volume: 24780,
  },
  {
    borough: "Brooklyn",
    city: "Brooklyn",
    zip_code: "11206",
    street_name: "Broadway",
    address: "1290 Broadway",
    latitude: 40.7014,
    longitude: -73.9425,
    status: "closed",
    days_open: 11,
    risk_score: 35,
    nearby_collision_count: 2,
    traffic_volume: 17120,
  },
];

function buildPothole(seed: MockSeed, index: number): Pothole {
  const accidentRisk =
    seed.risk_score >= 80 ? "High" : seed.risk_score >= 55 ? "Medium" : "Low";
  const urgencyTier = seed.risk_score >= 85 ? 3 : seed.risk_score >= 70 ? 2 : seed.risk_score >= 45 ? 1 : 0;
  const createdDay = (index % 20) + 1;

  return {
    unique_key: `mock-${1000 + index}`,
    borough: seed.borough,
    city: seed.city,
    zip_code: seed.zip_code,
    address: seed.address,
    street_name: seed.street_name,
    latitude: seed.latitude,
    longitude: seed.longitude,
    status: seed.status,
    descriptor:
      seed.status === "open"
        ? "Surface collapse with lane vibration and standing water nearby."
        : "Recently patched section with pending quality verification.",
    days_open: seed.days_open,
    risk_score: seed.risk_score,
    impact_score: Number((seed.risk_score / 10.3).toFixed(2)),
    nearby_collision_count: seed.nearby_collision_count,
    traffic_volume: seed.traffic_volume,
    accident_risk: accidentRisk,
    accident_risk_probability: Number(Math.min(seed.risk_score / 100 + 0.05, 0.99).toFixed(2)),
    predicted_repair_days: seed.status === "open" ? Math.max(2, Math.round(seed.days_open / 5)) : 0,
    repair_eta: seed.status === "open" ? `${Math.max(2, Math.round(seed.days_open / 5))} days` : "Patched",
    created_date: `2026-03-${String(createdDay).padStart(2, "0")}`,
    closed_date:
      seed.status === "closed"
        ? `2026-04-${String((createdDay + 10) % 28 || 1).padStart(2, "0")}`
        : null,
    urgency_tier: urgencyTier,
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
      total_collisions: 0,
    };

    if (pothole.status === "open") {
      bucket.open_count += 1;
    } else {
      bucket.closed_count += 1;
    }

    bucket.avg_days_open += pothole.days_open || 0;
    bucket.total_collisions += pothole.nearby_collision_count || 0;
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
    (potholes.reduce((sum, item) => sum + (item.days_open || 0), 0) / potholes.length).toFixed(1),
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

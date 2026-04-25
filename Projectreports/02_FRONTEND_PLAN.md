# Frontend Plan — PotholeTracker NYC

> **Audience:** Beginners who just started coding. Every step is explicit with commands to run, files to create, and code to write.

---

## Phase 0: Project Setup

### Step 0.1: Install Node.js
**What:** Node.js runs JavaScript on your machine and includes npm (package manager).

**How:**
1. Go to https://nodejs.org/
2. Download the **LTS** version (long-term support)
3. Run the installer, keep all defaults
4. Verify in your terminal:
```bash
node --version    # Should show v20.x.x or v22.x.x
npm --version     # Should show 10.x.x
```

**If it doesn't work:** Close and reopen your terminal. On Windows, make sure Node is in your PATH.

---

### Step 0.2: Create the React project with Vite
**What:** Vite is a fast build tool. React is the UI library. TypeScript catches bugs before they happen.

```bash
cd ~/HunterHack
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

**Verify:**
```bash
npm run dev
# Open http://localhost:5173 — you should see the Vite + React welcome page
# Press Ctrl+C to stop the dev server
```

---

### Step 0.3: Install all frontend dependencies at once
```bash
cd ~/HunterHack/frontend

# Map library (Leaflet — free, no API key needed)
npm install react-leaflet leaflet

# Animation library
npm install framer-motion

# Charts
npm install recharts

# Data fetching (handles caching, loading, errors automatically)
npm install @tanstack/react-query

# Styling
npm install -D tailwindcss @tailwindcss/vite

# Utility for CSS class names
npm install clsx

# Date formatting
npm install date-fns
```

---

### Step 0.4: Configure Tailwind CSS
**What:** Tailwind lets you style components by adding class names directly in your HTML — no separate CSS files needed.

**How:**
```bash
# frontend/vite.config.ts
```

```typescript
// frontend/vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
});
```

```css
/* frontend/src/index.css — replace everything with: */
@import "tailwindcss";
```

**Verify:** Run `npm run dev`, the page should still load (Tailwind styles will work now).

---

### Step 0.5: Set up project folder structure
```bash
cd ~/HunterHack/frontend
mkdir -p src/{components,pages,hooks,api,types,utils}
```

Your folder structure should look like:
```
frontend/
├── public/
├── src/
│   ├── api/           ← API call functions
│   ├── components/    ← Reusable UI pieces
│   ├── hooks/         ← Custom React hooks
│   ├── pages/         ← Full page views
│   ├── types/         ← TypeScript type definitions
│   ├── utils/         ← Helper functions
│   ├── App.tsx        ← Main app component
│   ├── main.tsx       ← Entry point
│   └── index.css      ← Global styles
├── .env.example       ← Template for env vars
├── package.json
├── tailwind.config.ts
├── tsconfig.json
└── vite.config.ts
```

---

## Phase 1: TypeScript Types

### Step 1.1: Define data types
**What:** TypeScript types describe the shape of your data. They catch bugs at compile time and give you autocomplete.

**Create `frontend/src/types/index.ts`:**
```typescript
// A single pothole from our API
export interface Pothole {
  id: string;
  latitude: number;
  longitude: number;
  borough: string;
  status: "open" | "closed";
  created_date: string;
  closed_date: string | null;
  days_open: number;
  descriptor: string;
  impact_score: number | null;
}

// Detailed pothole with ML predictions
export interface PotholeDetail extends Pothole {
  nearby_collision_count: number;
  traffic_volume: number | null;
  accident_risk: "LOW" | "MEDIUM" | "HIGH";
  accident_risk_probability: number;
  predicted_repair_days: number | null;
}

// Filter parameters for the pothole list
export interface PotholeFilters {
  borough?: string;
  status?: "open" | "closed";
  limit?: number;
  offset?: number;
}

// Stats returned by /api/stats/summary
export interface StatsSummary {
  total_open: number;
  total_closed: number;
  avg_days_open: number;
  by_borough: Record<string, BoroughStats>;
}

export interface BoroughStats {
  open_count: number;
  closed_count: number;
  avg_days_open: number;
  total_collisions: number;
}

// Timeline data point
export interface TimelinePoint {
  week: string;
  opened: number;
  closed: number;
}

// Alert record
export interface Alert {
  id: number;
  pothole_id: string;
  sent_date: string;
  status: "sent" | "acknowledged" | "failed";
  message: string;
}

// Map marker color based on days open
export type MarkerColor = "critical" | "warning" | "recent" | "closed";
```

---

## Phase 2: API Layer

### Step 2.1: Create the API client
**What:** A centralized place for all backend calls. If the API URL changes, you only update it here.

**Create `frontend/src/api/client.ts`:**
```typescript
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

export { fetchAPI, API_BASE };
```

---

### Step 2.2: Create API functions for each endpoint
**Create `frontend/src/api/potholes.ts`:**
```typescript
import { fetchAPI } from "./client";
import type { Pothole, PotholeDetail, PotholeFilters } from "../types";

export async function getPotholes(filters?: PotholeFilters): Promise<Pothole[]> {
  const params = new URLSearchParams();
  if (filters?.borough) params.set("borough", filters.borough);
  if (filters?.status) params.set("status", filters.status);
  if (filters?.limit) params.set("limit", String(filters.limit));
  if (filters?.offset) params.set("offset", String(filters.offset));

  const query = params.toString() ? `?${params.toString()}` : "";
  return fetchAPI<Pothole[]>(`/api/potholes${query}`);
}

export async function getPotholeById(id: string): Promise<PotholeDetail> {
  return fetchAPI<PotholeDetail>(`/api/potholes/${id}`);
}
```

**Create `frontend/src/api/stats.ts`:**
```typescript
import { fetchAPI } from "./client";
import type { StatsSummary, TimelinePoint } from "../types";

export async function getStatsSummary(): Promise<StatsSummary> {
  return fetchAPI<StatsSummary>("/api/stats/summary");
}

export async function getStatsTimeline(): Promise<TimelinePoint[]> {
  return fetchAPI<TimelinePoint[]>("/api/stats/timeline");
}
```

**Create `frontend/src/api/alerts.ts`:**
```typescript
import { fetchAPI } from "./client";
import type { Alert } from "../types";

export async function getAlertHistory(): Promise<Alert[]> {
  return fetchAPI<Alert[]>("/api/alerts/history");
}

export async function sendAlert(potholeId: string): Promise<Alert> {
  return fetchAPI<Alert>("/api/alerts/send", {
    method: "POST",
    body: JSON.stringify({ pothole_id: potholeId }),
  });
}
```

---

### Step 2.3: Set up React Query
**What:** React Query handles loading states, error states, caching, and auto-refreshing — so you don't have to.

**Edit `frontend/src/main.tsx`:**
```typescript
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,     // Data is fresh for 5 minutes
      retry: 2,                        // Retry failed requests twice
      refetchOnWindowFocus: false,     // Don't refetch when user switches tabs
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>
);
```

---

## Phase 3: Map Component

### Step 3.1: Create the Map component
**What:** The main map showing all potholes as colored dots.

**Create `frontend/src/components/PotholeMap.tsx`:**
```typescript
import { useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Tooltip } from "react-leaflet";
import { motion, AnimatePresence } from "framer-motion";
import type { Pothole } from "../types";
import { getMarkerColor, getRiskLabel } from "../utils/map";
import PotholeTooltip from "./PotholeTooltip";
import "leaflet/dist/leaflet.css";

interface PotholeMapProps {
  potholes: Pothole[];
  isLoading: boolean;
  selectedPothole: Pothole | null;
  onSelectPothole: (pothole: Pothole | null) => void;
}

export default function PotholeMap({
  potholes,
  isLoading,
  selectedPothole,
  onSelectPothole,
}: PotholeMapProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  // NYC center coordinates
  const NYC_CENTER: [number, number] = [40.7128, -74.006];
  const DEFAULT_ZOOM = 11;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-100">
        <div className="animate-pulse text-gray-500">Loading potholes...</div>
      </div>
    );
  }

  return (
    <MapContainer
      center={NYC_CENTER}
      zoom={DEFAULT_ZOOM}
      className="h-full w-full"
      scrollWheelZoom={true}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {potholes.map((pothole) => (
        <CircleMarker
          key={pothole.id}
          center={[pothole.latitude, pothole.longitude]}
          radius={selectedPothole?.id === pothole.id ? 10 : 6}
          pathOptions={{
            color: getMarkerColor(pothole),
            fillOpacity: pothole.status === "closed" ? 0.3 : 0.8,
            weight: selectedPothole?.id === pothole.id ? 3 : 1,
          }}
          eventHandlers={{
            mouseover: () => setHoveredId(pothole.id),
            mouseout: () => setHoveredId(null),
            click: () => onSelectPothole(pothole),
          }}
        >
          <AnimatePresence>
            {hoveredId === pothole.id && (
              <Tooltip permanent={false} direction="top">
                <PotholeTooltip pothole={pothole} />
              </Tooltip>
            )}
          </AnimatePresence>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
```

---

### Step 3.2: Create marker color utility
**Create `frontend/src/utils/map.ts`:**
```typescript
import type { Pothole, MarkerColor } from "../types";

export function getMarkerColor(pothole: Pothole): string {
  if (pothole.status === "closed") return "#9ca3af"; // gray

  const days = pothole.days_open;
  if (days > 30) return "#ef4444";      // red — critical
  if (days > 14) return "#f59e0b";      // amber — warning
  return "#22c55e";                      // green — recent
}

export function getMarkerCategory(pothole: Pothole): MarkerColor {
  if (pothole.status === "closed") return "closed";
  if (pothole.days_open > 30) return "critical";
  if (pothole.days_open > 14) return "warning";
  return "recent";
}

export function getRiskLabel(risk: string): string {
  switch (risk) {
    case "HIGH": return "High Risk";
    case "MEDIUM": return "Medium Risk";
    case "LOW": return "Low Risk";
    default: return "Unknown";
  }
}

export function formatDaysOpen(days: number): string {
  if (days === 1) return "1 day";
  if (days < 7) return `${days} days`;
  if (days < 30) return `${Math.floor(days / 7)} weeks`;
  return `${Math.floor(days / 30)} months`;
}
```

---

### Step 3.3: Create the tooltip component
**Create `frontend/src/components/PotholeTooltip.tsx`:**
```typescript
import type { Pothole } from "../types";
import { formatDaysOpen, getMarkerCategory } from "../utils/map";

interface PotholeTooltipProps {
  pothole: Pothole;
}

export default function PotholeTooltip({ pothole }: PotholeTooltipProps) {
  const category = getMarkerCategory(pothole);

  return (
    <div className="text-xs min-w-[150px]">
      <div className="font-bold text-sm mb-1">
        Pothole #{pothole.id.slice(-6)}
      </div>
      <div className="text-gray-600">{pothole.borough}</div>
      <div className="mt-1">
        <span className={`inline-block w-2 h-2 rounded-full mr-1 ${
          category === "critical" ? "bg-red-500" :
          category === "warning" ? "bg-amber-500" :
          category === "recent" ? "bg-green-500" :
          "bg-gray-400"
        }`} />
        Open for {formatDaysOpen(pothole.days_open)}
      </div>
      {pothole.impact_score !== null && (
        <div className="mt-1 text-gray-500">
          Impact Score: {pothole.impact_score.toFixed(2)}
        </div>
      )}
    </div>
  );
}
```

---

## Phase 4: Detail Panel (Slide-in Sidebar)

### Step 4.1: Create the detail panel
**Create `frontend/src/components/PotholeDetail.tsx`:**
```typescript
import { motion } from "framer-motion";
import type { PotholeDetail } from "../types";
import { formatDaysOpen, getRiskLabel } from "../utils/map";

interface PotholeDetailProps {
  pothole: PotholeDetail;
  onClose: () => void;
  onSendAlert: (id: string) => void;
  isSendingAlert: boolean;
}

export default function PotholeDetail({
  pothole,
  onClose,
  onSendAlert,
  isSendingAlert,
}: PotholeDetailProps) {
  return (
    <motion.div
      initial={{ x: "100%" }}
      animate={{ x: 0 }}
      exit={{ x: "100%" }}
      transition={{ type: "spring", damping: 25, stiffness: 200 }}
      className="absolute right-0 top-0 h-full w-96 bg-white shadow-xl z-50 overflow-y-auto"
    >
      <div className="p-6">
        {/* Header */}
        <div className="flex justify-between items-start mb-4">
          <h2 className="text-xl font-bold">Pothole #{pothole.id.slice(-6)}</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
          >
            &times;
          </button>
        </div>

        {/* Status badge */}
        <div className="mb-4">
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            pothole.status === "open"
              ? "bg-red-100 text-red-700"
              : "bg-green-100 text-green-700"
          }`}>
            {pothole.status === "open" ? "Open" : "Closed"}
          </span>
        </div>

        {/* Key metrics */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <MetricCard label="Days Open" value={formatDaysOpen(pothole.days_open)} />
          <MetricCard label="Borough" value={pothole.borough} />
          <MetricCard label="Accident Risk" value={getRiskLabel(pothole.accident_risk)} highlight={pothole.accident_risk === "HIGH"} />
          <MetricCard label="Nearby Collisions" value={String(pothole.nearby_collision_count)} />
          {pothole.traffic_volume && (
            <MetricCard label="Daily Vehicles" value={pothole.traffic_volume.toLocaleString()} />
          )}
          {pothole.predicted_repair_days && (
            <MetricCard label="Repair ETA" value={`${pothole.predicted_repair_days} days`} />
          )}
        </div>

        {/* ML Predictions section */}
        <div className="mb-6 p-4 bg-blue-50 rounded-lg">
          <h3 className="font-semibold text-blue-900 mb-2">ML Predictions</h3>
          <div className="space-y-1 text-sm text-blue-800">
            <p>Accident Risk: <strong>{getRiskLabel(pothole.accident_risk)}</strong> ({(pothole.accident_risk_probability * 100).toFixed(1)}%)</p>
            {pothole.predicted_repair_days && (
              <p>Estimated Repair: <strong>{pothole.predicted_repair_days} days</strong></p>
            )}
            {pothole.impact_score !== null && (
              <p>Impact Score: <strong>{pothole.impact_score.toFixed(2)}</strong></p>
            )}
          </div>
        </div>

        {/* Alert button */}
        {pothole.status === "open" && (
          <button
            onClick={() => onSendAlert(pothole.id)}
            disabled={isSendingAlert}
            className="w-full py-3 bg-red-600 text-white rounded-lg font-semibold hover:bg-red-700 disabled:opacity-50 transition-colors"
          >
            {isSendingAlert ? "Sending Alert..." : "Alert DOT Department"}
          </button>
        )}

        {/* Description */}
        <div className="mt-6">
          <h3 className="font-semibold mb-2">Description</h3>
          <p className="text-gray-600 text-sm">{pothole.descriptor}</p>
        </div>

        {/* Dates */}
        <div className="mt-4 text-sm text-gray-500">
          <p>Opened: {new Date(pothole.created_date).toLocaleDateString()}</p>
          {pothole.closed_date && (
            <p>Closed: {new Date(pothole.closed_date).toLocaleDateString()}</p>
          )}
        </div>
      </div>
    </motion.div>
  );
}

function MetricCard({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className={`p-3 rounded-lg ${highlight ? "bg-red-50" : "bg-gray-50"}`}>
      <div className="text-xs text-gray-500">{label}</div>
      <div className={`text-lg font-bold ${highlight ? "text-red-600" : "text-gray-900"}`}>
        {value}
      </div>
    </div>
  );
}
```

---

## Phase 5: Dashboard Page

### Step 5.1: Create the dashboard with stats and charts
**Create `frontend/src/pages/Dashboard.tsx`:**
```typescript
import { useQuery } from "@tanstack/react-query";
import { getStatsSummary, getStatsTimeline } from "../api/stats";
import type { StatsSummary } from "../types";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";

export default function Dashboard() {
  const { data: summary, isLoading: loadingSummary } = useQuery({
    queryKey: ["stats-summary"],
    queryFn: getStatsSummary,
  });

  const { data: timeline } = useQuery({
    queryKey: ["stats-timeline"],
    queryFn: getStatsTimeline,
  });

  if (loadingSummary || !summary) {
    return <div className="p-8 animate-pulse">Loading dashboard...</div>;
  }

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <h1 className="text-3xl font-bold mb-8">NYC Pothole Dashboard</h1>

      {/* Summary cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <SummaryCard
          title="Open Potholes"
          value={summary.total_open}
          color="text-red-600"
          bg="bg-red-50"
        />
        <SummaryCard
          title="Closed Potholes"
          value={summary.total_closed}
          color="text-green-600"
          bg="bg-green-50"
        />
        <SummaryCard
          title="Avg Days Open"
          value={Math.round(summary.avg_days_open)}
          color="text-amber-600"
          bg="bg-amber-50"
        />
        <SummaryCard
          title="Boroughs Tracked"
          value={Object.keys(summary.by_borough).length}
          color="text-blue-600"
          bg="bg-blue-50"
        />
      </div>

      {/* Borough breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-white rounded-xl shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Potholes by Borough</h2>
          <div className="space-y-3">
            {Object.entries(summary.by_borough).map(([borough, stats]) => (
              <BoroughBar key={borough} name={borough} stats={stats} />
            ))}
          </div>
        </div>

        {/* Timeline chart */}
        <div className="bg-white rounded-xl shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Potholes Opened vs Closed (Weekly)</h2>
          {timeline && (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={timeline}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="week" tick={{ fontSize: 12 }} />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="opened" fill="#ef4444" name="Opened" />
                <Bar dataKey="closed" fill="#22c55e" name="Closed" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}

function SummaryCard({ title, value, color, bg }: {
  title: string; value: number; color: string; bg: string;
}) {
  return (
    <div className={`${bg} rounded-xl p-6`}>
      <div className="text-sm text-gray-600">{title}</div>
      <div className={`text-3xl font-bold ${color}`}>{value.toLocaleString()}</div>
    </div>
  );
}

function BoroughBar({ name, stats }: { name: string; stats: { open_count: number; closed_count: number; avg_days_open: number; total_collisions: number } }) {
  const total = stats.open_count + stats.closed_count;
  const openPercent = total > 0 ? (stats.open_count / total) * 100 : 0;

  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="font-medium">{name}</span>
        <span className="text-gray-500">{stats.open_count} open / {stats.closed_count} closed</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className="bg-red-500 h-2 rounded-full"
          style={{ width: `${openPercent}%` }}
        />
      </div>
    </div>
  );
}
```

---

## Phase 6: Main App with Routing

### Step 6.1: Install React Router
```bash
cd ~/HunterHack/frontend
npm install react-router-dom
```

### Step 6.2: Create the main App component
**Edit `frontend/src/App.tsx`:**
```typescript
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getPotholes } from "./api/potholes";
import { getPotholeById } from "./api/potholes";
import { sendAlert } from "./api/alerts";
import PotholeMap from "./components/PotholeMap";
import PotholeDetail from "./components/PotholeDetail";
import Dashboard from "./pages/Dashboard";
import type { Pothole, PotholeDetail } from "./types";

export default function App() {
  const [selectedPotholeId, setSelectedPotholeId] = useState<string | null>(null);
  const [alertingPotholeId, setAlertingPotholeId] = useState<string | null>(null);

  // Fetch all potholes for the map
  const { data: potholes = [], isLoading } = useQuery({
    queryKey: ["potholes"],
    queryFn: () => getPotholes({ status: "open", limit: 5000 }),
  });

  // Fetch selected pothole details with ML predictions
  const { data: potholeDetail } = useQuery({
    queryKey: ["pothole-detail", selectedPotholeId],
    queryFn: () => getPotholeById(selectedPotholeId!),
    enabled: !!selectedPotholeId,
  });

  const handleSendAlert = async (potholeId: string) => {
    setAlertingPotholeId(potholeId);
    try {
      await sendAlert(potholeId);
    } finally {
      setAlertingPotholeId(null);
    }
  };

  return (
    <BrowserRouter>
      <div className="h-screen flex flex-col">
        {/* Navigation bar */}
        <nav className="bg-gray-900 text-white px-6 py-3 flex items-center justify-between">
          <h1 className="text-xl font-bold">PotholeTracker NYC</h1>
          <div className="flex gap-4">
            <a href="/" className="hover:text-blue-300 transition-colors">Map</a>
            <a href="/dashboard" className="hover:text-blue-300 transition-colors">Dashboard</a>
          </div>
        </nav>

        <Routes>
          <Route path="/" element={
            <div className="flex-1 relative">
              <PotholeMap
                potholes={potholes}
                isLoading={isLoading}
                selectedPothole={potholes.find(p => p.id === selectedPotholeId) || null}
                onSelectPothole={(p) => setSelectedPotholeId(p.id)}
              />
              {potholeDetail && (
                <PotholeDetail
                  pothole={potholeDetail}
                  onClose={() => setSelectedPotholeId(null)}
                  onSendAlert={handleSendAlert}
                  isSendingAlert={alertingPotholeId === potholeDetail.id}
                />
              )}
            </div>
          } />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
```

---

## Phase 7: Loading States & Error Handling

### Step 7.1: Create loading and error components
**Create `frontend/src/components/LoadingSpinner.tsx`:**
```typescript
export default function LoadingSpinner({ message = "Loading..." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center p-12">
      <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
      <p className="mt-3 text-gray-500 text-sm">{message}</p>
    </div>
  );
}
```

**Create `frontend/src/components/ErrorMessage.tsx`:**
```typescript
interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
}

export default function ErrorMessage({ message, onRetry }: ErrorMessageProps) {
  return (
    <div className="flex flex-col items-center justify-center p-12">
      <div className="text-red-500 text-4xl mb-3">&#9888;</div>
      <p className="text-gray-700 mb-3">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
        >
          Try Again
        </button>
      )}
    </div>
  );
}
```

### Step 7.2: Add error boundaries to pages
**Update `frontend/src/pages/Dashboard.tsx`** — add error handling:
```typescript
// At the top of the Dashboard component, add error handling:
const { data: summary, isLoading: loadingSummary, error: summaryError, refetch } = useQuery({
  queryKey: ["stats-summary"],
  queryFn: getStatsSummary,
});

if (summaryError) {
  return <ErrorMessage message="Failed to load dashboard stats" onRetry={() => refetch()} />;
}
```

---

## Phase 8: Animations & Polish

### Step 8.1: Add map marker animations
**Edit `frontend/src/components/PotholeMap.tsx`** — wrap markers with motion:
```typescript
import { motion, AnimatePresence } from "framer-motion";

// In the map markers section, add initial animation:
{potholes.map((pothole, index) => (
  <CircleMarker
    key={pothole.id}
    center={[pothole.latitude, pothole.longitude]}
    radius={selectedPothole?.id === pothole.id ? 10 : 6}
    pathOptions={{
      color: getMarkerColor(pothole),
      fillOpacity: pothole.status === "closed" ? 0.3 : 0.8,
    }}
    eventHandlers={{
      mouseover: () => setHoveredId(pothole.id),
      mouseout: () => setHoveredId(null),
      click: () => onSelectPothole(pothole),
    }}
  >
    {/* Tooltip renders on hover */}
    {hoveredId === pothole.id && (
      <Tooltip permanent={false} direction="top">
        <PotholeTooltip pothole={pothole} />
      </Tooltip>
    )}
  </CircleMarker>
))}
```

### Step 8.2: Add filter controls
**Create `frontend/src/components/MapFilters.tsx`:**
```typescript
import type { PotholeFilters } from "../types";

interface MapFiltersProps {
  filters: PotholeFilters;
  onFiltersChange: (filters: PotholeFilters) => void;
}

const BOROUGHS = ["", "Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"];

export default function MapFilters({ filters, onFiltersChange }: MapFiltersProps) {
  return (
    <div className="absolute top-4 left-4 z-40 bg-white/90 backdrop-blur rounded-lg shadow-lg p-4 flex gap-3">
      <select
        value={filters.borough || ""}
        onChange={(e) => onFiltersChange({ ...filters, borough: e.target.value || undefined })}
        className="border rounded px-3 py-2 text-sm"
      >
        <option value="">All Boroughs</option>
        {BOROUGHS.slice(1).map((b) => (
          <option key={b} value={b}>{b}</option>
        ))}
      </select>

      <select
        value={filters.status || ""}
        onChange={(e) => onFiltersChange({ ...filters, status: (e.target.value || undefined) as "open" | "closed" | undefined })}
        className="border rounded px-3 py-2 text-sm"
      >
        <option value="">All Status</option>
        <option value="open">Open Only</option>
        <option value="closed">Closed Only</option>
      </select>
    </div>
  );
}
```

---

## Phase 9: Mobile Responsiveness

### Step 9.1: Responsive layout adjustments
**Key changes to make the app work on phones:**
```typescript
// In App.tsx, the detail panel should overlay on mobile:
// Replace the fixed width with responsive classes:
className="absolute right-0 top-0 h-full w-full sm:w-96 bg-white shadow-xl z-50 overflow-y-auto"

// The filter bar should stack vertically on small screens:
className="absolute top-4 left-4 z-40 bg-white/90 backdrop-blur rounded-lg shadow-lg p-4 flex flex-col sm:flex-row gap-3"

// The dashboard grid should be single-column on mobile:
className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8"  // Summary cards
className="grid grid-cols-1 lg:grid-cols-2 gap-8"        // Charts
```

---

## Phase 10: Final Build & Deploy

### Step 10.1: Test the production build locally
```bash
cd ~/HunterHack/frontend
npm run build
# This creates a "dist" folder with optimized files

# Preview the build:
npm run preview
# Open http://localhost:4173 to verify everything works
```

### Step 10.2: Deploy to Vercel
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy (follow the prompts)
cd ~/HunterHack/frontend
vercel

# For production deployment:
vercel --prod
```

**Set environment variables in Vercel dashboard:**
- `VITE_API_BASE_URL` = your backend URL (e.g., `https://pothole-tracker-api.onrender.com`)
- `VITE_MAPBOX_TOKEN` = your Mapbox public token (if using Mapbox instead of Leaflet)

---

## File Summary

After completing all steps, your `frontend/` directory should contain:

```
frontend/
├── src/
│   ├── api/
│   │   ├── client.ts          ← API base URL + fetch wrapper
│   │   ├── potholes.ts        ← Pothole API calls
│   │   ├── stats.ts           ← Stats API calls
│   │   └── alerts.ts          ← Alert API calls
│   ├── components/
│   │   ├── PotholeMap.tsx     ← Main map with markers
│   │   ├── PotholeTooltip.tsx  ← Hover tooltip
│   │   ├── PotholeDetail.tsx  ← Slide-in detail panel
│   │   ├── MapFilters.tsx     ← Borough/status dropdowns
│   │   ├── LoadingSpinner.tsx  ← Loading indicator
│   │   └── ErrorMessage.tsx   ← Error display with retry
│   ├── pages/
│   │   └── Dashboard.tsx      ← Stats dashboard with charts
│   ├── types/
│   │   └── index.ts           ← TypeScript interfaces
│   ├── utils/
│   │   └── map.ts             ← Color logic, date formatting
│   ├── App.tsx                ← Main app with routing
│   ├── main.tsx               ← Entry point with React Query
│   └── index.css              ← Tailwind import
├── .env.example               ← Template env vars
├── package.json
├── tailwind.config.ts
├── tsconfig.json
└── vite.config.ts
```

---

## Verification Checklist

After finishing all steps, verify each item:

- [ ] `npm run dev` starts without errors
- [ ] Map renders centered on NYC
- [ ] Pothole dots appear on map with correct colors
- [ ] Hovering over a dot shows a tooltip with pothole info
- [ ] Clicking a dot opens the detail panel (slides in from right)
- [ ] Detail panel shows ML predictions (accident risk, repair ETA)
- [ ] "Alert DOT" button works
- [ ] Dashboard page shows summary cards and charts
- [ ] Borough and status filters work
- [ ] Loading spinners appear while data fetches
- [ ] Error messages appear if API is down (with retry button)
- [ ] App looks good on mobile (single column layout)
- [ ] `npm run build` completes without errors
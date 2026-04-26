# Taskin — Frontend Codebase Analysis & Image Generation Guide

> Complete contextualization of the Taskin/Frontend folder for PotholeIQ NYC. This document catalogs every feature, component, data flow, and visual design pattern — then provides detailed image generation prompts for assets that would elevate the website's presentation for demo day, hackathon judging, and marketing.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Component-by-Component Breakdown](#2-component-by-component-breakdown)
3. [Data Flow & API Layer](#3-data-flow--api-layer)
4. [Visual Design System](#4-visual-design-system)
5. [Feature Inventory](#5-feature-inventory)
6. [Image Generation Prompts](#6-image-generation-prompts)

---

## 1. Architecture Overview

### Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Framework | React 18 + TypeScript | UI rendering |
| Build | Vite 5 | Dev server, HMR, production bundling |
| Routing | React Router v6 | Map (/) and Dashboard (/dashboard) pages |
| Data | TanStack React Query v5 | Server state, caching, loading/error states |
| Animation | Framer Motion 11 | Page transitions, detail panel slide-in, metric cards, legend fade-in |
| Maps | React-Leaflet 4 + Leaflet 1.9 | Interactive NYC map with CircleMarker pothole dots |
| Charts | Recharts 2.12 | Dashboard bar chart (opened vs closed per week) |
| Icons | Lucide React 0.344 | Icon library (imported but used sparingly) |
| Smooth Scroll | Lenis 1.1 | Smooth scroll behavior (imported in package.json) |
| Styling | Custom CSS (no Tailwind runtime) | Dark theme, glass-morphism, animated gradients |

### Route Structure

```
/                → MapPage (main pothole explorer)
/dashboard       → Dashboard (stats + charts)
*                → Redirect to /
```

Both routes are wrapped in `AppShell` which provides the top navigation bar, LIVE indicator, and `<Outlet />` for page content.

### Data Flow Diagram

```
NYC Open Data APIs
        │
        ▼
FastAPI Backend (localhost:8000)
   /potholes/geojson      → Pothole[] (map markers)
   /api/potholes/:id      → PotholeDetail (detail panel)
   /api/stats/summary     → StatsSummary
   /api/stats/timeline    → TimelinePoint[]
   /api/alerts/send      → AlertResponse (DOT alert)
   /admin/refresh         → AdminRefreshResponse
        │
        ▼
Vite Proxy (dev) → React Frontend
   ┌─ React Query cache (5-min stale time)
   ├─ Fallback to mockData.ts on API failure
   └─ Response transformers normalize backend → frontend types
```

### Key Design Decisions

- **Mock data fallback**: If the backend is down or returns empty data, `MapPage` and `Dashboard` fall back to `mockPotholes` and `buildMockStatsResponse()`. This ensures the demo always works.
- **Response transformers**: `api/potholes.ts` normalizes backend responses — lowercase status, computed `accident_risk_probability` from `prob_high + prob_critical`, maps `fix_days_estimate` to both `fix_days_estimate` and `predicted_repair_days`.
- **Deferred filters**: MapPage uses `useDeferredValue` for filters so rapid dropdown changes don't block the main thread.
- **Viewport-aware sorting**: Potholes within the current map bounds are sorted by distance from the user's location. If no potholes are in bounds, all filtered potholes are shown.

---

## 2. Component-by-Component Breakdown

### `AppShell.tsx` — Top Navigation Shell

**What it renders:**
- Fixed top bar with "LIVE" pulse dot indicator (animated green dot + "LIVE" text)
- Brand block: "PotholeIQ" title + "NYC Intelligence" chip
- Navigation links: "Map" and "Dashboard" with active state styling
- Scroll-aware: adds `topbar-scrolled` class when page is scrolled >24px
- `<Outlet />` renders the current route's page component

**Key behaviors:**
- `useEffect` listens to `window.scroll` to toggle the scrolled state
- NavLink uses `isActive` callback for conditional `nav-link-active` class
- No admin refresh button (unlike MainProject version)

**Visual details:**
- Dark background with glass-morphism blur effect
- Brand chip: small rounded pill with muted background
- LIVE dot: animated pulse (CSS animation)
- Nav links: pill-shaped with hover background transition

---

### `MapPage.tsx` — Main Pothole Explorer

**What it renders:**
- Filter bar with borough dropdown, status dropdown, and "Use my location" button
- Three hero metric cards: "Visible nearby", "High risk in scope", "Closest match"
- Two-column layout: results list (left) + interactive map (right)
- Clicking a pothole opens the PotholeDetail slide-in panel

**Key behaviors:**
- `useQuery` fetches `/potholes/geojson` with filter params
- Falls back to `mockPotholes` on error or empty response
- `useDeferredValue` prevents filter changes from blocking rendering
- `useQuery` for pothole detail when a marker is selected
- Distance calculation via Haversine formula (`getDistanceMiles`)
- Results sorted by distance from user location
- Map only shows up to 18 nearest markers for performance
- `useUserLocation` hook auto-requests geolocation on mount

**ResultCard sub-component:**
- Displays: street name, distance (miles), borough, risk score (color-coded), days open, traffic volume
- Hover animation: `y: -3` lift effect
- Staggered entrance animation (0.045s per card)

---

### `PotholeMap.tsx` — Interactive Leaflet Map

**What it renders:**
- Full Leaflet map with dark CARTO basemap tiles (`dark_all` style)
- CircleMarker for each pothole, colored by risk level:
  - Green (`#74e6c3`) — low risk or closed
  - Amber (`#ffb347`) — medium risk (55-79)
  - Red (`#ff6b57`) — high risk (80+) or open with score ≥80
- Marker size: 7px default, 9px for high-risk open, 12px for selected
- Tooltip on hover: street name, borough, days open, risk score
- `BoundsTracker` component updates parent on map move/zoom
- `MapFocusController` flies to selected pothole or user location
- "N markers" pill overlay showing count of visible markers
- Animated legend (Framer Motion fade-in with 0.4s delay)

**Map tiles:** CARTO dark basemap — professional dark theme that matches the overall UI

---

### `PotholeDetail.tsx` — Slide-In Detail Panel

**What it renders:**
- Backdrop overlay + slide-in panel from the right (Framer Motion spring animation)
- Header with risk-tinted gradient background (red for critical, amber for high, green for low)
- Status pill ("open" or "closed") + unique key ID
- **Risk Ring**: Animated SVG circular progress ring showing risk score 0-100
  - Glow effect via `drop-shadow` filter
  - Animated `strokeDashoffset` transition (1.1s ease)
  - Risk score number in the center
  - Subtitle: "ML-scored from age, traffic volume, and nearby crash data"
- **Metric Cards** (6 metrics in a grid):
  1. Days open
  2. Urgency (Low/Moderate/High/Critical)
  3. Nearby crashes
  4. Traffic/day
  5. Accident risk (%)
  6. Repair ETA (days)
- **Field Summary**: Street, Description, Accident risk, Opened date, Closed date
- **Send DOT Alert** button (only shown for open potholes):
  - Uses `useMutation` to call `POST /api/alerts/send`
  - Shows "Sending alert..." while pending
  - Shows success/error message after completion
  - Requires `x-api-key` header from `VITE_ADMIN_API_KEY` env var

**Visual details:**
- Risk Ring is the hero visual element — animated SVG circle with glow
- Color palette dynamically adjusts based on risk score
- Exit animation slides panel back to the right

---

### `MapFilters.tsx` — Filter Controls

**What it renders:**
- Hero section: "Live browse mode" eyebrow, "NYC pothole risk intelligence" title, descriptive copy
- Location ribbon: current location label + "Use my location" button
- Two dropdown filters:
  1. Borough: All / Manhattan / Brooklyn / Queens / Bronx / Staten Island
  2. Status: All / Open / Closed

**Key behaviors:**
- Calls `onChange` callback with updated filters
- Location button calls `onUseLocation` which triggers browser geolocation
- Location label shows: user location, "Requesting your location", "Location denied", or fallback

---

### `Dashboard.tsx` — Operations Dashboard

**What it renders:**
- Hero section: "Citywide performance" eyebrow, "Operations dashboard" title, descriptive copy
- **4 Summary Cards** (animated counting numbers via `AnimatedNumber`):
  1. Open total
  2. Closed total
  3. Avg days open
  4. Boroughs tracked
- **Two-column layout:**
  - Left: "Borough pressure" — open vs closed bar chart per borough
    - Each borough row: name, "X open · Y closed · Z collisions", animated stacked bar
    - Open portion (colored), closed portion (colored)
    - Staggered entrance animation
  - Right: "Weekly momentum" — Recharts BarChart
    - X-axis: week labels
    - Two bars per week: opened (red `#ff6b57`) and closed (green `#7af0c3`)
    - Dark tooltip with glass border
    - Grid lines in subtle white

**Key behaviors:**
- `useQuery` fetches `/api/stats/summary` + `/api/stats/timeline` in parallel
- Falls back to `buildMockStatsResponse()` on error
- `AnimatedNumber` uses Framer Motion's `useSpring` for smooth count-up animation
- Borough bars animate width from 0 to percentage

---

### `ErrorMessage.tsx` — Error State

- Red "Error" badge + error message text
- Optional "Retry" button that calls `onRetry` callback

### `LoadingSpinner.tsx` — Loading State

- CSS spinner animation + "Loading data" message (customizable)

### `useUserLocation.ts` — Geolocation Hook

- Auto-requests geolocation on mount
- States: idle, locating, ready, denied, unsupported
- Returns: `{ location, status, errorMessage, requestLocation }`

### `useViewportPotholes.ts` — Viewport Sync Hook

- `BoundsTracker` component uses `useMapEvents` to track map move/zoom
- `useViewportPotholes` fetches potholes with static filters (no live bbox query)

---

## 3. Data Flow & API Layer

### API Client (`client.ts`)

- Base URL from `VITE_API_BASE_URL` env var, defaults to `http://localhost:8000`
- `fetchAPI<T>()` — generic fetch wrapper that:
  - Sets `Content-Type: application/json`
  - Extracts error message from `message` or `detail` fields
  - Throws `Error` with the extracted message on non-OK responses
  - Handles both JSON and non-JSON response bodies

### Pothole API (`potholes.ts`)

- `getPotholesGeoJSON(params)` → `GET /potholes/geojson?status=&borough=&min_risk=&urgency=&limit=`
  - Response transformer normalizes: lowercase status, compute `accident_risk_probability`, map `fix_days_estimate` → `predicted_repair_days`
- `getPotholeById(uniqueKey)` → `GET /api/potholes/{uniqueKey}`
  - Same normalization as above
- `predictPothole(payload)` → `POST /predict`

### Stats API (`stats.ts`)

- `getStatsSummary()` → `GET /api/stats/summary`
- `getStatsTimeline()` → `GET /api/stats/timeline`
- `getCombinedStats()` → calls both in parallel, returns `{ summary, timeline }`

### Alerts API (`alerts.ts`)

- `sendAlert(potholeId, message?)` → `POST /api/alerts/send` with `x-api-key` header
- `getAlertHistory(limit)` → `GET /api/alerts/history?limit=N`
- `adminRefresh(secret)` → `POST /admin/refresh?secret=...`

### Type System (`types/index.ts`)

**Core types:**
- `PotholeRecord` — base fields from backend
- `Pothole` extends `PotholeRecord` with `latitude`, `longitude`
- `PotholeDetail` extends `PotholeRecord` (same fields, different endpoint shape)
- `PotholeFeatureCollection` — GeoJSON wrapper
- `PotholeFilters` — `{ borough?, status?, min_risk?, urgency?, limit? }`
- `StatsSummary` — `{ total_open, total_closed, avg_days_open, by_borough }`
- `StatsResponse` — `{ summary: StatsSummary, timeline: TimelinePoint[] }`
- `AlertResponse`, `AdminRefreshResponse`, `PredictRequest`

### Utility Functions (`utils/map.ts`)

- `BOROUGHS` — ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
- `DEFAULT_CENTER` — { latitude: 40.7128, longitude: -74.006, label: "Lower Manhattan fallback" }
- `getMarkerColor(record)` → green/amber/red based on risk score and status
- `getRiskColor(score)` → same color logic as marker color
- `getUrgencyLabel(tier)` → Low/Moderate/High/Critical
- `formatAgeDays(days)` → "1 day" / "3 days" / "2 weeks" / "1 month"
- `formatNumber(value)` → locale-formatted number or "N/A"
- `formatDate(value)` → locale date string or "Unknown"
- `getDistanceMiles(from, to)` — Haversine distance in miles
- `withinBounds(pothole, bounds)` — checks lat/lng within map viewport
- `matchesFilters(pothole, filters)` — borough + status filter matching
- `getLocationLabel(location, status)` — human-readable location status

---

## 4. Visual Design System

### Color Palette

| Token | Hex | Usage |
|---|---|---|
| Background | `#0b1120` (approx) | Page background, deep navy |
| Card bg | `rgba(15, 23, 42, 0.6)` | Glass cards, panels |
| Primary text | `#f1f5f9` | Headings, body text |
| Muted text | `#7a9db5` | Eyebrow labels, secondary text |
| Risk: Critical | `#ff6b57` | High risk markers, bars, alerts |
| Risk: Medium | `#ffb347` | Medium risk, amber accent |
| Risk: Low/Closed | `#74e6c3` / `#7af0c3` | Low risk, closed potholes, success |
| Accent green | `#5fd8a7` | Closed status pill |
| LIVE dot | Animated green pulse | Live indicator |

### Typography

- Font family: Inter (Google Fonts, weights 400-900)
- Brand title: Extra-bold (800-900)
- Section headings: Semi-bold (600-700)
- Body: Regular (400)
- Eyebrow labels: Uppercase, small, muted color

### Animation Patterns

| Element | Library | Animation | Duration | Easing |
|---|---|---|---|---|
| Page entrance | Framer Motion | Fade up (opacity 0→1, y 16→0) | 400ms | `[0.16, 1, 0.3, 1]` |
| Detail panel | Framer Motion | Slide from right (x 100%→0) | Spring | stiffness: 260, damping: 28 |
| Result cards | Framer Motion | Staggered fade up | 300ms, stagger 45ms | `[0.16, 1, 0.3, 1]` |
| Risk Ring | Framer Motion | SVG strokeDashoffset | 1100ms | `[0.16, 1, 0.3, 1]` |
| Borough bars | Framer Motion | Width 0→N% | 700ms | easeOut |
| Summary cards | Framer Motion | Fade up, stagger | 350ms, stagger 70ms | `[0.16, 1, 0.3, 1]` |
| Map legend | Framer Motion | Fade in from below | 0.4s delay | default |
| LIVE dot | CSS keyframes | Pulse glow | Infinite loop | — |
| Spinner | CSS keyframes | Rotating border | 0.6s linear | infinite |

### Layout Patterns

- **Top bar**: Fixed position, glass-morphism backdrop blur
- **Map page**: Two-column — results list (scrollable) + map (fixed height)
- **Detail panel**: Fixed right side, slides in over map, backdrop overlay
- **Dashboard**: Single column, responsive grid (2-col on desktop)
- **Metric cards**: Grid layout, compact with label + large number
- **Stacked bar chart**: Per-borough horizontal bars showing open vs closed ratio

---

## 5. Feature Inventory

### Fully Implemented Features

1. **Interactive NYC Pothole Map** — Leaflet with CARTO dark tiles, CircleMarkers colored by risk
2. **Pothole Explorer List** — Sorted by distance, staggered animation, risk-colored stats
3. **Pothole Detail Panel** — Slide-in with animated Risk Ring, 6 metrics, DOT alert button
4. **Borough + Status Filters** — Real-time dropdown filtering
5. **Geolocation** — Auto-request on mount, distance calculation from user position
6. **DOT Alert Sending** — POST to backend with x-api-key auth, success/error feedback
7. **Operations Dashboard** — Animated number cards, borough pressure bars, weekly timeline chart
8. **Mock Data Fallback** — Seamless fallback when backend is unavailable
9. **API Response Normalization** — Transformers handle status case, probability computation
10. **Error + Loading States** — Spinner component, error message with retry button
11. **Scroll-Aware Top Bar** — Adds visual treatment when page is scrolled
12. **LIVE Indicator** — Animated pulse dot in the header
13. **Responsive Design** — Detail panel goes full-width on mobile
14. **Risk Visualization** — Three-tier color coding (green/amber/red) throughout map, list, and detail

### Features in MainProject but NOT in Taskin/Frontend

1. **Admin Refresh Button** — MainProject has "Refresh Data" button with toast; Taskin version does not
2. **Toast Notifications** — MainProject has `.toast` CSS + state; Taskin version does not
3. **CSS File** — Taskin/Frontend has no `index.css` file (it's referenced in `main.tsx` but missing from the directory)
4. **Mock Data File** — `mockData.ts` is referenced in MapPage and Dashboard but missing from Taskin/Frontend

---

## 6. Image Generation Prompts

Below are detailed prompts for generating images that would elevate PotholeIQ's website presentation. Each prompt is designed to produce professional, hackathon-quality visuals that match the dark-theme, data-driven aesthetic of the application.

---

### 6.1 — Hero / Landing Page Banner

**Purpose:** Full-width hero image for the top of the landing page or as a splash screen before the map loads. Shows the core value proposition visually.

**Prompt:**

> A dramatic aerial nighttime view of Manhattan, New York City, looking south from Central Park toward the Financial District. The scene is rendered in a deep navy-blue color palette (#0b1120 base) with teal-green (#7af0c3) and warm amber (#ffb347) data visualization overlays. Glowing data points and heat-map circles in red (#ff6b57), amber, and green are scattered across the streets below, representing pothole locations — red circles cluster around the busiest intersections, amber on secondary streets, green on recently repaired roads. A subtle grid overlay suggests the map technology underneath. The sky has a faint digital gradient with circuit-like patterns. The overall mood is "smart city intelligence at night." No text overlays. Ultra high resolution, 16:9 aspect ratio, photorealistic with digital overlay effect.

---

### 6.2 — Risk Score Ring Visualization (Detail Panel Hero)

**Purpose:** Featured image for the Pothole Detail Panel — an isolated, high-fidelity render of the animated Risk Ring that appears when a user clicks on a pothole.

**Prompt:**

> An isolated SVG-style circular progress ring on a dark navy background (#0b1120). The ring has a diameter of approximately 84px, rendered at 4x scale for clarity. The background track circle is very subtle white at 6% opacity. The progress arc fills 87% of the circle in a vibrant red (#ff6b57) with a rounded linecap and a soft red glow/shadow emanating from the stroke. The stroke has a gradient shimmer effect. In the center of the ring, the number "87" is displayed in Inter font, bold weight 800, white color, positioned slightly above center. Below the number, the text "RISK SCORE" appears in small caps, muted teal color (#7a9db5). The overall composition is clean, minimal, and data-dashboard aesthetic. Transparent or dark background. No additional UI elements.

---

### 6.3 — Interactive Map View Screenshot Placeholder

**Purpose:** A mockup/screenshot-quality illustration of the map page in action, for use in documentation, pitch decks, or as a loading placeholder.

**Prompt:**

> A dark-themed data dashboard application interface showing an interactive map of New York City. The map uses dark CARTO basemap tiles (deep navy and muted gray tones). Scattered across Manhattan, Brooklyn, Queens, Bronx, and Staten Island are colored circle markers: red (#ff6b57) for high-risk potholes, amber (#ffb347) for medium risk, and green (#74e6c3) for low risk or closed. Several markers are clustered around major streets like Flatbush Ave, Grand Concourse, and Queens Blvd. On the left side of the screen, a scrollable results list shows pothole cards with street names, risk scores, and distance in miles. The top bar has "PotholeIQ" branding with a green pulsing "LIVE" indicator. A bottom-left legend shows the risk color key. The overall aesthetic is professional dark-mode data intelligence dashboard, similar to a cybersecurity operations center. 16:9 aspect ratio, high-fidelity UI mockup quality.

---

### 6.4 — Dashboard Analytics View

**Purpose:** Illustration of the Dashboard page showing borough statistics and the weekly timeline chart.

**Prompt:**

> A dark-themed analytics dashboard page with a deep navy background (#0b1120). At the top, a section header reads "Operations dashboard" with a smaller "Citywide performance" eyebrow label in muted teal (#7a9db5). Below it, four summary metric cards in a horizontal row display: "Open total" with number "3,936" in bright red (#ff6b57), "Closed total" with "1,247" in green (#7af0c3), "Avg days open" with "38" in white, and "Boroughs tracked" with "5" in white. Below the cards, a two-column layout: on the left, a "Borough pressure" panel showing horizontal stacked bars for each NYC borough (Manhattan, Brooklyn, Queens, Bronx, Staten Island) with red segments for open potholes and green segments for closed ones. On the right, a "Weekly momentum" bar chart with 8 weeks on the x-axis, showing paired bars in red (opened) and green (closed) per week. The chart has subtle grid lines and dark tooltips. Professional data visualization aesthetic, clean spacing, Inter font family. 16:9 aspect ratio.

---

### 6.5 — Pothole Detail Panel Illustration

**Purpose:** High-fidelity illustration of the slide-in detail panel showing all pothole data for a single pothole.

**Prompt:**

> A dark-themed slide-in detail panel from the right side of a dashboard interface. The panel has a dark navy background (#0b1120) with a subtle red-tinted gradient at the top indicating high risk. At the top, a "Pothole detail" eyebrow label and the street name "Grand Concourse" as the heading. A green "open" status pill and a "#00485271" ID tag are shown. Below, a prominent animated risk ring shows "87" in red (#ff6b57) with the label "ML-scored from age, traffic volume, and nearby crash data." Below the ring, a 3x2 grid of metric cards displays: "44 days open", "Critical urgency", "15 nearby crashes", "33,210 traffic/day", "92.3% accident risk", "9 days repair ETA". Each metric has a small label and a bold value. Further down, a "Field summary" section lists street, description, accident risk level, and dates. At the bottom, a red "Send DOT alert" button with rounded corners. The panel has a frosted glass border effect. Professional dashboard UI aesthetic. Tall portrait aspect ratio (9:16).

---

### 6.6 — Borough Pressure Stacked Bar Chart

**Purpose:** Standalone illustration of the borough comparison chart for use in presentations.

**Prompt:**

> A horizontal stacked bar chart on a dark navy background (#0b1120) showing pothole statistics for 5 NYC boroughs. Each row has: a bold borough name on the left, a metric subtitle ("X open · Y closed · Z collisions"), and a horizontal bar that is partially red (#ff6b57, representing open potholes) and partially green (#7af0c3, representing closed potholes). The bars have rounded corners and subtle glow effects. Borough order from top to bottom: Brooklyn with 1,432 open, Queens with 1,204 open, Bronx with 987 open, Manhattan with 743 open, Staten Island with 455 open. Each row has a subtle entrance animation delay indicated by a slight opacity gradient. Section header reads "Borough pressure" with an eyebrow "Open vs closed." Clean, modern data visualization style. 16:9 aspect ratio.

---

### 6.7 — Weekly Momentum Chart

**Purpose:** Standalone illustration of the Recharts bar chart showing weekly opened vs closed trends.

**Prompt:**

> A dark-themed bar chart on a navy background (#0b1120) showing 8 weeks of pothole data. The x-axis shows week labels from "Mar 03" to "Apr 21". Each week has two vertical bars side by side: a red bar (#ff6b57) for "opened" potholes and a green bar (#7af0c3) for "closed" potholes. The bars have rounded top corners (6px radius) and a subtle glow effect. Grid lines are very faint white at 6% opacity. The y-axis shows counts from 0 to 60 in steps of 10. A legend at the bottom shows red dot + "opened" and green dot + "closed". The tooltip style is dark glass with a teal border (#7af0c3 at 14% opacity) and dark navy background (rgba(7,17,28,0.95)). Chart title: "Weekly momentum" with eyebrow "Opened vs closed". Professional Recharts/data visualization aesthetic. 16:9 aspect ratio.

---

### 6.8 — Live Indicator Pulse Animation Still

**Purpose:** A still frame capture of the LIVE pulse animation for use in marketing materials, about pages, or documentation.

**Prompt:**

> A single UI element on a dark navy background (#0b1120): a small green circle (approximately 8px diameter) with a bright green glow (#7af0c3) that has a soft pulsing radiance effect — the glow expands outward in two concentric rings at different opacities, creating a "radar pulse" visual. To the right of the dot, the text "LIVE" appears in uppercase, bold Inter font, white color (#f1f5f9). The overall effect suggests real-time data streaming and monitoring. Clean, minimal, professional operations dashboard aesthetic. Square aspect ratio (1:1).

---

### 6.9 — App Icon / Logo Mark

**Purpose:** Application icon for favicon, app stores, or social media preview.

**Prompt:**

> A minimal app icon for a pothole intelligence application called "PotholeIQ." The icon features a stylized map pin marker shape (teardrop/pin silhouette) with a circular risk-score ring inside it, filled 75% in red (#ff6b57). The pin sits on top of a subtle road grid pattern. The background is deep navy (#0b1120). The overall style is flat, geometric, and modern — similar to data/AI dashboard app icons. No text. The pin shape is slightly rounded with soft shadows. Square format, 1024x1024px, suitable for app icon use.

---

### 6.10 — Social Media Preview Card (Open Graph)

**Purpose:** 1200x630 Open Graph image for link previews on Twitter, Slack, LinkedIn, etc.

**Prompt:**

> A social media preview card at 1200x630 pixels. Dark navy background (#0b1120). On the left half: the text "PotholeIQ" in large Inter font weight 900, white color. Below it: "NYC Road Intelligence" in weight 500, muted teal (#7a9db5). Below that: "Real-time pothole tracking, ML risk scoring, and DOT alert automation" in weight 400, lighter muted text. Three small horizontal metric pills showing: "3,936 tracked", "87 risk scoring", "5 boroughs" with colored accent dots. On the right half: a dark map of Manhattan and surrounding boroughs with colored circle markers (red, amber, green) representing pothole locations, with a subtle glow effect. A green pulsing "LIVE" indicator is in the top-right corner. Professional dark-mode SaaS dashboard aesthetic. No photos of real people. 1200x630 aspect ratio exactly.

---

### 6.11 — Loading State / Skeleton Screen Illustration

**Purpose:** Visual placeholder for loading states, or for documentation showing the app's loading experience.

**Prompt:**

> A dark-themed UI skeleton screen on navy background (#0b1120). The layout shows: a fixed top bar with a pulsing green LIVE dot and "PotholeIQ" text placeholder (gray rectangle). Below it, three metric card skeletons (rounded rectangles with animated shimmer gradient sweeping left to right). Below the metrics, a two-column layout: on the left, 5 list item skeletons with rounded corners and shimmer animation; on the right, a large rectangular map area skeleton with a subtle grid pattern suggesting a loading map. The shimmer effect is a gradient from transparent to rgba(255,255,255,0.04) to transparent, sweeping horizontally. Professional dashboard skeleton loading aesthetic. 16:9 aspect ratio.

---

### 6.12 — Error State Illustration

**Purpose:** Visual for the error/fallback state when the backend is unreachable.

**Prompt:**

> A dark-themed error state UI on navy background (#0b1120). In the center of the composition, a circular icon with a red (#ff6b57) exclamation mark and a subtle red glow. Below the icon, the text "Error" in a rounded pill badge with red background. Below that, the error message text "Unable to reach the server" in muted teal (#7a9db5). Below that, a rounded button with the text "Retry" in white text on a semi-transparent background with a border. The overall composition is centered, clean, and minimal. Professional error state UI for a data dashboard application. 16:9 aspect ratio.

---

### 6.13 — Mobile Responsive View

**Purpose:** Shows how the app adapts to mobile screens for documentation or pitch deck.

**Prompt:**

> A mobile phone mockup (iPhone-style, modern bezel-less) displaying the PotholeIQ pothole explorer app. The phone screen shows a dark-themed UI with: a top bar with "PotholeIQ" branding and a green LIVE dot, a filter section with borough and status dropdowns, a "Visible nearby" metric card, a scrollable list of pothole cards showing street names, risk scores (colored in red/amber/green), and distances. Below the list, a compact dark map showing colored circle markers. The overall aesthetic is dark mode data dashboard. The phone is centered against a clean dark gradient background. Portrait orientation, 9:16 aspect ratio.

---

### 6.14 — Send DOT Alert Button Illustration

**Purpose:** Close-up of the alert button interaction for documentation or onboarding.

**Prompt:**

> A close-up of a dark-themed UI card showing a "Send DOT alert" button. The button is styled with a red (#ff6b57) background, white bold text "Send DOT alert", rounded corners (8px border radius), and a subtle hover glow effect. Above the button, text reads "Status: Open" with a green status pill. The card background is dark navy (#0b1120) with a glass-morphism border. A faint red gradient radiates from the top-left corner of the card indicating high risk. Professional dashboard UI element, isolated on transparent or dark background. 3:2 aspect ratio.

---

### 6.15 — Data Flow Architecture Diagram

**Purpose:** Simplified architecture diagram for the pitch deck showing how data flows from NYC Open Data through ML to the frontend.

**Prompt:**

> A clean, modern architecture diagram on a dark navy background (#0b1120) showing a data flow. From left to right: three source icons labeled "311 Potholes", "Traffic Volume", "Motor Vehicle Collisions" connected by arrows to a central hexagon labeled "XGBoost ML Pipeline" in teal accent (#7af0c3). From the ML hexagon, an arrow points to a cylinder labeled "SQLite Database". From the database, an arrow points to a rectangle labeled "FastAPI Backend". From the backend, an arrow points to a browser window icon labeled "PotholeIQ Frontend" showing a small map with colored dots. The arrows are thin lines with subtle glow effects in teal. The icons use simple geometric shapes with rounded corners. Text is in Inter font, white for labels, teal for connections. Professional technical diagram aesthetic. 16:9 aspect ratio, landscape orientation.

---

### 6.16 — Hackathon Demo Day Banner

**Purpose:** Eye-catching banner for the HunterHack 2026 demo day presentation, combining the product name with a striking visual.

**Prompt:**

> A wide banner image for a hackathon demo day presentation. The background is a dark navy gradient (#0b1120 to #0f1a30) with a subtle hexagonal grid pattern overlay. In the center, large bold text reads "PotholeIQ" in Inter font weight 900, white color (#f1f5f9), with the "IQ" portion highlighted in teal (#7af0c3). Below it, smaller text reads "NYC Road Intelligence" in Inter weight 400, muted teal (#7a9db5). On either side of the text, stylized data visualization elements: on the left, a partial circular risk ring in red (#ff6b57) at 87% fill, and on the right, a mini bar chart with alternating red and green bars. Scattered across the background are faint circle markers in red, amber, and green suggesting pothole locations. A small tag at bottom-right reads "HunterHack 2026" in small caps. Professional, dark, data-intelligence aesthetic. 16:9 aspect ratio, high resolution.

---

*End of Taskin.md — All features contextualized, all image prompts specified.*
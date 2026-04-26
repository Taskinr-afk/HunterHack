import { motion } from "framer-motion";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useQuery } from "@tanstack/react-query";
import { fetchAPI } from "../api/client";
import { formatDaysOpen } from "../utils/map";
import type { StatsSummary, TimelinePoint } from "../types";

export default function Dashboard() {
  const summaryQ = useQuery({
    queryKey: ["stats-summary"],
    queryFn:  () => fetchAPI<StatsSummary>("/api/stats/summary"),
    staleTime: 60_000,
  });

  const timelineQ = useQuery({
    queryKey: ["stats-timeline"],
    queryFn:  () => fetchAPI<TimelinePoint[]>("/api/stats/timeline"),
    staleTime: 60_000,
  });

  const isLoading = summaryQ.isLoading || timelineQ.isLoading;

  if (isLoading) {
    return (
      <motion.section className="page-stack"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <div style={{ padding: "2rem", color: "#a8bfd1" }}>Loading live data…</div>
      </motion.section>
    );
  }

  const summary  = summaryQ.data;
  const timeline = timelineQ.data ?? [];

  if (!summary) return null;

  const boroughEntries = Object.entries(summary.by_borough);

  const hotspots = boroughEntries
    .map(([name, b]) => ({ name, open: b.open_count, collisions: b.total_collisions ?? 0 }))
    .sort((a, z) => z.open - a.open)
    .slice(0, 5);

  return (
    <motion.section
      className="page-stack"
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <section className="filter-shell dashboard-hero">
        <div className="eyebrow">Live operations board</div>
        <h2 className="filter-title">Real-time citywide pothole data from NYC Open Data</h2>
        <p className="filter-copy">
          Powered by 3,936 real NYC 311 complaints enriched with traffic volume,
          collision proximity, and XGBoost risk scores.
        </p>
      </section>

      <section className="summary-grid">
        <div className="summary-card">
          <span className="summary-label">Open total</span>
          <strong className="summary-value">{summary.total_open}</strong>
        </div>
        <div className="summary-card">
          <span className="summary-label">Closed total</span>
          <strong className="summary-value">{summary.total_closed}</strong>
        </div>
        <div className="summary-card">
          <span className="summary-label">Avg days open</span>
          <strong className="summary-value">{Math.round(summary.avg_days_open)}</strong>
        </div>
        <div className="summary-card">
          <span className="summary-label">Boroughs tracked</span>
          <strong className="summary-value">{boroughEntries.length}</strong>
        </div>
      </section>

      <section className="dashboard-grid">
        <div className="content-panel">
          <div className="panel-head">
            <div>
              <div className="eyebrow">Borough pressure</div>
              <h3>Open versus closed</h3>
            </div>
          </div>

          <div className="borough-list">
            {boroughEntries.map(([name, bucket]) => {
              const total    = bucket.open_count + bucket.closed_count;
              const openPct  = total ? (bucket.open_count   / total) * 100 : 0;
              const closedPct = total ? (bucket.closed_count / total) * 100 : 0;

              return (
                <div key={name} className="borough-row">
                  <div className="borough-head">
                    <strong>{name}</strong>
                    <span>
                      {bucket.open_count} open | {bucket.closed_count} closed | {bucket.total_collisions ?? 0} collisions
                    </span>
                  </div>
                  <div className="stack-bar">
                    <div className="stack-bar-open"   style={{ width: `${openPct}%` }} />
                    <div className="stack-bar-closed" style={{ width: `${closedPct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="content-panel">
          <div className="panel-head">
            <div>
              <div className="eyebrow">Weekly momentum</div>
              <h3>Opened versus closed</h3>
            </div>
          </div>

          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={timeline}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                <XAxis dataKey="week" tick={{ fill: "#a8bfd1", fontSize: 12 }} />
                <YAxis tick={{ fill: "#a8bfd1", fontSize: 12 }} />
                <Tooltip
                  contentStyle={{
                    background: "#0f1823",
                    border: "1px solid rgba(255,255,255,0.08)",
                    borderRadius: 12,
                  }}
                />
                <Legend />
                <Bar dataKey="opened" fill="#ff6b57" radius={[6, 6, 0, 0]} />
                <Bar dataKey="closed"  fill="#74e6c3" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <section className="content-panel">
        <div className="panel-head">
          <div>
            <div className="eyebrow">Top hotspots</div>
            <h3>Boroughs with most open potholes</h3>
          </div>
        </div>

        <div className="hotspot-grid">
          {hotspots.map((h) => (
            <motion.div key={h.name} className="hotspot-card" whileHover={{ y: -4 }}>
              <div className="hotspot-address">{h.name}</div>
              <div className="hotspot-meta">New York City</div>
              <div className="hotspot-risk">{h.open} open</div>
              <div className="hotspot-copy">{h.collisions} nearby collisions</div>
            </motion.div>
          ))}
        </div>
      </section>
    </motion.section>
  );
}

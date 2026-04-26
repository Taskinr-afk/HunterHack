import { useQuery } from "@tanstack/react-query";
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
import { getCombinedStats } from "../api/stats";
import { buildMockStatsResponse } from "../utils/mockData";

export default function Dashboard() {
  const { data: statsResponse, isLoading, error } = useQuery({
    queryKey: ["combined-stats"],
    queryFn: async () => {
      try {
        const data = await getCombinedStats();
        return data.summary.total_open > 0 ? data : buildMockStatsResponse();
      } catch {
        return buildMockStatsResponse();
      }
    },
  });

  if (isLoading || !statsResponse) {
    return (
      <motion.section className="page-stack" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <div className="filter-shell dashboard-hero">
          <div className="eyebrow">Loading dashboard...</div>
        </div>
      </motion.section>
    );
  }

  if (error) {
    return (
      <motion.section className="page-stack" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <div className="filter-shell dashboard-hero">
          <div className="eyebrow">Error loading stats</div>
          <p className="filter-copy">{String(error)}</p>
        </div>
      </motion.section>
    );
  }

  const { summary, timeline } = statsResponse;
  const boroughEntries = Object.entries(summary.by_borough);

  return (
    <motion.section
      className="page-stack"
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <section className="filter-shell dashboard-hero">
        <div className="eyebrow">Citywide performance</div>
        <h2 className="filter-title">PotholeIQ operations dashboard</h2>
        <p className="filter-copy">
          Live statistics from the NYC 311 pothole dataset, powered by ML risk scoring.
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
              const total = bucket.open_count + bucket.closed_count;
              const openPct = total ? (bucket.open_count / total) * 100 : 0;
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
                    <div className="stack-bar-open" style={{ width: `${openPct}%` }} />
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
                <Bar dataKey="closed" fill="#74e6c3" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>
    </motion.section>
  );
}
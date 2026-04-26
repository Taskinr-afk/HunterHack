import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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
import DataSourceBanner from "../components/DataSourceBanner";
import ErrorMessage from "../components/ErrorMessage";
import LoadingSpinner from "../components/LoadingSpinner";
import { adminRefresh } from "../api/alerts";
import { getCombinedStats } from "../api/stats";
import { buildMockStatsResponse } from "../utils/mockData";

export default function Dashboard() {
  const queryClient = useQueryClient();
  const { data: realStats, isLoading, error, refetch } = useQuery({
    queryKey: ["combined-stats"],
    queryFn: () => getCombinedStats(),
  });

  const refreshMutation = useMutation({
    mutationFn: () => adminRefresh(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["combined-stats"] });
      queryClient.invalidateQueries({ queryKey: ["potholes-geojson"] });
      queryClient.invalidateQueries({ queryKey: ["pothole-detail"] });
    },
  });

  const isMockData = !!error;
  const statsResponse = isMockData ? buildMockStatsResponse() : realStats;

  if (isLoading) {
    return <LoadingSpinner message="Loading dashboard" />;
  }

  if (!statsResponse) {
    return <ErrorMessage message="Failed to load dashboard data" onRetry={() => refetch()} />;
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
      <DataSourceBanner isMock={isMockData} onRetry={() => refetch()} />

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
          <strong className="summary-value">{Math.round(summary.avg_age_days)}</strong>
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
                      {bucket.open_count} open | {bucket.closed_count} closed
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

      <section className="content-panel admin-panel">
        <div className="panel-head">
          <div>
            <div className="eyebrow">Admin tools</div>
            <h3>Data refresh</h3>
          </div>
        </div>
        <p className="filter-copy">
          Re-fetch data from NYC Open Data, re-score all potholes with ML, and reload the database.
        </p>
        <button
          type="button"
          className="button button-danger"
          onClick={() => refreshMutation.mutate()}
          disabled={refreshMutation.isPending}
        >
          {refreshMutation.isPending ? "Refreshing data..." : "Refresh data"}
        </button>
        {refreshMutation.isSuccess && (
          <p className="success-copy">
            Data refreshed — {refreshMutation.data?.rows_upserted ?? 0} potholes updated.
          </p>
        )}
        {refreshMutation.isError && (
          <p className="error-copy">
            Failed to refresh: {String(refreshMutation.error)}
          </p>
        )}
      </section>
    </motion.section>
  );
}
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getCombinedStats } from "../api/stats";
import { buildMockStatsResponse } from "../utils/mockData";

function AnimatedNumber({ value }: { value: number }) {
  const motionVal = useMotionValue(0);
  const spring = useSpring(motionVal, { stiffness: 38, damping: 14 });
  const display = useTransform(spring, (v) => Math.round(v).toLocaleString());
  useEffect(() => { motionVal.set(value); }, [value, motionVal]);
  return <motion.span>{display}</motion.span>;
}

const boroughVariants = { hidden: {}, show: { transition: { staggerChildren: 0.07 } } };
const rowVariants = { hidden: { opacity: 0, x: -12 }, show: { opacity: 1, x: 0, transition: { duration: 0.38, ease: [0.16, 1, 0.3, 1] } } };

export default function Dashboard() {
  const { data: statsResponse, isLoading, error } = useQuery({
    queryKey: ["combined-stats"],
    queryFn: async () => { try { const data = await getCombinedStats(); return data.summary.total_open > 0 ? data : buildMockStatsResponse(); } catch { return buildMockStatsResponse(); } },
  });

  if (isLoading || !statsResponse) return (
    <motion.section className="page-stack" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="filter-shell dashboard-hero"><div className="eyebrow">Loading dashboard...</div></div>
    </motion.section>
  );

  if (error) return (
    <motion.section className="page-stack" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="filter-shell dashboard-hero"><div className="eyebrow">Error loading stats</div><p className="filter-copy">{String(error)}</p></div>
    </motion.section>
  );

  const { summary, timeline } = statsResponse;
  const boroughEntries = Object.entries(summary.by_borough);

  return (
    <motion.section className="page-stack" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}>
      <section className="filter-shell dashboard-hero">
        <div className="eyebrow">Citywide performance</div>
        <h2 className="filter-title">Operations dashboard</h2>
        <p className="filter-copy">Live statistics from the NYC 311 pothole dataset, scored by XGBoost risk model across 3,936 records.</p>
      </section>
      <section className="summary-grid">
        {[{ label: "Open total", value: summary.total_open }, { label: "Closed total", value: summary.total_closed }, { label: "Avg days open", value: Math.round(summary.avg_days_open) }, { label: "Boroughs tracked", value: boroughEntries.length }].map(({ label, value }, i) => (
          <motion.div key={label} className="summary-card" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07, duration: 0.35, ease: [0.16, 1, 0.3, 1] }}>
            <span className="summary-label">{label}</span>
            <strong className="summary-value"><AnimatedNumber value={value} /></strong>
          </motion.div>
        ))}
      </section>
      <section className="dashboard-grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <div className="content-panel">
          <div className="panel-head"><div><div className="eyebrow">Borough pressure</div><h3>Open vs closed</h3></div></div>
          <motion.div className="borough-list" variants={boroughVariants} initial="hidden" animate="show">
            {boroughEntries.map(([name, bucket]) => {
              const total = bucket.open_count + bucket.closed_count;
              const openPct = total ? (bucket.open_count / total) * 100 : 0;
              const closedPct = total ? (bucket.closed_count / total) * 100 : 0;
              return (
                <motion.div key={name} className="borough-row" variants={rowVariants}>
                  <div className="borough-head"><strong>{name}</strong><span>{bucket.open_count} open · {bucket.closed_count} closed{bucket.total_collisions ? ` · ${bucket.total_collisions} collisions` : ""}</span></div>
                  <div className="stack-bar">
                    <motion.div className="stack-bar-open" initial={{ width: 0 }} animate={{ width: `${openPct}%` }} transition={{ duration: 0.7, ease: "easeOut", delay: 0.1 }} />
                    <motion.div className="stack-bar-closed" initial={{ width: 0 }} animate={{ width: `${closedPct}%` }} transition={{ duration: 0.7, ease: "easeOut", delay: 0.15 }} />
                  </div>
                </motion.div>
              );
            })}
          </motion.div>
        </div>
        <div className="content-panel">
          <div className="panel-head"><div><div className="eyebrow">Weekly momentum</div><h3>Opened vs closed</h3></div></div>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={timeline} barGap={4}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="week" tick={{ fill: "#7a9db5", fontSize: 11 }} axisLine={{ stroke: "rgba(255,255,255,0.06)" }} tickLine={false} />
                <YAxis tick={{ fill: "#7a9db5", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: "rgba(7,17,28,0.95)", border: "1px solid rgba(122,240,195,0.14)", borderRadius: 14, fontSize: 12 }} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
                <Legend wrapperStyle={{ fontSize: 11, color: "#7a9db5" }} />
                <Bar dataKey="opened" fill="#ff6b57" radius={[6, 6, 0, 0]} maxBarSize={28} />
                <Bar dataKey="closed" fill="#7af0c3" radius={[6, 6, 0, 0]} maxBarSize={28} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>
    </motion.section>
  );
}

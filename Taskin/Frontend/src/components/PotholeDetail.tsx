import { AnimatePresence, motion } from "framer-motion";
import { useMutation } from "@tanstack/react-query";
import { formatDate, formatAgeDays, formatNumber, getRiskColor, getUrgencyLabel } from "../utils/map";
import { sendAlert } from "../api/alerts";
import type { Pothole } from "../types";

interface PotholeDetailProps { pothole: Pothole | null; onClose: () => void; }

function RiskRing({ score, color }: { score: number; color: string }) {
  const radius = 34;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - Math.min(Math.max(score, 0), 100) / 100);
  return (
    <svg width="84" height="84" viewBox="0 0 84 84" style={{ flexShrink: 0 }}>
      <circle cx="42" cy="42" r={radius} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="6" />
      <motion.circle cx="42" cy="42" r={radius} fill="none" stroke={color} strokeWidth="6" strokeLinecap="round"
        strokeDasharray={circumference}
        initial={{ strokeDashoffset: circumference }}
        animate={{ strokeDashoffset: offset }}
        transition={{ duration: 1.1, ease: [0.16, 1, 0.3, 1] }}
        style={{ transform: "rotate(-90deg)", transformOrigin: "42px 42px", filter: `drop-shadow(0 0 6px ${color}88)` }}
      />
      <text x="42" y="47" textAnchor="middle" fill={color} fontSize="15" fontWeight="800" fontFamily="Inter, system-ui, sans-serif">{Math.min(Math.max(score, 0), 100).toFixed(0)}</text>
    </svg>
  );
}

function MetricCard({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="metric-card">
      <span className="metric-label">{label}</span>
      <strong className="metric-value" style={tone ? { color: tone } : undefined}>{value}</strong>
    </div>
  );
}

export default function PotholeDetail({ pothole, onClose }: PotholeDetailProps) {
  const alertMutation = useMutation({ mutationFn: () => sendAlert(pothole!.unique_key) });
  const riskTone = getRiskColor(pothole?.risk_score);
  const riskScore = pothole?.risk_score ?? 0;
  const headerGradient = riskScore >= 80
    ? "linear-gradient(135deg, rgba(255,107,87,0.12), transparent 70%)"
    : riskScore >= 55
      ? "linear-gradient(135deg, rgba(255,196,102,0.1), transparent 70%)"
      : "linear-gradient(135deg, rgba(122,240,195,0.08), transparent 70%)";

  return (
    <AnimatePresence>
      {pothole ? (
        <>
          <motion.button type="button" className="detail-backdrop" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} aria-label="Close detail panel" />
          <motion.aside className="detail-panel" initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }} transition={{ type: "spring", stiffness: 260, damping: 28 }}>
            <div className="detail-header" style={{ background: headerGradient }}>
              <div>
                <div className="eyebrow">Pothole detail</div>
                <h2>{pothole.street_name || pothole.borough || "Pothole record"}</h2>
              </div>
              <button type="button" className="icon-button" onClick={onClose}>Close</button>
            </div>
            <div className="detail-scroll">
              <div className="detail-status-row">
                <span className={`status-pill status-pill-${pothole.status}`}>{pothole.status}</span>
                <span className="detail-key">#{pothole.unique_key.slice(-8)}</span>
              </div>
              <p className="detail-copy">{pothole.borough}</p>
              <div className="detail-risk-block">
                <div className="detail-risk-head">
                  <span className="eyebrow">Risk profile</span>
                  <span style={{ color: riskTone, fontSize: "0.8rem", fontWeight: 600 }}>{getUrgencyLabel(pothole.urgency_tier)}</span>
                </div>
                <div className="risk-ring-wrapper">
                  <RiskRing score={pothole.risk_score ?? 0} color={riskTone} />
                  <div className="risk-ring-info">
                    <div style={{ color: "var(--muted)", fontSize: "0.84rem", lineHeight: 1.55 }}>ML-scored from age, traffic volume, and nearby crash data.</div>
                    <div style={{ marginTop: "0.5rem", fontSize: "0.82rem", color: riskTone, fontWeight: 600 }}>{pothole.risk_score != null ? `${pothole.risk_score.toFixed(0)}/100` : "N/A"}</div>
                  </div>
                </div>
              </div>
              <div className="metric-grid">
                <MetricCard label="Days open" value={formatAgeDays(pothole.age_days)} />
                <MetricCard label="Urgency" value={getUrgencyLabel(pothole.urgency_tier)} tone={riskTone} />
                <MetricCard label="Nearby crashes" value={formatNumber(pothole.nearby_crashes)} />
                <MetricCard label="Traffic/day" value={formatNumber(pothole.traffic_volume)} />
                <MetricCard label="Accident risk" value={pothole.accident_risk_probability != null ? `${(pothole.accident_risk_probability * 100).toFixed(1)}%` : "N/A"} />
                <MetricCard label="Repair ETA" value={pothole.fix_days_estimate != null ? `${pothole.fix_days_estimate} days` : pothole.predicted_repair_days ? `${pothole.predicted_repair_days} days` : "N/A"} />
              </div>
              <div className="info-panel">
                <div className="eyebrow" style={{ marginBottom: "0.4rem" }}>Field summary</div>
                <p><strong>Street:</strong> {pothole.street_name || "Unknown"}</p>
                <p><strong>Description:</strong> {pothole.descriptor || "Pothole"}</p>
                <p><strong>Accident risk:</strong> {pothole.accident_risk || pothole.urgency_label || "Unknown"}</p>
                <p><strong>Opened:</strong> {formatDate(pothole.created_date)}</p>
                <p><strong>Closed:</strong> {formatDate(pothole.closed_date)}</p>
              </div>
              {pothole.status === "open" && (
                <motion.button type="button" className="button button-danger button-block" style={{ marginTop: "1rem" }}
                  onClick={() => alertMutation.mutate()} disabled={alertMutation.isPending}
                  whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.98 }}
                >
                  {alertMutation.isPending ? "Sending alert..." : "Send DOT alert"}
                </motion.button>
              )}
              {alertMutation.isSuccess && <p className="success-copy">Alert {alertMutation.data?.status === "sent" ? "sent" : "logged"} successfully.</p>}
              {alertMutation.isError && <p className="error-copy">Failed: {String(alertMutation.error)}</p>}
            </div>
          </motion.aside>
        </>
      ) : null}
    </AnimatePresence>
  );
}

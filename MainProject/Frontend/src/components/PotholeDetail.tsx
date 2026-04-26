import { AnimatePresence, motion } from "framer-motion";
import { useMutation } from "@tanstack/react-query";
import {
  formatDate,
  formatAgeDays,
  formatBorough,
  formatNumber,
  formatRepairEta,
  getStreetLabel,
  getRiskColor,
  getUrgencyLabel,
} from "../utils/map";
import { sendAlert } from "../api/alerts";
import type { Pothole } from "../types";

interface PotholeDetailProps {
  pothole: Pothole | null;
  onClose: () => void;
}

function MetricCard({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="metric-card">
      <span className="metric-label">{label}</span>
      <strong className="metric-value" style={tone ? { color: tone } : undefined}>
        {value}
      </strong>
    </div>
  );
}

export default function PotholeDetail({ pothole, onClose }: PotholeDetailProps) {
  const alertMutation = useMutation({
    mutationFn: () => sendAlert(pothole!.unique_key),
  });

  const riskTone = getRiskColor(pothole?.risk_score);

  return (
    <AnimatePresence>
      {pothole ? (
        <>
          <motion.button
            type="button"
            className="detail-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            aria-label="Close detail panel"
          />

          <motion.aside
            className="detail-panel"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 240, damping: 26 }}
          >
            <div className="detail-header">
              <div>
                <div className="eyebrow">Pothole detail</div>
                <h2>{getStreetLabel(pothole)}</h2>
              </div>
              <button type="button" className="icon-button" onClick={onClose}>
                Close
              </button>
            </div>

            <div className="detail-scroll">
              <div className="detail-status-row">
                <span className={`status-pill status-pill-${pothole.status}`}>{pothole.status}</span>
                <span className="detail-key">#{pothole.unique_key.slice(-8)}</span>
              </div>

              <p className="detail-copy">
                {formatBorough(pothole.borough)}
              </p>

              <div className="detail-risk-block">
                <div className="detail-risk-head">
                  <span className="eyebrow">Risk profile</span>
                  <strong style={{ color: riskTone }}>
                    {pothole.risk_score !== null && pothole.risk_score !== undefined
                      ? `${pothole.risk_score.toFixed(0)}/100`
                      : "N/A"}
                  </strong>
                </div>
                <div className="risk-bar">
                  <motion.div
                    className="risk-bar-fill"
                    style={{ backgroundColor: riskTone }}
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(pothole.risk_score || 0, 100)}%` }}
                  />
                </div>
              </div>

              <div className="metric-grid">
                <MetricCard label="Days open" value={formatAgeDays(pothole.age_days)} />
                <MetricCard
                  label="Urgency"
                  value={getUrgencyLabel(pothole.urgency_tier)}
                  tone={riskTone}
                />
                <MetricCard
                  label="Nearby crashes"
                  value={formatNumber(pothole.nearby_crashes)}
                />
                <MetricCard label="Traffic/day" value={formatNumber(pothole.traffic_volume)} />
                <MetricCard
                  label="Risk probability"
                  value={
                    pothole.accident_risk_probability !== null &&
                    pothole.accident_risk_probability !== undefined
                      ? `${(pothole.accident_risk_probability * 100).toFixed(1)}%`
                      : "N/A"
                  }
                />
                <MetricCard
                  label="Est. repair"
                  value={formatRepairEta(
                    pothole.fix_days_estimate ?? pothole.predicted_repair_days,
                    pothole.created_date,
                  )}
                />
              </div>

              <div className="info-panel">
                <div className="eyebrow">Field summary</div>
                <p>
                  <strong>Street:</strong> {getStreetLabel(pothole)}
                </p>
                <p>
                  <strong>Description:</strong> {pothole.descriptor || "No description provided"}
                </p>
                <p>
                  <strong>Accident risk:</strong> {pothole.accident_risk || pothole.urgency_label || "Unknown"}
                </p>
                <p>
                  <strong>Opened:</strong> {formatDate(pothole.created_date)}
                </p>
                <p>
                  <strong>Closed:</strong> {formatDate(pothole.closed_date)}
                </p>
              </div>

              {pothole.status === "open" && (
                <button
                  type="button"
                  className="button button-danger button-block"
                  onClick={() => alertMutation.mutate()}
                  disabled={alertMutation.isPending}
                >
                  {alertMutation.isPending ? "Sending alert..." : "Send DOT alert"}
                </button>
              )}

              {alertMutation.isSuccess && (
                <p className="success-copy">
                  Alert {alertMutation.data?.status === "sent" ? "sent" : "logged"} successfully.
                </p>
              )}
              {alertMutation.isError && (
                <p className="error-copy">
                  Failed to send alert: {String(alertMutation.error)}
                </p>
              )}
            </div>
          </motion.aside>
        </>
      ) : null}
    </AnimatePresence>
  );
}

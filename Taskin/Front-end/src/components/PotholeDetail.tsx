import { AnimatePresence, motion } from "framer-motion";
import { useMutation } from "@tanstack/react-query";
import {
  formatDate,
  formatDaysOpen,
  formatNumber,
  getRiskColor,
  getUrgencyLabel,
} from "../utils/map";
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
    mutationFn: async () => {
      await new Promise((resolve) => window.setTimeout(resolve, 900));
      return {
        status: "queued",
      };
    },
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
                <div className="eyebrow">Prototype detail</div>
                <h2>{pothole.address || pothole.street_name || "Pothole record"}</h2>
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
                {pothole.city} | {pothole.borough} | {pothole.zip_code}
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
                <MetricCard label="Days open" value={formatDaysOpen(pothole.days_open)} />
                <MetricCard
                  label="Urgency"
                  value={getUrgencyLabel(pothole.urgency_tier)}
                  tone={riskTone}
                />
                <MetricCard
                  label="Nearby collisions"
                  value={formatNumber(pothole.nearby_collision_count)}
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
                  label="Repair ETA"
                  value={
                    pothole.predicted_repair_days !== null &&
                    pothole.predicted_repair_days !== undefined
                      ? `${pothole.predicted_repair_days} days`
                      : pothole.repair_eta || "N/A"
                  }
                />
              </div>

              <div className="info-panel">
                <div className="eyebrow">Field summary</div>
                <p>
                  <strong>Street:</strong> {pothole.street_name}
                </p>
                <p>
                  <strong>Description:</strong> {pothole.descriptor}
                </p>
                <p>
                  <strong>Accident risk:</strong> {pothole.accident_risk || "Unknown"}
                </p>
                <p>
                  <strong>Opened:</strong> {formatDate(pothole.created_date)}
                </p>
                <p>
                  <strong>Closed:</strong> {formatDate(pothole.closed_date)}
                </p>
              </div>

              <button
                type="button"
                className="button button-danger button-block"
                onClick={() => alertMutation.mutate()}
                disabled={alertMutation.isPending}
              >
                {alertMutation.isPending ? "Queueing alert..." : "Queue DOT alert mock"}
              </button>

              {alertMutation.isSuccess ? (
                <p className="success-copy">Mock alert queued. This is safe until the backend lands.</p>
              ) : null}
            </div>
          </motion.aside>
        </>
      ) : null}
    </AnimatePresence>
  );
}

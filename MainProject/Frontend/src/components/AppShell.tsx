import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { adminRefresh } from "../api/alerts";

export default function AppShell() {
  const queryClient = useQueryClient();
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const location = useLocation();
  const isMapPage = location.pathname === "/";

  const refreshMutation = useMutation({
    mutationFn: () => adminRefresh(),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["potholes-geojson"] });
      queryClient.invalidateQueries({ queryKey: ["pothole-detail"] });
      queryClient.invalidateQueries({ queryKey: ["combined-stats"] });
      const rows = data?.rows_upserted ?? "unknown";
      setToast({ message: `Data refreshed — ${rows} rows upserted`, type: "success" });
      setTimeout(() => setToast(null), 5000);
    },
    onError: (error) => {
      setToast({ message: `Refresh failed: ${error.message}`, type: "error" });
      setTimeout(() => setToast(null), 8000);
    },
  });

  return (
    <div className={isMapPage ? "app-shell app-shell-map" : "app-shell"}>
      <header className={isMapPage ? "topbar topbar-map" : "topbar"}>
        <div className="brand-block">
          <span className="eyebrow">HunterHack frontend</span>
          <div className="brand-line">
            <h1>PotholeIQ NYC</h1>
            <span className="brand-chip">Live operations</span>
          </div>
        </div>

        <nav className="nav-links" aria-label="Primary">
          <NavLink
            to="/"
            end
            className={({ isActive }) => (isActive ? "nav-link nav-link-active" : "nav-link")}
          >
            Map
          </NavLink>
          <NavLink
            to="/dashboard"
            className={({ isActive }) => (isActive ? "nav-link nav-link-active" : "nav-link")}
          >
            Dashboard
          </NavLink>
          <button
            type="button"
            className="nav-link nav-link-refresh"
            onClick={() => refreshMutation.mutate()}
            disabled={refreshMutation.isPending}
            title="Re-fetch data from NYC Open Data and re-score"
          >
            {refreshMutation.isPending ? "Refreshing..." : "Refresh Data"}
          </button>
        </nav>
      </header>

      {toast && (
        <div className={`toast toast-${toast.type}`}>
          {toast.message}
        </div>
      )}

      <main className={`app-main${isMapPage ? " app-main-fullscreen" : ""}`}>
        <Outlet />
      </main>
    </div>
  );
}

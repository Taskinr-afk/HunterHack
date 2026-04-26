import { NavLink, Outlet } from "react-router-dom";

export default function AppShell() {
  return (
    <div className="app-shell">
      <header className="topbar">
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
        </nav>
      </header>

      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}

import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

export default function AppShell() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div className="app-shell">
      <header className={`topbar${scrolled ? " topbar-scrolled" : ""}`}>
        <div className="brand-block">
          <div className="brand-live">
            <span className="live-dot" />
            <span className="live-label">LIVE</span>
          </div>
          <div className="brand-line">
            <h1 className="brand-title">PotholeIQ</h1>
            <span className="brand-chip">NYC Intelligence</span>
          </div>
        </div>
        <nav className="nav-links" aria-label="Primary">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "nav-link nav-link-active" : "nav-link")}>Map</NavLink>
          <NavLink to="/dashboard" className={({ isActive }) => (isActive ? "nav-link nav-link-active" : "nav-link")}>Dashboard</NavLink>
        </nav>
      </header>
      <main className="app-main"><Outlet /></main>
    </div>
  );
}

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";
import { useApi } from "@/lib/use-api";
import type { HealthResponse, ReadyResponse } from "@/lib/types";
import { Icon, type IconName } from "@/components/icons";

const navigation: Array<{ href: string; label: string; icon: IconName; group: string }> = [
  { href: "/", label: "Overview", icon: "overview", group: "Workspace" },
  { href: "/predict", label: "Prediction lab", icon: "predict", group: "Workspace" },
  { href: "/csv", label: "CSV analysis", icon: "upload", group: "Workspace" },
  { href: "/transactions", label: "Transactions", icon: "transactions", group: "Workspace" },
  { href: "/risk", label: "Risk intelligence", icon: "risk", group: "Intelligence" },
  { href: "/explainability", label: "Explainability", icon: "explain", group: "Intelligence" },
  { href: "/anomalies", label: "Anomaly review", icon: "anomaly", group: "Intelligence" },
  { href: "/investigations", label: "Investigations", icon: "investigations", group: "Operations" },
  { href: "/system", label: "Model & system", icon: "system", group: "Operations" },
];

const titleByPath: Record<string, string> = {
  "/": "Overview",
  "/predict": "Prediction lab",
  "/csv": "CSV analysis",
  "/transactions": "Transaction history",
  "/risk": "Risk intelligence",
  "/explainability": "Explainability explorer",
  "/anomalies": "Anomaly intelligence",
  "/investigations": "Investigation workspace",
  "/system": "Model & system",
  "/analyses": "Analysis history",
};

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const health = useApi<HealthResponse>("/health");
  const ready = useApi<ReadyResponse>("/ready");
  const apiState = health.data ? "online" : health.error ? "offline" : "checking";
  const modelState = ready.data ? "online" : ready.error ? "offline" : "checking";
  const pageTitle = pathname.startsWith("/analyses/") ? "Analysis detail" : (titleByPath[pathname] ?? "Fraud intelligence");

  return (
    <div className="app-frame">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <div className={`mobile-backdrop ${mobileOpen ? "show" : ""}`} onClick={() => setMobileOpen(false)} aria-hidden="true" />
      <aside className={`sidebar ${mobileOpen ? "open" : ""}`} aria-label="Main navigation">
        <Link className="brand" href="/" onClick={() => setMobileOpen(false)}>
          <span className="brand-mark"><Icon name="shield" /></span>
          <span><span className="brand-title">Fraud Intelligence</span><span className="brand-subtitle">Analyst command center</span></span>
        </Link>
        {(["Workspace", "Intelligence", "Operations"] as const).map((group) => (
          <div key={group}>
            <div className="nav-label">{group}</div>
            <nav className="nav-list" aria-label={group}>
              {navigation.filter((item) => item.group === group).map((item) => (
                <Link key={item.href} href={item.href} className={`nav-link ${isActive(pathname, item.href) ? "active" : ""}`} aria-current={isActive(pathname, item.href) ? "page" : undefined} onClick={() => setMobileOpen(false)}>
                  <Icon name={item.icon} />{item.label}
                </Link>
              ))}
            </nav>
          </div>
        ))}
        <div className="sidebar-spacer" />
        <div className="local-card">
          <div className="local-card-head"><span>Local runtime</span><span className={`status-dot ${apiState}`} /></div>
          <p>Loopback API · unauthenticated · trusted workstation only</p>
        </div>
        <div className="sidebar-foot"><span className="status-dot online" />Local workspace</div>
      </aside>

      <div className="main-column">
        <header className="topbar">
          <div className="topbar-left">
            <button className="mobile-menu" type="button" aria-label={mobileOpen ? "Close navigation" : "Open navigation"} aria-expanded={mobileOpen} onClick={() => setMobileOpen((open) => !open)}><Icon name={mobileOpen ? "close" : "menu"} /></button>
            <div className="page-context"><span className="crumb">Fraud intelligence / local</span><span className="topbar-title">{pageTitle}</span></div>
          </div>
          <div className="topbar-right">
            <span className="system-chip" title={health.data?.components.database ? `Database: ${health.data.components.database}` : "Checking local API"}><span className={`status-dot ${apiState}`} />{apiState === "online" ? "API connected" : apiState === "offline" ? "API offline" : "Checking API"}</span>
            <span className="system-chip model-chip"><span className={`status-dot ${modelState}`} />{modelState === "online" ? "Model ready" : modelState === "offline" ? "Model unavailable" : "Checking model"}</span>
            <Link href="/system" className="topbar-link" aria-label="Open model and system status"><Icon name="external" /><span>System status</span></Link>
          </div>
        </header>
        <main className="content-wrap" id="main-content" tabIndex={-1}>{children}</main>
      </div>
    </div>
  );
}

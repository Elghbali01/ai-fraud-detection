import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";
import Link from "next/link";
import type { RiskTier } from "@/lib/types";
import { riskTone } from "@/lib/format";
import { Icon, type IconName } from "@/components/icons";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div className="page-title-block">
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p className="page-description">{description}</p>
      </div>
      {actions ? <div className="header-actions">{actions}</div> : null}
    </header>
  );
}

export function SectionHeading({ title, description, meta }: { title: string; description?: string; meta?: string }) {
  return (
    <div className="section-heading">
      <div><h2>{title}</h2>{description ? <p>{description}</p> : null}</div>
      {meta ? <span className="section-meta">{meta}</span> : null}
    </div>
  );
}

export function Card({ children, className = "", ...props }: HTMLAttributes<HTMLElement>) {
  return <section className={`card ${className}`} {...props}>{children}</section>;
}

export function CardHeading({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return <div className="card-heading"><div className="card-heading-copy"><h2 className="card-title">{title}</h2>{description ? <p className="card-copy">{description}</p> : null}</div>{action}</div>;
}

export function Button({ variant = "default", icon, children, className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "default" | "primary" | "quiet" | "danger"; icon?: IconName }) {
  return <button className={`button button-${variant} ${className}`} {...props}>{icon ? <Icon name={icon} /> : null}{children}</button>;
}

export function ActionLink({ href, icon, children }: { href: string; icon?: IconName; children: ReactNode }) {
  return <Link className="button button-default" href={href}>{children}{icon ? <Icon name={icon} /> : null}</Link>;
}

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: string }) {
  return <span className={`badge tone-${tone}`}>{children}</span>;
}

export function RiskBadge({ tier }: { tier: RiskTier | string }) {
  return <span className={`badge ${riskTone(tier)}`}><span className={`status-dot ${tier === "Critical" ? "offline" : tier === "Low" ? "online" : ""}`} />{tier}</span>;
}

export function MetricCard({ label, value, note, icon }: { label: string; value: string; note: string; icon: IconName }) {
  return <Card className="metric-card"><span className="metric-label">{label}</span><span className="metric-value">{value}</span><span className="metric-note">{note}</span><span className="metric-icon"><Icon name={icon} /></span></Card>;
}

export function EmptyState({ icon = "transactions", title, description, action }: { icon?: IconName; title: string; description: string; action?: ReactNode }) {
  return <div className="empty-state"><span className="empty-icon"><Icon name={icon} /></span><h3>{title}</h3><p>{description}</p>{action ? <div style={{ marginTop: 5 }}>{action}</div> : null}</div>;
}

export function ErrorState({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  return <div className="error-state" role="alert"><span className="error-icon"><Icon name="alert" /></span><div><h3>{error.message.includes("Cannot reach") ? "API is unavailable" : "Request could not be completed"}</h3><p>{error.message}</p>{"status" in error && (error as Error & { requestId?: string }).requestId ? <p className="mono" style={{ marginTop: 6 }}>Request ID: {(error as Error & { requestId?: string }).requestId}</p> : null}{onRetry ? <Button className="small" icon="refresh" onClick={onRetry} style={{ marginTop: 10 }}>Try again</Button> : null}</div></div>;
}

export function LoadingState({ label = "Loading verified API data" }: { label?: string }) {
  return <div className="card loading-surface" role="status" aria-label={label}><div className="skeleton short" /><div className="skeleton medium" /><div className="skeleton skeleton-block" /></div>;
}

export function Callout({ children, tone = "info", icon = "shield" }: { children: ReactNode; tone?: "info" | "warning" | "danger"; icon?: IconName }) {
  return <div className={`callout ${tone === "warning" ? "callout-warning" : tone === "danger" ? "callout-danger" : ""}`}><Icon name={icon} /><div>{children}</div></div>;
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return <label className="field"><span className="field-label">{label}</span>{children}{hint ? <span className="field-hint">{hint}</span> : null}</label>;
}

export function StatusLine({ state, label }: { state: "online" | "offline" | "checking"; label: string }) {
  return <span className="status-line"><span className={`status-dot ${state}`} />{label}</span>;
}

export function JsonBlock({ value }: { value: unknown }) {
  return <pre className="json-pre">{JSON.stringify(value, null, 2)}</pre>;
}

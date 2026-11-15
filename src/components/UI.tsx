import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Database, Info } from "lucide-react";

export function Card({
  children,
  className = "",
  title,
  eyebrow,
  action,
}: {
  children: ReactNode;
  className?: string;
  title?: string;
  eyebrow?: string;
  action?: ReactNode;
}) {
  return (
    <section className={`card ${className}`}>
      {(title || eyebrow || action) && (
        <header className="card-header">
          <div>
            {eyebrow && <span className="eyebrow">{eyebrow}</span>}
            {title && <h3>{title}</h3>}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

export function DemoBadge() {
  return (
    <span className="demo-badge">
      <Database size={11} /> DEMO DATA
    </span>
  );
}

export function Status({
  type,
  children,
}: {
  type: "verified" | "partial" | "missing" | "experimental";
  children: ReactNode;
}) {
  return (
    <span className={`status status-${type}`}>
      {type === "verified" && <CheckCircle2 size={11} />}
      {type === "missing" && <AlertTriangle size={11} />}
      {type === "experimental" && <Info size={11} />}
      {children}
    </span>
  );
}

export function EmptyState({ reset }: { reset: () => void }) {
  return (
    <div className="empty-state">
      <Database size={28} />
      <h3>No demo observations match</h3>
      <p>Adjust the active sensor or confidence filters to restore observations.</p>
      <button className="button secondary" onClick={reset}>
        Reset filters
      </button>
    </div>
  );
}

export function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <strong>{label}</strong>
      {payload.map((item) => (
        <span key={item.name}>
          <i style={{ background: item.color }} />
          {item.name}: {item.value}
        </span>
      ))}
      <small>Sample index</small>
    </div>
  );
}

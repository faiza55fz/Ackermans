import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Database, Info, RefreshCw } from "lucide-react";

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
      <h3>No observations match</h3>
      <p>Adjust the active sensor or confidence filters to restore observations.</p>
      <button className="button secondary" onClick={reset}>
        Reset filters
      </button>
    </div>
  );
}

export function LoadingSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-3 py-4 animate-pulse">
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="h-4 bg-[#233142] rounded"
          style={{ width: i === 0 ? "80%" : i === 1 ? "95%" : "60%" }}
        />
      ))}
    </div>
  );
}

export function DataUnavailable({
  title = "Data Temporarily Unavailable",
  message = "Observations for the selected region and sensor constellation are not present in the current dataset snapshot.",
  onRetry,
}: {
  title?: string;
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="p-8 text-center border border-dashed border-[#2d3f54] rounded-lg bg-[#141d28]/60 my-4 space-y-2">
      <AlertTriangle className="mx-auto mb-2 text-[#ffb84d]" size={32} />
      <h4 className="text-[#d8e2ef] font-semibold text-base">{title}</h4>
      <p className="text-[#8e9eb3] text-sm max-w-md mx-auto">
        {message}
      </p>
      {onRetry && (
        <div className="pt-2">
          <button className="button secondary inline-flex items-center gap-2 min-h-[40px] px-4" onClick={onRetry}>
            <RefreshCw size={14} /> Retry loading
          </button>
        </div>
      )}
    </div>
  );
}

export function ChartTooltip({
  active,
  payload,
  label,
  modelOutputDisclaimer,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
  modelOutputDisclaimer?: string | boolean;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <strong>{label}</strong>
      {payload.map((item) => (
        <span key={item.name}>
          <i style={{ background: item.color }} />
          {item.name}: {typeof item.value === "number" ? item.value.toLocaleString() : item.value}
        </span>
      ))}
      {modelOutputDisclaimer && (
        <small style={{ color: "#ffb84d", marginTop: 4, display: "block" }}>
          {typeof modelOutputDisclaimer === "string" ? modelOutputDisclaimer : "Experimental Model Output"}
        </small>
      )}
    </div>
  );
}

import React, { type ReactNode } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/* --------------------------------- badges --------------------------------- */

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium uppercase tracking-wide whitespace-nowrap",
  {
    variants: {
      tone: {
        neutral: "border-white/10 bg-surface-2 text-muted-foreground",
        success: "border-success/30 bg-success/10 text-success",
        warning: "border-warning/30 bg-warning/10 text-warning",
        danger: "border-danger/30 bg-danger/10 text-danger",
        info: "border-info/30 bg-info/10 text-info",
        solid: "border-transparent bg-primary text-primary-foreground",
      },
    },
    defaultVariants: { tone: "neutral" },
  }
);

export function Badge({
  tone,
  className,
  children,
}: VariantProps<typeof badgeVariants> & { className?: string; children: ReactNode }) {
  return <span className={cn(badgeVariants({ tone }), className)}>{children}</span>;
}

export function evidenceTone(status?: string) {
  switch ((status || "").toUpperCase()) {
    case "EXPLICIT":
      return "success" as const;
    case "CONDITIONAL":
      return "warning" as const;
    case "PARTIAL":
    case "INFERRED":
      return "info" as const;
    case "CONFLICTED":
    case "CONFLICTING":
    case "MIXED":
      return "danger" as const;
    default:
      return "neutral" as const;
  }
}

export function severityTone(level?: string) {
  switch ((level || "").toUpperCase()) {
    case "LOW":
      return "success" as const;
    case "MEDIUM":
      return "warning" as const;
    case "HIGH":
    case "CRITICAL":
      return "danger" as const;
    default:
      return "neutral" as const;
  }
}

export function EvidenceBadge({ status }: { status?: string }) {
  return <Badge tone={evidenceTone(status)}>{status || "NOT_SPECIFIED"}</Badge>;
}

export function SeverityBadge({ level }: { level?: string }) {
  return <Badge tone={severityTone(level)}>{level || "UNSPECIFIED"}</Badge>;
}

/* --------------------------------- panels --------------------------------- */

export function Panel({
  title,
  subtitle,
  action,
  children,
  className,
}: {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={cn("rounded-xl border border-white/10 bg-surface", className)}
      aria-label={title}
    >
      {(title || action) && (
        <header className="flex items-start justify-between gap-4 border-b border-white/10 px-5 py-3.5">
          <div>
            {title && (
              <h2 className="text-sm font-semibold tracking-tight text-white">{title}</h2>
            )}
            {subtitle && <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow && (
          <p className="mb-1.5 text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
            {eyebrow}
          </p>
        )}
        <h1 className="text-2xl font-semibold tracking-tight text-white">{title}</h1>
        {description && (
          <p className="mt-1.5 max-w-2xl text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {action}
    </header>
  );
}

/* ------------------------------ state displays ----------------------------- */

export function EmptyState({
  icon = "fa-regular fa-folder-open",
  title,
  description,
  action,
}: {
  icon?: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-white/10 bg-surface/40 px-6 py-14 text-center">
      <span className="mb-4 flex h-11 w-11 items-center justify-center rounded-full border border-white/10 bg-surface-2">
        <i className={cn(icon, "text-sm text-muted-foreground")} aria-hidden="true" />
      </span>
      <h3 className="text-sm font-semibold text-white">{title}</h3>
      <p className="mt-1.5 max-w-md text-sm text-muted-foreground">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="flex flex-col items-start gap-3 rounded-xl border border-danger/30 bg-danger/5 px-5 py-4"
    >
      <div className="flex items-start gap-3">
        <i className="fa-solid fa-triangle-exclamation mt-0.5 text-danger" aria-hidden="true" />
        <div>
          <p className="text-sm font-medium text-white">Something went wrong</p>
          <p className="mt-1 text-sm text-muted-foreground">
            {message || "The request could not be completed."}
          </p>
        </div>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-md border border-white/20 bg-surface-2 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-surface-3"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export function SkeletonRows({ rows = 4, className }: { rows?: number; className?: string }) {
  return (
    <div className={cn("space-y-3", className)} aria-hidden="true">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="fx-skeleton h-10 rounded-lg" />
      ))}
    </div>
  );
}

/* --------------------------------- gauges --------------------------------- */

export function ScoreGauge({
  value,
  label,
  description,
  tone = "neutral",
  max = 100,
}: {
  value: number;
  label: string;
  description?: string;
  tone?: "neutral" | "success" | "warning" | "danger" | "info";
  max?: number;
}) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  const stroke =
    tone === "success"
      ? "var(--success)"
      : tone === "warning"
        ? "var(--warning)"
        : tone === "danger"
          ? "var(--danger)"
          : tone === "info"
            ? "var(--info)"
            : "var(--text)";
  const r = 34;
  const c = 2 * Math.PI * r;
  return (
    <div className="flex items-start gap-3">
      <svg width="74" height="74" viewBox="0 0 84 84" className="shrink-0" role="img" aria-label={`${label}: ${value}`}>
        <circle cx="42" cy="42" r={r} fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="6" />
        <circle
          cx="42"
          cy="42"
          r={r}
          fill="none"
          stroke={stroke}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c - (c * pct) / 100}
          transform="rotate(-90 42 42)"
          style={{ transition: "stroke-dashoffset 700ms cubic-bezier(0.22, 1, 0.36, 1)" }}
        />
        <text
          x="42"
          y="47"
          textAnchor="middle"
          fill="#ffffff"
          fontSize="16"
          fontWeight="600"
        >
          {Math.round(value)}
        </text>
      </svg>
      <div className="min-w-0">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">{label}</p>
        <p className="text-xs text-white/90 font-medium">{value}/{max}</p>
        {description && (
          <p className="text-[10px] text-white/60 leading-tight mt-1 line-clamp-2" title={description}>
            {description}
          </p>
        )}
      </div>
    </div>
  );
}

/* ------------------------------- misc helpers ------------------------------ */

export function KeyValue({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-white/5 py-2.5 last:border-0">
      <span className="text-xs uppercase tracking-wide text-muted-foreground">{label}</span>
      <span className="text-right text-sm text-white font-medium">{value}</span>
    </div>
  );
}

export function toText(item: unknown): string {
  if (item == null) return "";
  if (typeof item === "string") return item;
  if (typeof item === "number" || typeof item === "boolean") return String(item);
  if (typeof item === "object") {
    const o = item as Record<string, unknown>;
    for (const k of ["text", "description", "fact", "value", "question", "title", "label", "item"]) {
      if (typeof o[k] === "string") return o[k] as string;
    }
    return JSON.stringify(o);
  }
  return String(item);
}

export function CitationChip({
  page,
  section,
  verified,
}: {
  page?: number | string;
  section?: string;
  verified?: boolean;
}) {
  return (
    <span className="inline-flex items-center gap-2 rounded-md border border-white/10 bg-surface-2 px-2.5 py-1 text-xs text-muted-foreground">
      <i className="fa-regular fa-file-lines text-[10px]" aria-hidden="true" />
      <span className="text-white">Page {page ?? "—"}</span>
      {section && <span>· Section: {section}</span>}
      {verified !== undefined && (
        <i
          className={cn(
            verified ? "fa-solid fa-circle-check text-success" : "fa-regular fa-circle text-muted-foreground",
            "text-[10px]"
          )}
          aria-label={verified ? "Verified citation" : "Unverified citation"}
        />
      )}
    </span>
  );
}

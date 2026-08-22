import React from "react";
import { type StructuredFact } from "@/lib/api";
import { EvidenceBadge } from "@/components/finex/primitives";
import { CheckCircle2, AlertCircle, FileText } from "lucide-react";

interface StructuredFactCardProps {
  fact: StructuredFact | string | any;
  isCondition?: boolean;
}

export function parseFactObject(fact: any): StructuredFact {
  if (typeof fact === "string") {
    try {
      return JSON.parse(fact);
    } catch {
      return { field: "Fact", value: fact, status: "EXPLICIT" };
    }
  }
  return fact || {};
}

export function StructuredFactCard({ fact: rawFact, isCondition = false }: StructuredFactCardProps) {
  const fact = parseFactObject(rawFact);

  const title =
    fact.field
      ? fact.field.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase())
      : fact.category
        ? fact.category.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase())
        : isCondition
          ? "Conditional Term"
          : "Loan Fact";

  const hasValue = fact.value !== undefined && fact.value !== null && fact.value !== "" && fact.value !== "NOT_SPECIFIED";
  const formattedValue = hasValue
    ? `${fact.value}${
        fact.unit === "percent" || String(fact.value).includes("%")
          ? ""
          : fact.currency
            ? ` ${fact.currency}`
            : fact.unit
              ? ` ${fact.unit}`
              : ""
      }`
    : isCondition
      ? "Conditional"
      : "Not Specified";

  const conditionText = fact.condition || (isCondition ? fact.source_text : undefined);
  const status = fact.status || (isCondition ? "CONDITIONAL" : "EXPLICIT");

  return (
    <div className="rounded-lg border border-white/10 bg-surface-2 p-3.5 flex flex-col justify-between gap-2.5 transition-colors hover:border-white/20">
      <div>
        <div className="flex items-center justify-between gap-2 mb-1.5">
          <div className="flex items-center gap-2 min-w-0">
            {isCondition ? (
              <AlertCircle className="h-4 w-4 text-amber-400 shrink-0" />
            ) : (
              <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
            )}
            <span className="text-xs font-semibold text-white truncate" title={title}>
              {title}
            </span>
          </div>
          <EvidenceBadge status={status} />
        </div>

        {conditionText && (
          <p className="text-[11px] text-white/80 leading-relaxed bg-white/5 rounded px-2 py-1.5 mt-1.5 border border-white/5">
            <span className="text-amber-300/90 font-medium mr-1">Condition:</span>
            {conditionText}
          </p>
        )}
      </div>

      <div className="flex items-center justify-between border-t border-white/5 pt-2 text-[11px]">
        {fact.page ? (
          <span className="text-white/50 flex items-center gap-1">
            <FileText className="h-3 w-3" />
            Page {fact.page} {fact.source_document ? `(${fact.source_document})` : ""}
          </span>
        ) : (
          <span className="text-white/40">Verified Fact</span>
        )}
        <span className={`font-mono font-semibold ${hasValue ? "text-white" : "text-white/60"}`}>
          {formattedValue}
        </span>
      </div>
    </div>
  );
}

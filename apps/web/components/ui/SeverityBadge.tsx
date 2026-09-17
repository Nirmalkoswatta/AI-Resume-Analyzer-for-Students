import type { Severity } from "@resume/schema";

const LABELS: Record<Severity, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
};

const STYLES: Record<Severity, string> = {
  critical: "bg-critical/12 text-critical ring-critical/30",
  high: "bg-high/12 text-high ring-high/30",
  medium: "bg-medium/12 text-medium ring-medium/30",
  low: "bg-low/12 text-low ring-low/30",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${STYLES[severity]}`}
    >
      {LABELS[severity]}
    </span>
  );
}

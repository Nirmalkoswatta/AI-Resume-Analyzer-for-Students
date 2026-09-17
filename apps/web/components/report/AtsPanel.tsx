import type { AtsScore } from "@resume/schema";

import { Card } from "@/components/ui/Card";
import { SeverityBadge } from "@/components/ui/SeverityBadge";

function scoreTone(score: number): string {
  if (score >= 80) return "text-pass";
  if (score >= 60) return "text-medium";
  return "text-critical";
}

export function AtsPanel({ ats }: { ats: AtsScore }) {
  const failed = ats.checks.filter((check) => !check.passed);

  return (
    <Card
      title="ATS friendliness"
      description="How reliably an applicant tracking system can read this resume. Every check is shown."
    >
      <div className="mb-6 flex items-baseline gap-3">
        <span className={`text-5xl font-semibold tabular-nums ${scoreTone(ats.score)}`}>
          {Math.round(ats.score)}
        </span>
        <span className="text-sm text-ink-muted">
          out of 100 &middot; {failed.length} of {ats.checks.length} checks need attention
        </span>
      </div>

      <ul className="divide-y divide-border-subtle">
        {ats.checks.map((check) => (
          <li key={check.id} className="flex gap-3 py-3">
            <span
              aria-hidden
              className={`mt-1 size-2 shrink-0 rounded-full ${check.passed ? "bg-pass" : "bg-critical"}`}
            />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium">{check.label}</span>
                <span className="sr-only">{check.passed ? "Passed" : "Needs attention"}</span>
                {check.passed ? null : <SeverityBadge severity={check.severity} />}
              </div>
              <p className="mt-1 text-sm text-ink-muted">{check.explanation}</p>
            </div>
          </li>
        ))}
      </ul>

      <p className="mt-4 text-xs text-ink-muted">Rubric version {ats.rubric_version}</p>
    </Card>
  );
}

import type { JobDescriptionMatch, RoleFit } from "@resume/schema";

import { Card } from "@/components/ui/Card";

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function FitPanel({ fit }: { fit: RoleFit }) {
  const match = fit.job_description;

  if (fit.predictions.length === 0) {
    return (
      <Card title="Role fit" description="No role could be predicted.">
        <p className="text-sm text-ink-muted">
          Role fit is worked out from recognised software skills, and none were found here, so
          there is nothing to rank. This says nothing about your suitability for a role.
        </p>
        {match ? (
          <div className="mt-6 border-t border-border-subtle pt-5">
            <JobMatch match={match} />
          </div>
        ) : null}
      </Card>
    );
  }

  return (
    <Card
      title="Role fit"
      description="Predicted from resume content, and compared against your target posting."
    >
      <ul className="space-y-3">
        {fit.predictions.map((prediction) => (
          <li key={prediction.role}>
            <div className="mb-1 flex items-baseline justify-between text-sm">
              <span className="font-medium">{prediction.role}</span>
              <span className="tabular-nums text-ink-muted">{percent(prediction.confidence)}</span>
            </div>
            <div aria-hidden className="h-1.5 overflow-hidden rounded-full bg-surface">
              <div
                className="h-full rounded-full bg-accent"
                style={{ width: percent(prediction.confidence) }}
              />
            </div>
          </li>
        ))}
      </ul>

      {match ? (
        <div className="mt-6 border-t border-border-subtle pt-5">
          <JobMatch match={match} />
        </div>
      ) : null}
    </Card>
  );
}

function JobMatch({ match }: { match: JobDescriptionMatch }) {
  return (
    <>
      <p className="text-sm font-medium">Against your target job</p>
      <p className="mt-1 text-sm text-ink-muted">
        You already cover {match.matched_skills.length} of the skills this posting names,{" "}
        {percent(match.similarity)} of them.
      </p>

      {match.missing_skills.length > 0 ? (
        <>
          <p className="mt-4 text-sm font-medium">Gaps worth closing first</p>
          <ul className="mt-2 space-y-1.5">
            {match.missing_skills.map((gap) => (
              <li key={gap.skill} className="flex items-baseline justify-between text-sm">
                <span>{gap.skill}</span>
                <span className="text-ink-muted">
                  {gap.importance >= 0.75 ? "frequently required" : "often mentioned"}
                </span>
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </>
  );
}

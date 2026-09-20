import type { Severity, Suggestion } from "@resume/schema";

import { Card } from "@/components/ui/Card";
import { SeverityBadge } from "@/components/ui/SeverityBadge";

const ORDER: Record<Severity, number> = { critical: 0, high: 1, medium: 2, low: 3 };

export function SuggestionsPanel({ suggestions }: { suggestions: Suggestion[] }) {
  const ordered = [...suggestions].sort((a, b) => ORDER[a.severity] - ORDER[b.severity]);

  return (
    <Card title="What to fix next" description="Ordered by how much each change will help.">
      <ol className="space-y-5">
        {ordered.map((suggestion) => (
          <li key={suggestion.id}>
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-medium">{suggestion.title}</h3>
              <SeverityBadge severity={suggestion.severity} />
            </div>
            <p className="mt-1 text-sm text-ink-muted">{suggestion.detail}</p>
            {suggestion.location ? (
              <p className="mt-2 border-l-2 border-border-subtle pl-3 font-mono text-xs text-ink-muted">
                page {suggestion.location.page}: {suggestion.location.excerpt}
              </p>
            ) : null}
          </li>
        ))}
      </ol>
    </Card>
  );
}

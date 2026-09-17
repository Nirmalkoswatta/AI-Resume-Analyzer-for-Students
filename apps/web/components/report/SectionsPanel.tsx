import type { DetectedSection, SectionKind } from "@resume/schema";

import { Card } from "@/components/ui/Card";

const SECTION_LABELS: Record<SectionKind, string> = {
  contact: "Contact",
  summary: "Summary",
  education: "Education",
  experience: "Experience",
  skills: "Skills",
  projects: "Projects",
  certifications: "Certifications",
  awards: "Awards",
  publications: "Publications",
  languages: "Languages",
  interests: "Interests",
  references: "References",
  other: "Other",
};

export function SectionsPanel({
  sections,
  missing,
}: {
  sections: DetectedSection[];
  missing: SectionKind[];
}) {
  return (
    <Card title="Structure" description="Sections found in the document, and what is absent.">
      <ul className="space-y-2">
        {sections.map((section) => (
          <li
            key={`${section.kind}-${section.location.line_start}`}
            className="flex items-baseline justify-between gap-4 text-sm"
          >
            <span className="font-medium">{SECTION_LABELS[section.kind]}</span>
            <span className="text-ink-muted">
              {section.heading ? `"${section.heading}"` : "no heading"} &middot;{" "}
              {section.word_count} words
            </span>
          </li>
        ))}
      </ul>

      {missing.length > 0 ? (
        <div className="mt-5 rounded-lg border border-border-subtle bg-surface p-4">
          <p className="text-sm font-medium">Worth adding</p>
          <p className="mt-1 text-sm text-ink-muted">
            {missing.map((kind) => SECTION_LABELS[kind]).join(", ")}
          </p>
        </div>
      ) : null}
    </Card>
  );
}

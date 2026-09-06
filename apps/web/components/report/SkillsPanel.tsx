import type { Skill } from "@resume/schema";

import { Card } from "@/components/ui/Card";

export function SkillsPanel({ skills }: { skills: Skill[] }) {
  const demonstrated = skills.filter((skill) => skill.evidence === "demonstrated");
  const claimed = skills.filter((skill) => skill.evidence === "claimed");

  return (
    <Card
      title="Skills"
      description="Skills backed by a project or role read far stronger than a bare list."
    >
      <SkillGroup
        heading={`Demonstrated in your experience (${demonstrated.length})`}
        skills={demonstrated}
        tone="border-pass/40 bg-pass/8"
      />
      {claimed.length > 0 ? (
        <SkillGroup
          heading={`Listed only (${claimed.length})`}
          skills={claimed}
          tone="border-border-subtle bg-surface"
        />
      ) : null}
    </Card>
  );
}

function SkillGroup({
  heading,
  skills,
  tone,
}: {
  heading: string;
  skills: Skill[];
  tone: string;
}) {
  if (skills.length === 0) return null;

  return (
    <div className="mb-5 last:mb-0">
      <p className="mb-2 text-sm font-medium">{heading}</p>
      <ul className="flex flex-wrap gap-2">
        {skills.map((skill) => (
          <li
            key={skill.name}
            className={`rounded-full border px-3 py-1 text-sm ${tone}`}
            title={skill.category ?? undefined}
          >
            {skill.name}
          </li>
        ))}
      </ul>
    </div>
  );
}

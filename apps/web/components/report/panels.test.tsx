import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";
import type {
  AtsScore,
  DetectedSection,
  RoleFit,
  Skill,
  Suggestion,
} from "@resume/schema";

import { AtsPanel } from "@/components/report/AtsPanel";
import { FitPanel } from "@/components/report/FitPanel";
import { SectionsPanel } from "@/components/report/SectionsPanel";
import { SkillsPanel } from "@/components/report/SkillsPanel";
import { SuggestionsPanel } from "@/components/report/SuggestionsPanel";

afterEach(cleanup);

function skill(name: string, evidence: Skill["evidence"]): Skill {
  return {
    name,
    canonical_id: `seed:${name.toLowerCase()}`,
    category: "Programming languages",
    source: "gazetteer",
    evidence,
    found_in: ["skills"],
    confidence: 0.95,
  };
}

function suggestion(id: string, severity: Suggestion["severity"], title: string): Suggestion {
  return { id, severity, title, detail: `detail for ${title}`, section: null, location: null };
}

const ATS: AtsScore = {
  score: 48,
  rubric_version: "2026.09.1",
  checks: [
    {
      id: "single_column_layout",
      label: "Single-column layout",
      passed: false,
      weight: 0.25,
      severity: "critical",
      explanation: "Two text columns were detected.",
    },
    {
      id: "machine_readable_text",
      label: "Selectable text layer",
      passed: true,
      weight: 0.25,
      severity: "critical",
      explanation: "The document contains real text.",
    },
  ],
};

test("a resume with no recognised skills explains why rather than showing nothing", () => {
  render(<SkillsPanel skills={[]} />);

  expect(screen.getByText(/could not identify/i)).toBeDefined();
  expect(screen.getByText(/another field/i)).toBeDefined();
});

test("demonstrated and claimed skills are grouped separately", () => {
  render(<SkillsPanel skills={[skill("Python", "demonstrated"), skill("Git", "claimed")]} />);

  expect(screen.getByText(/Demonstrated in your experience \(1\)/)).toBeDefined();
  expect(screen.getByText(/Listed only \(1\)/)).toBeDefined();
  expect(screen.getByText("Python")).toBeDefined();
  expect(screen.getByText("Git")).toBeDefined();
});

test("the listed-only group is hidden when everything is demonstrated", () => {
  render(<SkillsPanel skills={[skill("Python", "demonstrated")]} />);

  expect(screen.queryByText(/Listed only/)).toBeNull();
});

test("no role prediction explains itself instead of rendering an empty list", () => {
  const fit: RoleFit = { predictions: [], job_description: null };

  render(<FitPanel fit={fit} />);

  expect(screen.getByText(/nothing to rank/i)).toBeDefined();
  expect(screen.getByText(/says nothing about your suitability/i)).toBeDefined();
});

test("job description gaps still show when no role could be predicted", () => {
  const fit: RoleFit = {
    predictions: [],
    job_description: {
      similarity: 0.4,
      matched_skills: ["Python"],
      missing_skills: [{ skill: "Kubernetes", importance: 1 }],
    },
  };

  render(<FitPanel fit={fit} />);

  expect(screen.getByText(/nothing to rank/i)).toBeDefined();
  expect(screen.getByText("Kubernetes")).toBeDefined();
});

test("role predictions render with their confidence", () => {
  const fit: RoleFit = {
    predictions: [{ role: "Backend Developer", confidence: 0.32 }],
    job_description: null,
  };

  render(<FitPanel fit={fit} />);

  expect(screen.getByText("Backend Developer")).toBeDefined();
  expect(screen.getByText("32%")).toBeDefined();
});

test("every ats check is shown, passed and failed alike", () => {
  render(<AtsPanel ats={ATS} />);

  expect(screen.getByText("Single-column layout")).toBeDefined();
  expect(screen.getByText("Selectable text layer")).toBeDefined();
  expect(screen.getByText(/1 of 2 checks need attention/)).toBeDefined();
});

test("a failed check carries its severity and a passed one does not", () => {
  render(<AtsPanel ats={ATS} />);

  expect(screen.getAllByText("Critical")).toHaveLength(1);
});

test("the score is rounded for display", () => {
  render(<AtsPanel ats={{ ...ATS, score: 47.6 }} />);

  expect(screen.getByText("48")).toBeDefined();
});

test("suggestions are ordered by severity regardless of input order", () => {
  render(
    <SuggestionsPanel
      suggestions={[
        suggestion("a", "low", "Least urgent"),
        suggestion("b", "critical", "Most urgent"),
        suggestion("c", "medium", "Middle"),
      ]}
    />,
  );

  const headings = screen.getAllByRole("heading", { level: 3 }).map((node) => node.textContent);

  expect(headings).toEqual(["Most urgent", "Middle", "Least urgent"]);
});

function section(
  kind: DetectedSection["kind"],
  heading: string | null,
  wordCount: number,
  lineStart: number,
): DetectedSection {
  return {
    kind,
    heading,
    word_count: wordCount,
    location: { page: 1, line_start: lineStart, line_end: lineStart + 2, excerpt: "" },
  };
}

test("a block with no heading is labelled rather than rendered blank", () => {
  render(
    <SectionsPanel
      sections={[section("other", null, 17, 12), section("languages", "Languages", 2, 30)]}
      missing={[]}
    />,
  );

  expect(screen.getByText(/no heading/i)).toBeDefined();
  expect(screen.getByText("Languages")).toBeDefined();
});

test("missing sections are named so the advice is actionable", () => {
  render(<SectionsPanel sections={[section("skills", "Skills", 12, 3)]} missing={["projects"]} />);

  expect(screen.getByText("Projects")).toBeDefined();
});

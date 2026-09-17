import type { AnalysisResult } from "@resume/schema";

import { AtsPanel } from "@/components/report/AtsPanel";
import { FitPanel } from "@/components/report/FitPanel";
import { SectionsPanel } from "@/components/report/SectionsPanel";
import { SkillsPanel } from "@/components/report/SkillsPanel";
import { SuggestionsPanel } from "@/components/report/SuggestionsPanel";

export function Report({ result }: { result: AnalysisResult }) {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="lg:col-span-2">
        <SuggestionsPanel suggestions={result.suggestions} />
      </div>
      <AtsPanel ats={result.ats} />
      <div className="grid gap-6">
        <SectionsPanel sections={result.sections} missing={result.missing_sections} />
        <SkillsPanel skills={result.skills} />
      </div>
      <div className="lg:col-span-2">
        <FitPanel fit={result.fit} />
      </div>
    </div>
  );
}

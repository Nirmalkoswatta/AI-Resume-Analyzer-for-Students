import type { components } from "./api";

type Schemas = components["schemas"];

export type AnalysisResult = Schemas["AnalysisResult"];
export type AtsCheck = Schemas["AtsCheck"];
export type AtsScore = Schemas["AtsScore"];
export type DetectedSection = Schemas["DetectedSection"];
export type DocumentStats = Schemas["DocumentStats"];
export type ErrorResponse = Schemas["ErrorResponse"];
export type JobDescriptionMatch = Schemas["JobDescriptionMatch"];
export type RoleFit = Schemas["RoleFit"];
export type RolePrediction = Schemas["RolePrediction"];
export type Skill = Schemas["Skill"];
export type SkillGap = Schemas["SkillGap"];
export type Suggestion = Schemas["Suggestion"];
export type TextLocation = Schemas["TextLocation"];

export type AnalysisErrorCode = Schemas["AnalysisErrorCode"];
export type EvidenceStrength = Schemas["EvidenceStrength"];
export type SectionKind = Schemas["SectionKind"];
export type Severity = Schemas["Severity"];
export type SkillSource = Schemas["SkillSource"];

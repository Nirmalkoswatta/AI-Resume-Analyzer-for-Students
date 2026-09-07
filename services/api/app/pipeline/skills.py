import re
from dataclasses import dataclass

from rapidfuzz import fuzz, process

from app.pipeline.document import Document
from app.pipeline.taxonomy import SkillEntry, Taxonomy, get_taxonomy
from app.schemas.analysis import DetectedSection, Skill
from app.schemas.enums import EvidenceStrength, SectionKind, SkillSource

DEMONSTRATING_SECTIONS = frozenset(
    {SectionKind.EXPERIENCE, SectionKind.PROJECTS, SectionKind.PUBLICATIONS}
)

EXACT_CONFIDENCE = 0.95
FUZZY_SCORE_THRESHOLD = 92.0
FUZZY_CONFIDENCE_CEILING = 0.8
MIN_FUZZY_TOKEN_LENGTH = 6

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9+#.]+")


@dataclass(frozen=True, slots=True)
class Token:
    original: str
    lowered: str


@dataclass
class MatchAccumulator:
    entry: SkillEntry
    sections: set[SectionKind]
    confidence: float
    fuzzy: bool


def extract_skills(document: Document, sections: list[DetectedSection]) -> list[Skill]:
    taxonomy = get_taxonomy()
    texts = section_texts(document, sections)

    matches: dict[str, MatchAccumulator] = {}
    for kind, text in texts.items():
        collect_exact_matches(text, kind, taxonomy, matches)

    for kind, text in texts.items():
        collect_fuzzy_matches(text, kind, taxonomy, matches)

    return [build_skill(match) for match in sorted(matches.values(), key=sort_key)]


def sort_key(match: MatchAccumulator) -> tuple[int, str, str]:
    demonstrated = 0 if match.sections & DEMONSTRATING_SECTIONS else 1
    return demonstrated, match.entry.category, match.entry.name.lower()


def section_texts(document: Document, sections: list[DetectedSection]) -> dict[SectionKind, str]:
    texts: dict[SectionKind, str] = {}

    for section in sections:
        if section.word_count == 0:
            continue

        lines = [
            document.line_at(index)
            for index in range(section.location.line_start, section.location.line_end + 1)
        ]
        body = " ".join(line.text for line in lines if line is not None)
        if not body:
            continue

        texts[section.kind] = f"{texts.get(section.kind, '')} {body}".strip()

    return texts


def tokenise_with_case(text: str) -> list[Token]:
    return [
        Token(original=match.group(), lowered=match.group().lower())
        for match in _TOKEN_PATTERN.finditer(text)
    ]


def collect_exact_matches(
    text: str,
    kind: SectionKind,
    taxonomy: Taxonomy,
    matches: dict[str, MatchAccumulator],
) -> None:
    tokens = tokenise_with_case(text)
    longest = taxonomy.longest_surface
    position = 0

    while position < len(tokens):
        matched_length = 0

        for length in range(min(longest, len(tokens) - position), 0, -1):
            window = tokens[position : position + length]
            surface = " ".join(token.lowered for token in window)
            entry = taxonomy.by_surface.get(surface)

            if entry is None:
                continue
            if entry.strict and not accepts_strict_match(entry, window, kind):
                continue

            record(matches, entry, kind, EXACT_CONFIDENCE, fuzzy=False)
            matched_length = length
            break

        position += matched_length if matched_length else 1


def accepts_strict_match(entry: SkillEntry, window: list[Token], kind: SectionKind) -> bool:
    if kind is not SectionKind.SKILLS:
        return False
    written = " ".join(token.original for token in window)
    return written == entry.name or written in entry.surfaces


def collect_fuzzy_matches(
    text: str,
    kind: SectionKind,
    taxonomy: Taxonomy,
    matches: dict[str, MatchAccumulator],
) -> None:
    candidates = fuzzy_candidate_surfaces(taxonomy)
    if not candidates:
        return

    for token in tokenise_with_case(text):
        if len(token.lowered) < MIN_FUZZY_TOKEN_LENGTH:
            continue

        result = process.extractOne(
            token.lowered, candidates, scorer=fuzz.ratio, score_cutoff=FUZZY_SCORE_THRESHOLD
        )
        if result is None:
            continue

        surface, score, _ = result
        entry = taxonomy.by_surface[surface]
        if entry.id in matches:
            continue

        confidence = min(FUZZY_CONFIDENCE_CEILING, score / 100.0)
        record(matches, entry, kind, confidence, fuzzy=True)


def fuzzy_candidate_surfaces(taxonomy: Taxonomy) -> list[str]:
    return [
        surface
        for surface, entry in taxonomy.by_surface.items()
        if not entry.strict and " " not in surface and len(surface) >= MIN_FUZZY_TOKEN_LENGTH
    ]


def record(
    matches: dict[str, MatchAccumulator],
    entry: SkillEntry,
    kind: SectionKind,
    confidence: float,
    fuzzy: bool,
) -> None:
    existing = matches.get(entry.id)

    if existing is None:
        matches[entry.id] = MatchAccumulator(
            entry=entry, sections={kind}, confidence=confidence, fuzzy=fuzzy
        )
        return

    existing.sections.add(kind)
    if confidence > existing.confidence:
        existing.confidence = confidence
        existing.fuzzy = fuzzy


def build_skill(match: MatchAccumulator) -> Skill:
    demonstrated = bool(match.sections & DEMONSTRATING_SECTIONS)

    return Skill(
        name=match.entry.name,
        canonical_id=match.entry.id,
        category=match.entry.category,
        source=SkillSource.GAZETTEER,
        evidence=EvidenceStrength.DEMONSTRATED if demonstrated else EvidenceStrength.CLAIMED,
        found_in=sorted(match.sections, key=lambda kind: kind.value),
        confidence=round(match.confidence, 2),
    )


def claimed_only_skills(skills: list[Skill]) -> list[Skill]:
    return [skill for skill in skills if skill.evidence is EvidenceStrength.CLAIMED]

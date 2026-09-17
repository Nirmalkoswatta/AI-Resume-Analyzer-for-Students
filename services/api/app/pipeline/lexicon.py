import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.schemas.enums import SectionKind

HEADINGS_PATH = Path(__file__).resolve().parents[1] / "resources" / "headings.yaml"

_NON_ALPHANUMERIC = re.compile(r"[^a-z0-9 ]+")
_REPEATED_SPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class HeadingLexicon:
    alias_to_kind: dict[str, SectionKind]
    expected_sections: tuple[SectionKind, ...]

    def kind_for(self, text: str) -> SectionKind | None:
        return self.alias_to_kind.get(normalise(text))


def normalise(text: str) -> str:
    lowered = text.strip().lower()
    stripped = _NON_ALPHANUMERIC.sub(" ", lowered)
    return _REPEATED_SPACE.sub(" ", stripped).strip()


@lru_cache(maxsize=1)
def get_heading_lexicon() -> HeadingLexicon:
    raw: dict[str, Any] = yaml.safe_load(HEADINGS_PATH.read_text(encoding="utf-8"))

    alias_to_kind: dict[str, SectionKind] = {}
    for kind_name, aliases in raw["aliases"].items():
        kind = SectionKind(kind_name)
        for alias in aliases:
            alias_to_kind[normalise(alias)] = kind

    expected = tuple(SectionKind(name) for name in raw["expected_sections"])

    return HeadingLexicon(alias_to_kind=alias_to_kind, expected_sections=expected)

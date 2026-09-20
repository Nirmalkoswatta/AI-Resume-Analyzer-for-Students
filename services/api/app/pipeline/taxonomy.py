import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

SKILLS_PATH = Path(__file__).resolve().parents[1] / "resources" / "skills.yaml"

_TOKEN_SEPARATOR = re.compile(r"[^a-z0-9+#.]+")
_TRAILING_NOISE = re.compile(r"[.]+$")


@dataclass(frozen=True, slots=True)
class SkillEntry:
    id: str
    name: str
    category: str
    strict: bool
    surfaces: tuple[str, ...]

    @property
    def max_surface_length(self) -> int:
        return max(len(surface.split()) for surface in self.surfaces)


@dataclass(frozen=True)
class Taxonomy:
    source: str
    version: str
    entries: tuple[SkillEntry, ...]
    by_surface: dict[str, SkillEntry] = field(default_factory=dict)
    strict_surfaces: frozenset[str] = frozenset()

    @property
    def longest_surface(self) -> int:
        return max((entry.max_surface_length for entry in self.entries), default=1)


def normalise_token(token: str) -> str:
    return _TRAILING_NOISE.sub("", token.strip().lower())


def tokenise(text: str) -> list[str]:
    lowered = text.lower()
    return [token for token in _TOKEN_SEPARATOR.split(lowered) if token]


def normalise_surface(surface: str) -> str:
    return " ".join(tokenise(surface))


@lru_cache(maxsize=1)
def get_taxonomy() -> Taxonomy:
    raw: dict[str, Any] = yaml.safe_load(SKILLS_PATH.read_text(encoding="utf-8"))

    entries: list[SkillEntry] = []
    by_surface: dict[str, SkillEntry] = {}
    strict_surfaces: set[str] = set()

    for item in raw["skills"]:
        surfaces = build_surfaces(item)
        entry = SkillEntry(
            id=item["id"],
            name=item["name"],
            category=item["category"],
            strict=bool(item.get("strict", False)),
            surfaces=surfaces,
        )
        entries.append(entry)

        for surface in surfaces:
            by_surface.setdefault(surface, entry)
            if entry.strict:
                strict_surfaces.add(surface)

    return Taxonomy(
        source=str(raw["source"]),
        version=str(raw["version"]),
        entries=tuple(entries),
        by_surface=by_surface,
        strict_surfaces=frozenset(strict_surfaces),
    )


def build_surfaces(item: dict[str, Any]) -> tuple[str, ...]:
    raw_surfaces = [item["name"], *item.get("aliases", [])]
    surfaces = {normalise_surface(surface) for surface in raw_surfaces}
    return tuple(sorted(surface for surface in surfaces if surface))

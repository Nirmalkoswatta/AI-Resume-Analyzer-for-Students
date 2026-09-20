import argparse
import csv
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DESTINATION = REPOSITORY_ROOT / "services" / "api" / "app" / "resources" / "skills.yaml"

STRICT_NAME_MAX_LENGTH = 2
MIN_NAME_LENGTH = 2
MAX_NAME_WORDS = 5

_ID_UNSAFE = re.compile(r"[^a-z0-9]+")
_ESCO_ALT_SEPARATOR = re.compile(r"[\r\n|]+")


@dataclass
class Entry:
    name: str
    id: str
    category: str
    aliases: set[str] = field(default_factory=set)
    strict: bool = False


def slugify(text: str) -> str:
    return _ID_UNSAFE.sub("-", text.strip().lower()).strip("-")


def is_usable_name(name: str) -> bool:
    if len(name) < MIN_NAME_LENGTH and not name.isalpha():
        return False
    if len(name.split()) > MAX_NAME_WORDS:
        return False
    return bool(name.strip())


def read_esco(path: Path) -> Iterator[Entry]:
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            name = (row.get("preferredLabel") or "").strip()
            if not name or not is_usable_name(name):
                continue

            category = (row.get("skillType") or "skill").strip() or "skill"
            aliases = {
                alias.strip()
                for alias in _ESCO_ALT_SEPARATOR.split(row.get("altLabels") or "")
                if alias.strip() and is_usable_name(alias.strip())
            }

            yield Entry(
                name=name,
                id=f"esco:{slugify(name)}",
                category=category,
                aliases=aliases - {name},
                strict=len(name) <= STRICT_NAME_MAX_LENGTH,
            )


def read_onet(path: Path) -> Iterator[Entry]:
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            name = (row.get("Example") or "").strip()
            if not name or not is_usable_name(name):
                continue

            category = (row.get("Commodity Title") or "Technology").strip() or "Technology"

            yield Entry(
                name=name,
                id=f"onet:{slugify(name)}",
                category=category,
                strict=len(name) <= STRICT_NAME_MAX_LENGTH,
            )


def merge(entries: Iterator[Entry]) -> list[Entry]:
    merged: dict[str, Entry] = {}

    for entry in entries:
        existing = merged.get(entry.id)
        if existing is None:
            merged[entry.id] = entry
            continue
        existing.aliases |= entry.aliases

    return sorted(merged.values(), key=lambda entry: (entry.category, entry.name.lower()))


def to_document(entries: list[Entry], source: str, version: str) -> dict[str, object]:
    return {
        "source": source,
        "version": version,
        "skills": [
            {
                "name": entry.name,
                "id": entry.id,
                "category": entry.category,
                **({"aliases": sorted(entry.aliases)} if entry.aliases else {}),
                **({"strict": True} if entry.strict else {}),
            }
            for entry in entries
        ],
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert an ESCO or O*NET export into the taxonomy file the API reads. "
            "Download the source data yourself and accept its licence before running this."
        )
    )
    parser.add_argument("--source", choices=["esco", "onet"], required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument("--version", required=True)
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    if not arguments.input.exists():
        print(f"input not found: {arguments.input}", file=sys.stderr)
        return 1

    reader = read_esco if arguments.source == "esco" else read_onet
    entries = merge(reader(arguments.input))

    if arguments.limit > 0:
        entries = entries[: arguments.limit]

    document = to_document(entries, arguments.source, arguments.version)
    arguments.output.write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )

    print(f"wrote {len(entries)} skills to {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

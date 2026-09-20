import argparse
import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
PROFILE_HANDLE = re.compile(
    r"\b(?:linkedin\.com/in|github\.com|gitlab\.com)/[\w./-]+", re.IGNORECASE
)
PHONE = re.compile(r"(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,4}\d{2,4}(?!\w)")
YEAR_RANGE = re.compile(r"(?:19|20)\d{2}\s*-\s*(?:19|20)\d{2}")
POSTAL_CODE = re.compile(r"\b\d{5}(?:-\d{4})?\b")

MIN_PHONE_DIGITS = 8

EMAIL_TOKEN = "[EMAIL]"
URL_TOKEN = "[URL]"
PHONE_TOKEN = "[PHONE]"
POSTAL_TOKEN = "[POSTAL]"


def digit_count(text: str) -> int:
    return sum(character.isdigit() for character in text)


def mask_phone(match: re.Match[str]) -> str:
    candidate = match.group()
    if YEAR_RANGE.fullmatch(candidate.strip()):
        return candidate
    return PHONE_TOKEN if digit_count(candidate) >= MIN_PHONE_DIGITS else candidate


def scrub(text: str) -> str:
    """Masks emails, links, phone numbers and postal codes.

    Names and street addresses are not caught by patterns. Treat the output as reduced-risk,
    not anonymous, and run a named-entity pass before publishing any corpus.
    """
    text = EMAIL.sub(EMAIL_TOKEN, text)
    text = PROFILE_HANDLE.sub(URL_TOKEN, text)
    text = URL.sub(URL_TOKEN, text)
    text = PHONE.sub(mask_phone, text)
    return POSTAL_CODE.sub(POSTAL_TOKEN, text)


def scrub_records(lines: Iterator[str], field: str) -> Iterator[str]:
    for line in lines:
        if not line.strip():
            continue
        record = json.loads(line)
        record[field] = scrub(record[field])
        yield json.dumps(record, ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Strip contact details from a JSONL corpus.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--field", default="text", help="JSON field holding the resume text.")
    arguments = parser.parse_args()

    with arguments.input.open(encoding="utf-8") as source:
        cleaned = list(scrub_records(iter(source), arguments.field))

    arguments.output.write_text("\n".join(cleaned) + "\n", encoding="utf-8")
    sys.stdout.write(f"scrubbed {len(cleaned)} records into {arguments.output}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import json

from scrub_pii import scrub, scrub_records


def test_emails_are_masked() -> None:
    assert scrub("write to jane.doe+cv@uni.ac.uk today") == "write to [EMAIL] today"


def test_links_and_profiles_are_masked() -> None:
    cleaned = scrub("see https://jane.dev/portfolio and github.com/janedoe/repo")

    assert "jane" not in cleaned
    assert cleaned.count("[URL]") == 2


def test_international_phone_numbers_are_masked() -> None:
    assert "[PHONE]" in scrub("Call +44 20 7946 0958 anytime")
    assert "[PHONE]" in scrub("Phone: (415) 555-0132")


def test_short_numbers_such_as_years_survive() -> None:
    assert scrub("Worked 2021-2024 on 3 projects") == "Worked 2021-2024 on 3 projects"


def test_postal_codes_are_masked() -> None:
    assert scrub("Austin, TX 78701") == "Austin, TX [POSTAL]"


def test_records_keep_other_fields_and_skip_blank_lines() -> None:
    lines = iter(['{"text": "mail a@b.co", "role": "Data Analyst"}', "", "  "])

    cleaned = [json.loads(line) for line in scrub_records(lines, "text")]

    assert cleaned == [{"text": "mail [EMAIL]", "role": "Data Analyst"}]

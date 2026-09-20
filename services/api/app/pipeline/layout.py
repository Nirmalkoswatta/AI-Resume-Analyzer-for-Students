import re
from collections import Counter
from dataclasses import dataclass

from app.pipeline.document import Line, Page

HEADER_BAND_RATIO = 0.07
FOOTER_BAND_RATIO = 0.07
GUTTER_BIN_WIDTH = 3.0
MIN_GUTTER_RATIO = 0.05
GUTTER_SEARCH_MARGIN_RATIO = 0.2
MIN_LINES_FOR_COLUMN_DETECTION = 8
MIN_VERTICAL_OVERLAP_RATIO = 0.4
MAX_GUTTER_CROSSING_RATIO = 0.12
MIN_COLUMN_SHARE = 0.2
MIN_PAGES_FOR_RUNNING_FURNITURE = 2
MIN_REPEATS_FOR_RUNNING_FURNITURE = 2

_DIGITS = re.compile(r"\d+")


@dataclass(frozen=True, slots=True)
class PageBands:
    header_limit: float
    footer_limit: float


def page_bands(height: float) -> PageBands:
    return PageBands(
        header_limit=height * HEADER_BAND_RATIO,
        footer_limit=height * (1.0 - FOOTER_BAND_RATIO),
    )


def is_in_header_or_footer(line: Line, height: float) -> bool:
    bands = page_bands(height)
    return line.bottom <= bands.header_limit or line.top >= bands.footer_limit


def body_lines(lines: tuple[Line, ...], height: float) -> list[Line]:
    return [line for line in lines if not is_in_header_or_footer(line, height) and line.text]


def count_columns(lines: tuple[Line, ...], width: float, height: float) -> int:
    return 2 if detect_gutter(lines, width, height) is not None else 1


def detect_gutter(lines: tuple[Line, ...], width: float, height: float) -> float | None:
    candidates = body_lines(lines, height)
    if len(candidates) < MIN_LINES_FOR_COLUMN_DETECTION:
        return None

    gutter = find_gutter(candidates, width)
    if gutter is None:
        return None

    left, right = split_at(candidates, gutter)
    if min(len(left), len(right)) < len(candidates) * MIN_COLUMN_SHARE:
        return None
    if not vertically_overlapping(left, right):
        return None

    return gutter


def count_lines_per_bin(lines: list[Line], width: float) -> list[int]:
    bin_count = max(1, int(width / GUTTER_BIN_WIDTH))
    crossings = [0] * bin_count

    for line in lines:
        start = max(0, int(line.x0 / GUTTER_BIN_WIDTH))
        end = min(bin_count - 1, int(line.x1 / GUTTER_BIN_WIDTH))
        for index in range(start, end + 1):
            crossings[index] += 1

    return crossings


def sparse_runs(
    crossings: list[int], start: int, end: int, tolerance: int
) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    run_start: int | None = None

    for index in range(start, end):
        if crossings[index] <= tolerance:
            if run_start is None:
                run_start = index
            continue
        if run_start is not None:
            runs.append((run_start, index))
            run_start = None

    if run_start is not None:
        runs.append((run_start, end))

    return runs


def find_gutter(lines: list[Line], width: float) -> float | None:
    crossings = count_lines_per_bin(lines, width)
    bin_count = len(crossings)

    search_start = int(bin_count * GUTTER_SEARCH_MARGIN_RATIO)
    search_end = int(bin_count * (1.0 - GUTTER_SEARCH_MARGIN_RATIO))
    minimum_run = max(1, int(bin_count * MIN_GUTTER_RATIO))
    tolerance = int(len(lines) * MAX_GUTTER_CROSSING_RATIO)

    widest: tuple[int, int] | None = None

    for run_start, run_end in sparse_runs(crossings, search_start, search_end, tolerance):
        if run_end - run_start < minimum_run:
            continue
        if not any(crossings[:run_start]) or not any(crossings[run_end:]):
            continue
        if widest is None or run_end - run_start > widest[1] - widest[0]:
            widest = (run_start, run_end)

    if widest is None:
        return None

    return (widest[0] + widest[1]) / 2 * GUTTER_BIN_WIDTH


def split_at(lines: list[Line], gutter: float) -> tuple[list[Line], list[Line]]:
    left = [line for line in lines if line.x1 <= gutter]
    right = [line for line in lines if line.x0 >= gutter]
    return left, right


def vertically_overlapping(left: list[Line], right: list[Line]) -> bool:
    left_top = min(line.top for line in left)
    left_bottom = max(line.bottom for line in left)
    right_top = min(line.top for line in right)
    right_bottom = max(line.bottom for line in right)

    overlap = min(left_bottom, right_bottom) - max(left_top, right_top)
    if overlap <= 0:
        return False

    shorter = min(left_bottom - left_top, right_bottom - right_top)
    if shorter <= 0:
        return False

    return overlap / shorter >= MIN_VERTICAL_OVERLAP_RATIO


def has_running_header_or_footer(pages: tuple[Page, ...]) -> bool:
    if len(pages) < MIN_PAGES_FOR_RUNNING_FURNITURE:
        return False

    repeats: Counter[str] = Counter()
    for page in pages:
        repeats.update(
            {
                furniture_key(line.text)
                for line in page.lines
                if line.text and is_in_header_or_footer(line, page.height)
            }
        )

    return any(count >= MIN_REPEATS_FOR_RUNNING_FURNITURE for count in repeats.values())


def furniture_key(text: str) -> str:
    return _DIGITS.sub("", text).strip().lower()


def split_into_columns(lines: tuple[Line, ...], width: float, height: float) -> list[list[Line]]:
    gutter = detect_gutter(lines, width, height)
    if gutter is None:
        return [list(lines)]

    return assign_every_line(lines, gutter)


def assign_every_line(lines: tuple[Line, ...], gutter: float) -> list[list[Line]]:
    left: list[Line] = []
    right: list[Line] = []

    for line in lines:
        if line_midpoint(line) <= gutter:
            left.append(line)
        else:
            right.append(line)

    return [column for column in (left, right) if column]


def line_midpoint(line: Line) -> float:
    return (line.x0 + line.x1) / 2

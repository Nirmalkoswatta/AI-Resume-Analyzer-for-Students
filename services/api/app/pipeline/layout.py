from dataclasses import dataclass

from app.pipeline.document import Line

HEADER_BAND_RATIO = 0.07
FOOTER_BAND_RATIO = 0.07
GUTTER_BIN_WIDTH = 3.0
MIN_GUTTER_RATIO = 0.05
GUTTER_SEARCH_MARGIN_RATIO = 0.2
MIN_LINES_FOR_COLUMN_DETECTION = 8
MIN_VERTICAL_OVERLAP_RATIO = 0.4


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
    candidates = body_lines(lines, height)
    if len(candidates) < MIN_LINES_FOR_COLUMN_DETECTION:
        return 1

    gutter = find_gutter(candidates, width)
    if gutter is None:
        return 1

    left, right = split_at(candidates, gutter)
    if not left or not right:
        return 1
    if not vertically_overlapping(left, right):
        return 1

    return 2


def build_occupancy(lines: list[Line], width: float) -> list[bool]:
    bin_count = max(1, int(width / GUTTER_BIN_WIDTH))
    occupied = [False] * bin_count

    for line in lines:
        start = max(0, int(line.x0 / GUTTER_BIN_WIDTH))
        end = min(bin_count - 1, int(line.x1 / GUTTER_BIN_WIDTH))
        for index in range(start, end + 1):
            occupied[index] = True

    return occupied


def empty_runs(occupied: list[bool], start: int, end: int) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    run_start: int | None = None

    for index in range(start, end):
        if not occupied[index]:
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
    occupied = build_occupancy(lines, width)
    bin_count = len(occupied)

    search_start = int(bin_count * GUTTER_SEARCH_MARGIN_RATIO)
    search_end = int(bin_count * (1.0 - GUTTER_SEARCH_MARGIN_RATIO))
    minimum_run = max(1, int(bin_count * MIN_GUTTER_RATIO))

    widest: tuple[int, int] | None = None

    for run_start, run_end in empty_runs(occupied, search_start, search_end):
        if run_end - run_start < minimum_run:
            continue
        if not any(occupied[:run_start]) or not any(occupied[run_end:]):
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

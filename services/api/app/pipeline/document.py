from dataclasses import dataclass
from functools import cached_property


@dataclass(frozen=True, slots=True)
class Span:
    text: str
    font: str
    size: float
    bold: bool
    italic: bool
    x0: float
    top: float
    x1: float
    bottom: float


@dataclass(frozen=True)
class Line:
    index: int
    page_number: int
    spans: tuple[Span, ...]
    x0: float
    top: float
    x1: float
    bottom: float

    @cached_property
    def text(self) -> str:
        return "".join(span.text for span in self.spans).strip()

    @cached_property
    def max_font_size(self) -> float:
        return max((span.size for span in self.spans), default=0.0)

    @cached_property
    def is_bold(self) -> bool:
        return bool(self.spans) and all(span.bold for span in self.spans if span.text.strip())

    @cached_property
    def word_count(self) -> int:
        return len(self.text.split())

    @cached_property
    def is_upper_case(self) -> bool:
        letters = [character for character in self.text if character.isalpha()]
        return bool(letters) and all(character.isupper() for character in letters)


@dataclass(frozen=True)
class Page:
    number: int
    width: float
    height: float
    lines: tuple[Line, ...]
    image_count: int
    table_count: int
    character_count: int

    @cached_property
    def has_text(self) -> bool:
        return self.character_count > 0


@dataclass(frozen=True)
class Document:
    pages: tuple[Page, ...]
    font_families: tuple[str, ...]
    column_count: int
    has_text_in_header_footer: bool

    @cached_property
    def lines(self) -> tuple[Line, ...]:
        return tuple(line for page in self.pages for line in page.lines)

    @cached_property
    def page_count(self) -> int:
        return len(self.pages)

    @cached_property
    def word_count(self) -> int:
        return sum(line.word_count for line in self.lines)

    @cached_property
    def character_count(self) -> int:
        return sum(page.character_count for page in self.pages)

    @cached_property
    def image_count(self) -> int:
        return sum(page.image_count for page in self.pages)

    @cached_property
    def table_count(self) -> int:
        return sum(page.table_count for page in self.pages)

    @cached_property
    def median_font_size(self) -> float:
        sizes = sorted(line.max_font_size for line in self.lines if line.text)
        if not sizes:
            return 0.0
        middle = len(sizes) // 2
        if len(sizes) % 2 == 1:
            return sizes[middle]
        return (sizes[middle - 1] + sizes[middle]) / 2

    @cached_property
    def lines_by_index(self) -> dict[int, Line]:
        return {line.index: line for line in self.lines}

    def line_at(self, index: int) -> Line | None:
        return self.lines_by_index.get(index)

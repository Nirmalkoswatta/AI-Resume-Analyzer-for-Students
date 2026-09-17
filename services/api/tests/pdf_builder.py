import pymupdf

PAGE_WIDTH = 612.0
PAGE_HEIGHT = 792.0
BODY_FONT_SIZE = 10.0
HEADING_FONT_SIZE = 13.0

LEFT_COLUMN_X = 72.0
RIGHT_COLUMN_X = 340.0

SINGLE_COLUMN_BODY = [
    ("EDUCATION", HEADING_FONT_SIZE),
    ("BSc Computer Science, University of Colombo, 2023 - 2027", BODY_FONT_SIZE),
    ("Relevant coursework: Data Structures, Databases", BODY_FONT_SIZE),
    ("WORK EXPERIENCE", HEADING_FONT_SIZE),
    ("Software Engineering Intern, Reddy Labs, Jun 2026 - Aug 2026", BODY_FONT_SIZE),
    ("Built REST endpoints in Python and Flask", BODY_FONT_SIZE),
    ("Improved report load time from 8s to 1.2s", BODY_FONT_SIZE),
    ("PROJECTS", HEADING_FONT_SIZE),
    ("Campus event finder, a React and PostgreSQL web app", BODY_FONT_SIZE),
    ("SKILLS", HEADING_FONT_SIZE),
    ("Python, JavaScript, React, SQL, Git", BODY_FONT_SIZE),
]


def new_document() -> pymupdf.Document:
    return pymupdf.open()


def write_lines(
    page: pymupdf.Page,
    lines: list[tuple[str, float]],
    x: float,
    start_y: float,
    leading: float = 16.0,
) -> float:
    y = start_y
    for text, size in lines:
        page.insert_text((x, y), text, fontsize=size, fontname="helv")
        y += leading
    return y


def single_column_resume() -> bytes:
    document = new_document()
    page = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((LEFT_COLUMN_X, 90.0), "Priya Fernando", fontsize=16.0, fontname="helv")
    page.insert_text(
        (LEFT_COLUMN_X, 108.0),
        "priya.f@example.com | +94 77 123 4567",
        fontsize=BODY_FONT_SIZE,
        fontname="helv",
    )
    write_lines(page, SINGLE_COLUMN_BODY, LEFT_COLUMN_X, 140.0)
    return to_bytes(document)


def two_column_resume() -> bytes:
    document = new_document()
    page = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((LEFT_COLUMN_X, 90.0), "Priya Fernando", fontsize=16.0, fontname="helv")

    left = [
        ("WORK EXPERIENCE", HEADING_FONT_SIZE),
        ("Software Engineering Intern, Reddy Labs", BODY_FONT_SIZE),
        ("Built REST endpoints in Python", BODY_FONT_SIZE),
        ("Improved report load times", BODY_FONT_SIZE),
        ("Wrote unit tests for the billing module", BODY_FONT_SIZE),
        ("EDUCATION", HEADING_FONT_SIZE),
        ("BSc Computer Science, Colombo", BODY_FONT_SIZE),
        ("Graduating 2027", BODY_FONT_SIZE),
    ]
    right = [
        ("SKILLS", HEADING_FONT_SIZE),
        ("Python", BODY_FONT_SIZE),
        ("JavaScript", BODY_FONT_SIZE),
        ("React", BODY_FONT_SIZE),
        ("PostgreSQL", BODY_FONT_SIZE),
        ("Git", BODY_FONT_SIZE),
        ("Docker", BODY_FONT_SIZE),
        ("Linux", BODY_FONT_SIZE),
    ]

    write_lines(page, left, LEFT_COLUMN_X, 140.0)
    write_lines(page, right, RIGHT_COLUMN_X, 140.0)
    return to_bytes(document)


def resume_with_header_footer_text() -> bytes:
    document = new_document()
    for number in (1, 2):
        page = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        page.insert_text(
            (LEFT_COLUMN_X, 30.0),
            "priya.f@example.com | +94 77 123 4567",
            fontsize=BODY_FONT_SIZE,
            fontname="helv",
        )
        page.insert_text(
            (LEFT_COLUMN_X, PAGE_HEIGHT - 20.0),
            f"Page {number} of 2",
            fontsize=BODY_FONT_SIZE,
            fontname="helv",
        )
        write_lines(page, SINGLE_COLUMN_BODY, LEFT_COLUMN_X, 140.0)
    return to_bytes(document)


def single_page_with_edge_text() -> bytes:
    document = new_document()
    page = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((LEFT_COLUMN_X, 30.0), "Priya Fernando", fontsize=16.0, fontname="helv")
    write_lines(page, SINGLE_COLUMN_BODY, LEFT_COLUMN_X, 140.0)
    return to_bytes(document)


def multi_page_resume(page_count: int) -> bytes:
    document = new_document()
    for _ in range(page_count):
        page = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        write_lines(page, SINGLE_COLUMN_BODY, LEFT_COLUMN_X, 140.0)
    return to_bytes(document)


def scanned_resume() -> bytes:
    document = new_document()
    page = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.draw_rect(pymupdf.Rect(72, 72, 540, 700), color=(0, 0, 0), fill=(0.9, 0.9, 0.9))
    return to_bytes(document)


def encrypted_resume() -> bytes:
    document = new_document()
    page = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    write_lines(page, SINGLE_COLUMN_BODY, LEFT_COLUMN_X, 140.0)
    return document.tobytes(
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="owner",
        user_pw="user",
    )


def resume_with_creative_headings() -> bytes:
    document = new_document()
    page = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    lines = [
        ("WHERE I HAVE BEEN", HEADING_FONT_SIZE),
        ("Software Engineering Intern, Reddy Labs", BODY_FONT_SIZE),
        ("Built REST endpoints in Python and Flask", BODY_FONT_SIZE),
        ("WHAT I KNOW", HEADING_FONT_SIZE),
        ("Python, JavaScript, React, SQL, Git", BODY_FONT_SIZE),
    ]
    write_lines(page, lines, LEFT_COLUMN_X, 140.0)
    return to_bytes(document)


def to_bytes(document: pymupdf.Document) -> bytes:
    payload: bytes = document.tobytes()
    document.close()
    return payload


def resume_with_ambiguous_skills() -> bytes:
    document = new_document()
    page = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    lines = [
        ("WORK EXPERIENCE", HEADING_FONT_SIZE),
        ("Teaching Assistant, University of Colombo", BODY_FONT_SIZE),
        ("Helped students go through lab exercises each week", BODY_FONT_SIZE),
        ("Marked coursework and gave written feedback", BODY_FONT_SIZE),
        ("SKILLS", HEADING_FONT_SIZE),
        ("C, R, Go, Python", BODY_FONT_SIZE),
    ]
    write_lines(page, lines, LEFT_COLUMN_X, 140.0)
    return to_bytes(document)


def resume_with_misspelled_skills() -> bytes:
    document = new_document()
    page = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    lines = [
        ("WORK EXPERIENCE", HEADING_FONT_SIZE),
        ("Software Engineering Intern, Reddy Labs", BODY_FONT_SIZE),
        ("Deployed services with Kubernets and Dockr", BODY_FONT_SIZE),
        ("SKILLS", HEADING_FONT_SIZE),
        ("Javascripts, Kubernets", BODY_FONT_SIZE),
    ]
    write_lines(page, lines, LEFT_COLUMN_X, 140.0)
    return to_bytes(document)


def scrambled_block_order_resume() -> bytes:
    document = new_document()
    page = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)

    blocks = [
        (620.0, [("SKILLS", HEADING_FONT_SIZE), ("Python, React, SQL, Git", BODY_FONT_SIZE)]),
        (
            420.0,
            [
                ("EDUCATION", HEADING_FONT_SIZE),
                ("BSc Computer Science, University of Colombo", BODY_FONT_SIZE),
            ],
        ),
        (
            220.0,
            [
                ("WORK EXPERIENCE", HEADING_FONT_SIZE),
                ("Software Engineering Intern, Reddy Labs", BODY_FONT_SIZE),
                ("Built REST endpoints in Python and Flask", BODY_FONT_SIZE),
            ],
        ),
        (120.0, [("Priya Fernando", 16.0), ("priya.f@example.com", BODY_FONT_SIZE)]),
    ]

    for start_y, lines in blocks:
        write_lines(page, lines, LEFT_COLUMN_X, start_y)

    return to_bytes(document)


def two_column_resume_under_full_width_banner() -> bytes:
    document = new_document()
    page = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    write_lines(
        page,
        [
            ("Priya Fernando", 16.0),
            ("Final year computer science student looking for a backend internship where", 10.0),
            ("I can keep building the Python services I started at Reddy Labs last summer.", 10.0),
        ],
        LEFT_COLUMN_X,
        90.0,
    )

    left = [
        ("WORK EXPERIENCE", HEADING_FONT_SIZE),
        ("Software Engineering Intern, Reddy Labs", BODY_FONT_SIZE),
        ("Built REST endpoints in Python", BODY_FONT_SIZE),
        ("Improved report load times", BODY_FONT_SIZE),
        ("Wrote unit tests for the billing module", BODY_FONT_SIZE),
        ("EDUCATION", HEADING_FONT_SIZE),
        ("BSc Computer Science, Colombo", BODY_FONT_SIZE),
        ("Graduating 2027", BODY_FONT_SIZE),
    ]
    right = [
        ("SKILLS", HEADING_FONT_SIZE),
        ("Python", BODY_FONT_SIZE),
        ("JavaScript", BODY_FONT_SIZE),
        ("React", BODY_FONT_SIZE),
        ("PostgreSQL", BODY_FONT_SIZE),
        ("Git", BODY_FONT_SIZE),
        ("Docker", BODY_FONT_SIZE),
        ("Linux", BODY_FONT_SIZE),
    ]

    write_lines(page, left, LEFT_COLUMN_X, 180.0)
    write_lines(page, right, RIGHT_COLUMN_X, 180.0)
    return to_bytes(document)


def resume_with_title_case_headings() -> bytes:
    document = new_document()
    page = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    write_lines(
        page,
        [
            ("Priya Fernando", 20.0),
            ("Summary", HEADING_FONT_SIZE),
            ("Final year computer science student.", BODY_FONT_SIZE),
            ("Skill Highlights", HEADING_FONT_SIZE),
            ("Python, JavaScript, React, SQL, Git", BODY_FONT_SIZE),
            ("Experience", HEADING_FONT_SIZE),
            ("Software Engineering Intern, Reddy Labs", BODY_FONT_SIZE),
            ("Education", HEADING_FONT_SIZE),
            ("BSc Computer Science, Colombo", BODY_FONT_SIZE),
            ("Languages", HEADING_FONT_SIZE),
            ("Sinhala, Tamil, English", BODY_FONT_SIZE),
        ],
        LEFT_COLUMN_X,
        90.0,
    )
    return to_bytes(document)

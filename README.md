# AI Resume Analyzer for Students

Upload a resume PDF and get back an ATS-friendliness score with every check shown, a
structure audit, extracted skills, predicted role fit, a gap analysis against a target job
posting, and a prioritised list of fixes.

No LLM. Analysis is a deterministic rule pipeline plus classical ML models trained on
public datasets, with a small pretrained sentence encoder for semantic job matching.

## Layout

| Path | What lives there |
| --- | --- |
| `apps/web` | Next.js 16 frontend |
| `services/api` | FastAPI service and the analysis pipeline |
| `packages/schema` | OpenAPI spec and the TypeScript types generated from it |
| `ml` | Dataset preparation, model training, evaluation |
| `infra` | Dockerfiles |

## Running it

Both services, containerised:

```bash
docker compose up --build
```

Or run them directly. API first:

```bash
cd services/api && python -m venv .venv && ./.venv/Scripts/python.exe -m pip install -e ".[dev]" && ./.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000
```

Then the web app:

```bash
npm install && npm run dev
```

The frontend is on http://localhost:3000, the API on http://localhost:8000, and interactive
API docs on http://localhost:8000/docs.

## The API contract

`services/api/app/schemas/` is the single source of truth. The TypeScript types the
frontend imports are generated from it, never hand-written.

After changing any schema:

```bash
python services/api/scripts/export_openapi.py && npm run schema:types
```

Commit `packages/schema/openapi.json` and `packages/schema/src/api.d.ts` alongside the
change. CI regenerates both and fails if what you committed is stale, so the frontend can
never silently drift from the backend.

`packages/schema/src/index.ts` is hand-written and maps the generated shapes to readable
names. Add an alias there when you add a schema.

## Configuration

API settings are environment variables prefixed `RESUME_API_`, defined in
`services/api/app/config.py`. List-valued settings must be JSON, and the service fails at
startup rather than falling back to a default if one is malformed:

```bash
RESUME_API_ALLOWED_ORIGINS='["https://yourdomain.com"]'
```

The frontend reads `RESUME_API_URL` server-side only. The browser never calls the API
directly; requests go through `apps/web/app/api/analyze/route.ts`, which keeps the service
off the public internet.

## Checks

```bash
cd services/api && ./.venv/Scripts/python.exe -m ruff check . && ./.venv/Scripts/python.exe -m mypy app scripts && ./.venv/Scripts/python.exe -m pytest
```

```bash
npm run lint && npm run typecheck --workspace @resume/web && npm run build
```

## Conventions

**No comments.** If a line needs one, the name is wrong or the function is too big. Rename
it or extract it. Multi-clause booleans become named predicates. The only exception is a
short docstring on a public entry point where units, ranges, or failure modes are not
inferable from the signature.

Python is Ruff-formatted at 100 columns and passes `mypy --strict`. Pipeline stages in
`app/pipeline/` are pure functions with no I/O and no globals, which is what makes the
golden-file tests possible. Thresholds and rubric weights live in config, never inline.

TypeScript is strict with no `any`. API types come from `packages/schema`. Server
Components by default.

## The pipeline

`app/pipeline/` runs in order, each stage a pure function over the previous stage's output:

| Stage | Does | Trained? |
| --- | --- | --- |
| `ingest` | PyMuPDF to `Document`: lines, spans, fonts, sizes, bounding boxes, columns | No |
| `segment` | Lines to sections using `resources/headings.yaml` plus font and case signals | No |
| `ats` | Weighted rubric from `resources/ats_rubric.yaml` | No |
| `advise` | Failed checks and missing sections to prioritised suggestions | No |
| `skills` | Taxonomy match over `resources/skills.yaml`, with fuzzy recovery | No |
| `fit` | Role classifier plus job-description similarity | Planned |

`ingest` is the only module that touches PyMuPDF. Everything downstream reads the
`Document` dataclass, so nothing else depends on the PDF library.

### Tuning without touching code

Both YAML files under `app/resources/` are the knobs. `headings.yaml` holds heading
synonyms, which sections are expected, and the advice shown when one is missing;
`ats_rubric.yaml` holds each check's weight, severity, wording, and the fix it produces.
Adding a heading synonym or reweighting a check is a config change and a test, not a code
change. Bump `version` in the rubric whenever weights move, so a changed score can always
be explained.

## Skill extraction

Skills come from `resources/skills.yaml` — a seed taxonomy of 105 skills and 272
matchable surface forms, authored in-repo so there is no licensing encumbrance.

Two matching rules carry most of the weight:

- **Ambiguous short names are restricted to the Skills section.** `C`, `R`, and `Go` are
  marked `strict` in the taxonomy and are only matched there, with original casing. A resume
  saying "helped students go through lab exercises" does not know Go.
- **A skill is `demonstrated` only when it appears in Experience, Projects, or
  Publications.** Anywhere else it is `claimed`. That distinction drives both the UI grouping
  and the suggestion to go back and evidence a claim.

Typos are recovered with `rapidfuzz` above a 92 similarity threshold on tokens of six
characters or more, at reduced confidence, so a fuzzy hit is always distinguishable from an
exact one. Adding a skill or alias is a YAML edit.

### Swapping in a full taxonomy

`ml/build_gazetteer.py` converts an O*NET or ESCO export into the same file:

```bash
python ml/build_gazetteer.py --source onet --input "path/to/Technology Skills.txt" --version 2026.09
```

Download the source yourself — both sit behind a licence someone has to read and accept,
and both require attribution in the product if you ship a derived gazetteer.
**O*NET** (onetcenter.org/database.html, CC BY 4.0) is the better fit: its Technology
Skills file is a clean list of concrete tool names. **ESCO** (esco.ec.europa.eu, CC BY 4.0)
labels competences as verb phrases — you get `use Python`, not `Python` — so it needs a
verb-stripping pass before it matches resume text well.

After regenerating, run the API tests. `test_skills.py` asserts the taxonomy loads, ids are
unique, and known aliases resolve, which is the guard against a bad conversion.

## Current state

Ingestion, segmentation, ATS scoring, skill extraction, and suggestions all run on the real
uploaded file. Scores are deterministic and every check is shown with its reasoning.

Detected and rejected with typed errors: scanned image resumes, encrypted PDFs, corrupt
files, documents over the page limit, oversized uploads, and non-PDFs renamed to `.pdf`.

Still a fixture, isolated in `app/fixtures.py`: role fit and job-description matching. That
needs the trained classifier and the sentence encoder.

Next, all landing in `ml/` and loaded by the API as finished artefacts:

- **Role classifier** — TF-IDF into LinearSVC over a public resume corpus. Dedupe by cosine
  similarity before splitting; near-duplicate resumes across the split inflate accuracy badly.
- **Skill NER** — `sklearn-crfsuite` over the public annotated resume set, to catch skills
  absent from the taxonomy. A supplement to the gazetteer, never a replacement.
- **Job-description matching** — `all-MiniLM-L6-v2` embeddings alongside the keyword gap.

Strip PII at ingest before training on any public resume corpus. Those datasets contain
real people's names, emails, and phone numbers, and nothing downstream needs identity.

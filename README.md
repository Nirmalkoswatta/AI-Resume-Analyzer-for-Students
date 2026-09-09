# AI Resume Analyzer for Students

Upload a resume PDF and get back an ATS-friendliness score with every check shown, a
structure audit, extracted skills, predicted role fit, a gap analysis against a target job
posting, and a prioritised list of fixes.

No LLM. Analysis is a deterministic pipeline driven by editable config: the same PDF
always produces the same score, and every judgement traces back to a rule you can read.
Trained models are planned where the rules run out, not used as the starting point.

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
| `fit` | Role profiles from `resources/roles.yaml`, job-description gap analysis | No |

`ingest` is the only module that touches PyMuPDF. Everything downstream reads the
`Document` dataclass, so nothing else depends on the PDF library.

### Tuning without touching code

Four YAML files under `app/resources/` are the knobs, and most tuning is editing them
rather than writing code:

| File | Controls |
| --- | --- |
| `headings.yaml` | Heading synonyms, expected sections, advice when one is missing |
| `ats_rubric.yaml` | Each check's weight, severity, wording, and the fix it produces |
| `skills.yaml` | The skill taxonomy: names, aliases, categories, strict matching |
| `roles.yaml` | Role profiles as lists of skill ids |

Bump `version` in the rubric whenever weights move, so a changed score can always be
explained. Adding a heading synonym, a skill alias, or a role is a config change and a
test, never a code change.

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

## Role fit and job matching

Both reuse the skill taxonomy rather than adding a model.

**Job-description matching** runs the same matcher over the pasted posting, then diffs
against the resume. `missing_skills` is the output that matters; `similarity` is just the
matched fraction. Importance is how often the posting repeats a skill, so a requirement
named three times outranks one mentioned in passing. A posting with no recognisable skills
returns no match block rather than a fabricated score.

**Role prediction** scores the extracted skills against the profiles in
`resources/roles.yaml`. Two things stop it degenerating:

- Skills are weighted by **distinctiveness** — one over the number of roles listing them —
  so Git and Python barely move the ranking while Terraform or Figma do. Without this,
  small generic profiles win every time.
- Demonstrated skills count more than merely claimed ones.

### The ceiling here

This is a rules approach, not the trained classifier the project plans for. It is honest
about what it knows: it can only predict roles listed in `roles.yaml`, using skills present
in `skills.yaml`. A resume full of skills outside the taxonomy will rank poorly for reasons
the student cannot see. It costs no dependencies, no model download, no training corpus,
and it is fully explainable, which is why it ships first.

Swap it for a trained model when the seed rules visibly mispredict on real resumes. That
work needs a public resume corpus, which has licensing and PII questions attached — see the
taxonomy section above for the same tradeoff.

## Current state

The whole pipeline runs on the real uploaded file. No fixtures remain. Scores are
deterministic and every check is shown with its reasoning.

Detected and rejected with typed errors: scanned image resumes, encrypted PDFs, corrupt
files, documents over the page limit, oversized uploads, and non-PDFs renamed to `.pdf`.

Not built yet:

- **PDF report export** — render the result to a downloadable file.
- **Rate limiting** — before this is exposed publicly.
- **Trained models** — role classifier and skill NER, per the ceiling noted above. Strip PII
  at ingest before training on any public resume corpus; those datasets contain real
  people's names, emails, and phone numbers, and nothing downstream needs identity.

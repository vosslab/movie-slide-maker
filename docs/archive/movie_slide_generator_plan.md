# Plan: Interactive movie-slide generator

Status: Complete and archived on 2026-07-21. All milestones passed autonomous acceptance, and a
fresh independent subagent approved the integrated implementation, command results, and retained
render evidence.

## Context

The maintainer has an ignored local reference corpus under `SLIDE_ARTIFACTS/` with
movie-introduction slides that share a stable layout: a centered `Title (Year)` header, a left
outline of movie facts and ratings, and a right-side poster. This corpus supports planning,
comparison, and optional template regeneration; it is not a shipped input or permanent repository
artifact. The committed extracted template supplies the runtime visual styling. The generator fills
that design with current movie data and produces an OpenDocument Presentation.

The primary local reference is `SLIDE_ARTIFACTS/class02b-pre-film_content.odp`, including its hidden
movie layout and `lecture99-template_2017` master. It establishes the user-visible labels, bullet
meaning, typography intent, poster region, and 28 cm by 17.5 cm landscape page. The permanent
runtime asset derived from it is `template/movie_slide_template.pptx`.

## Locked product requirements

- The single-movie workflow is interactive and accepts title plus year, IMDb id or URL, and TMDB id
  or URL. Ambiguous title searches present a numbered choice menu.
- TMDB supplies title, year, plot, broad genres, runtime minutes, director, cross-provider ids, and
  poster.
- IMDb supplies rating and vote count.
- Rotten Tomatoes supplies the current Tomatometer, fresh or rotten state, and critics consensus.
  The critics consensus is mandatory.
- Metacritic supplies the current Metascore. The Metascore is mandatory.
- Every successful run uses live provider data gathered during that run.
- Validate provider identity and mandatory fields before presentation creation. A failure raises a
  clear error naming the source, movie, and attempted URL or id, then stops the run before output.
- The reference slide supplies the field labels, bullet hierarchy, layout intent, and typography.
- The single-movie product deliverable is `./<slug>.odp`. The intermediate `.pptx` is scratch and
  is removed after the ODP passes semantic validation.
- The batch review artifact is `output_smoke/review_deck.odp`.

## Objectives

- Resolve one movie identity consistently across all four providers.
- Assemble one typed `MovieData` value containing only fields used by the slide builder.
- Fill the extracted template while preserving its visual design as the design authority.
- Preserve the reference slide's literal user-visible labels and bullet meaning while allowing
  representation-independent XML and provider details to vary.
- Keep fast pytest checks pure, deterministic, inline, network-free, and comfortably below one
  second.
- Put live HTTP, real files, template conversion, LibreOffice, and rendering checks in directly
  runnable `tests/e2e/e2e_*.py` scripts.
- Finish every milestone through manager and subagent execution while the maintainer is away.
- Produce durable normal, long-text, and multi-movie render evidence that automated checks and an
  independent subagent can review without opening an office application interactively.

## Design principles

Template fill keeps the master as the design authority. Provider modules remain replaceable behind
one `MovieData` contract. Semantic checks inspect meaning rather than serializer output: frame roles,
text, properties, geometry with tolerances, provider identity, required field presence, and plausible
ranges.

The autonomous acceptance path is intentionally small. M11 scripts the resolver choice, M12 injects
provider results for one success and one mandatory-field abort, M15 captures and checks normal and
long-text renders, and M18 captures and checks every batch-deck page. These harnesses complement the
live product runs without adding a captured-provider fixture matrix, perceptual hashing, or a
product-specific permanent pytest. Maintainer viewing is optional and never blocks completion.

The implementation follows the repository's **atomic task decomposition**, **prompt positively**,
**focus on important issues**, and **finish the obvious** principles from
[`docs/REPO_STYLE.md`](../REPO_STYLE.md). Each patch has one owner, one bounded outcome, one
verification command set, and a manager-recorded handoff. One fresh independent subagent reviews
the integrated implementation and captured acceptance evidence before closeout.

## Source authorities

- The reference deck owns user-visible labels, bullet hierarchy, master/layout choice, typography
  intent, and poster placement intent.
- Live TMDB, IMDb, Rotten Tomatoes, and Metacritic results own movie values.
- The provider identity contract uses IMDb id as the cross-provider anchor. Rotten Tomatoes and
  Metacritic candidates also match at least two of title, release year, and director.
- TMDB runtime is already integer minutes and flows directly into `MovieData`.

## Scope boundaries

- Generate a standalone slide deck; the user can insert the result into another lecture deck.
- Use the interactive single-movie workflow and the list-driven batch review workflow.
- Show director names while leaving subjective notable-film additions to the user.
- Target movies on the repository's supported macOS, LibreOffice Still, and OpenDyslexic setup.
- Use polite, single-movie or short-batch request rates with randomized delays.
- Represent reference highlights with escaped-Unicode colored-square marks supported by the chosen
  presentation library.

## Architecture and ownership

Runtime code lives in the `slide_maker/` package. The only final root-level Python file is the thin
interactive entry stub `make_movie_slide.py`; it gathers CLI input and dispatches into the package.
Maintainer-only discovery and template extraction scripts live under `devel/`. Verification follows
[`docs/PYTEST_STYLE.md`](../PYTEST_STYLE.md),
[`tests/TESTS_README.md`](../../tests/TESTS_README.md), and
[`docs/E2E_TESTS.md`](../E2E_TESTS.md).

- `slide_maker/__init__.py`: one-line package docstring with no imports or re-exports.
- `slide_maker/moviedata.py`: typed provider-to-builder contract and mandatory-field validation,
  owned by M1 under `D-CONTRACT`.
- `slide_maker/config.py`: load the required root-local `read_token` from `tmdb_key.yml`.
- `tmdb_key_sample.yml`: documented sample containing only `read_token`.
- `slide_maker/http_client.py`: shared `curl_cffi` policy for headers, timeout, randomized delay,
  and one bounded retry for 403 or 429.
- `slide_maker/tmdb_client.py`: TMDB search, cross-map, details, credits, and poster download.
- `slide_maker/imdb_ratings.py`: IMDb rating and votes via `imdbinfo`, with a probe-supported JSON-LD
  path when required.
- `slide_maker/rt_scraper.py`: Tomatometer, fresh/rotten state, and mandatory critics consensus.
- `slide_maker/metacritic_scraper.py`: mandatory Metascore.
- `slide_maker/movie_input.py`: pure classifier and IMDb id extraction from ids and URLs.
- `slide_maker/movie_resolver.py`: interactive TMDB-backed disambiguation with injectable input for
  scripted acceptance.
- `slide_maker/slide_builder.py`: append one template-based slide from `MovieData`.
- `slide_maker/emoji_marks.py`: escaped-Unicode presentation marks plus pure Rotten Tomatoes state
  and Metascore band helpers, owned with `slide_maker/moviedata.py` by M1 under `D-CONTRACT`.
- `slide_maker/slide_convert.py`: LibreOffice conversion, semantic ODP validation, and conditional
  scratch cleanup.
- `slide_maker/movie_pipeline.py`: interactive single-movie orchestration.
- `make_movie_slide.py`: thin runnable root input and dispatch stub.
- `slide_maker/review_deck.py`: module-based short-batch pipeline producing
  `output_smoke/review_deck.odp`.
- `devel/probe_sources.py`: runnable, evidence-producing provider probe that imports
  `slide_maker.config` for TMDB credentials and `slide_maker.http_client` for every live request.
- `devel/extract_slide_template.py`: runnable template extraction and anchor-discovery tool.
- `template/movie_slide_template.pptx`: extracted master and required movie layout.
- `tests/e2e/e2e_*.py`: directly runnable integration checks listed below.

## Cross-cutting Python rules

Apply these rules to every planned Python file:

- Add full parameter and return annotations to every function. Use built-in generics, PEP 604
  unions, and `collections.abc`.
- Group imports as Standard Library, PIP3 modules, then local repo modules. Within each group, order
  by module-name length and alphabetically for equal lengths.
- Import runtime modules through absolute package-qualified names such as
  `import slide_maker.http_client`. Keep `slide_maker/__init__.py` limited to its docstring.
- Use tabs for indentation and ASCII source. Encode presentation symbols with escapes.
- Put `#!/usr/bin/env python3` on directly runnable scripts and set their executable bit. The
  runnable scripts are `devel/probe_sources.py`, `devel/extract_slide_template.py`, and the sole
  root product entry `make_movie_slide.py`. Run the batch entry as a package module.
- Plain developer and runtime scripts use explicit validation exceptions. Tests own assertions in
  `tests/test_*.py` and correctly named `tests/e2e/e2e_*.py` files.
- Route live HTTP through `slide_maker/http_client.py`. Sleep for `random.random()` seconds before
  each live request unless the official API specifies a different policy.
- Run every repository-local Python command with `source source_me.sh && python3`.
- Name every implementation-only smoke script with a leading underscore. Create its file-shaped
  inputs inside `tempfile.TemporaryDirectory()`, then remove the scratch script and verify cleanup
  in the owning task handoff.
- Declare each direct third-party import in `pip_requirements.txt`.

## Data contract

`MovieData` contains the fields the slide renders:

- `title`, `year`, `plot`, `genres`, `runtime_minutes`, and `directors`
- `tmdb_id` and `imdb_id`
- `imdb_rating` and `imdb_votes`
- `rt_tomatometer`, `rt_state`, and `rt_consensus`
- `metascore` and `metascore_band`
- `poster_path`

Validation requires nonempty identity and display text, current RT consensus, current Metascore,
ratings in their provider ranges, positive runtime, and an existing poster path before build.

## Dependency map

| Milestone | Dependency id | Deliverable | Depends on |
| --- | --- | --- | --- |
| M0 | D-PROBE | Shared-client source probe and report | D-CONFIG, D-HTTP |
| M1 | D-CONTRACT | `slide_maker/moviedata.py`, `slide_maker/emoji_marks.py`, score semantics | - |
| M2 | D-CONFIG | `slide_maker/config.py`, `tmdb_key_sample.yml` | - |
| M3 | D-DEPS | `pip_requirements.txt` | - |
| M3b | D-HTTP | `slide_maker/http_client.py` | D-DEPS |
| M4 | D-TEMPLATE | Extraction and discovered template anchors | D-DEPS |
| M6 | D-TMDB | TMDB client and live E2E | D-PROBE, D-CONFIG, D-HTTP, D-CONTRACT |
| M7 | D-IMDB | IMDb client and live E2E | D-PROBE, D-HTTP, D-CONTRACT |
| M8 | D-RT | RT client and live E2E | D-PROBE, D-HTTP, D-CONTRACT |
| M9 | D-MC | Metacritic client and live E2E | D-PROBE, D-HTTP, D-CONTRACT |
| M10 | D-INPUT | `slide_maker/movie_input.py` | - |
| M13 | D-BUILD | Builder and real-template E2E | D-CONTRACT, D-TEMPLATE |
| M14 | D-CONVERT | Conversion and real-file E2E | D-BUILD |
| M5 | D-PACKAGE | `slide_maker/` package migration and import revalidation | D-CONFIG, D-HTTP, D-CONTRACT, D-INPUT, D-BUILD, D-CONVERT |
| M11 | D-RESOLVE | Interactive resolver and E2E | D-PACKAGE, D-INPUT, D-TMDB |
| M12 | D-ORCH | Package pipeline, root CLI stub, live Her ODP | D-PACKAGE, D-RESOLVE, D-TMDB, D-IMDB, D-RT, D-MC, D-BUILD, D-CONVERT |
| M15 | D-VISUAL | Semantic ODP and render acceptance | D-PACKAGE, D-CONVERT |
| M18 | D-DECK | Package batch module, review deck, and E2E | D-PACKAGE, D-ORCH, D-BUILD, D-CONVERT |
| M17 | D-DOCS | Usage, install, README, changelog | D-ORCH, D-VISUAL, D-DECK |

## Milestones and work packages

### M0: Probe sources

After M2 and M3b release `D-CONFIG` and `D-HTTP`, run `devel/probe_sources.py` against a small
representative movie set. The probe imports `slide_maker.config` for TMDB credentials and uses
`slide_maker.http_client` for every live HTTP request, sharing the production headers, randomized delay,
timeout, and bounded retry behavior. Record resolved identity, response status, structured-field
presence, parse-path observations, and plausible value ranges in
`docs/active_plans/audits/movie_source_probe_report.md`. Generate run-scoped raw responses under the
ignored `output_smoke/movie_source_probe/` path. Permanent tests use inline inputs.

Verification:

```bash
source source_me.sh && python3 -m pyflakes devel/probe_sources.py
source source_me.sh && python3 -m pytest tests/test_import_requirements.py tests/test_function_typing.py
source source_me.sh && python3 devel/probe_sources.py
```

The plain probe script uses explicit validation exceptions for failed rows. Its E2E consumers own
assertions.

### M1: Define data and score semantics

Implement the typed `MovieData` fields and one pure mandatory-field validator in
`slide_maker/moviedata.py`. Implement escaped-Unicode presentation marks and two pure score helpers
in `slide_maker/emoji_marks.py`: Rotten
Tomatoes scores below 60 map to rotten and scores of 60 or higher map to fresh; Metascores below 40
map to the low band, scores from 40 through 60 map to the middle band, and scores of 61 or higher
map to the high band. `D-CONTRACT` owns these shared boundary rules for providers, the builder, and
temporary M5 smoke verification. Keep the data contract limited to rendered values and
cross-provider identity.

Verification:

```bash
source source_me.sh && python3 -m pyflakes slide_maker/moviedata.py slide_maker/emoji_marks.py
source source_me.sh && python3 -m pytest tests/test_import_requirements.py tests/test_function_typing.py
```

### M2: Load configuration

Load `read_token` by required key access from `tmdb_key.yml`. Add `tmdb_key_sample.yml` with only
the required `read_token` key and a safe placeholder. Raise a clear configuration error when the
key is absent.

Verification:

```bash
source source_me.sh && python3 -m pyflakes slide_maker/config.py
source source_me.sh && python3 -m pytest tests/test_import_requirements.py tests/test_function_typing.py
source source_me.sh && python3 -m pyflakes _smoke_config.py
source source_me.sh && python3 _smoke_config.py
rm _smoke_config.py
test ! -e _smoke_config.py
```

The implementation-only `_smoke_config.py` check creates its file-shaped inputs inside
`tempfile.TemporaryDirectory()` and uses explicit validation exceptions for the missing-key case.
M2 removes the underscore-prefixed scratch script and verifies cleanup in the same task handoff.

### M3: Declare Python dependencies

Set the direct runtime dependency list to:

- `python-pptx`
- `imdbinfo`
- `curl_cffi`
- `pyyaml`
- `pillow`

The installed LibreOffice Still application and existing `Brewfile` declaration are environment
facts. Dependency work updates Python declarations and uses read-only installed-state checks.

Verification:

```bash
source source_me.sh && python3 -m pip show python-pptx imdbinfo curl_cffi pyyaml pillow
source source_me.sh && python3 -m pytest tests/test_import_requirements.py
rg -n '^cask "libreoffice-still"$' Brewfile
soffice --version
```

### M3b: Add shared HTTP policy

Implement the typed request helper with common headers, browser impersonation, timeout, randomized
polite delay, and one bounded 403/429 retry. Provider E2Es own live HTTP proof.

Verification:

```bash
source source_me.sh && python3 -m pyflakes slide_maker/http_client.py
source source_me.sh && python3 -m pytest tests/test_import_requirements.py tests/test_function_typing.py
```

Provider E2Es prove live requests through the shared client. Focused static checks and independent
review confirm the configured headers, delay, timeout, and bounded-retry control flow.

### M4: Extract template and discover anchors

Implement `devel/extract_slide_template.py` to select the authoritative source deck, extract the
required master and movie layout, and discover the title, outline, poster, page, and font/autofit
anchors needed by later milestones. Record the selected source deck and slide. Produce
`template/movie_slide_template.pptx` and raise explicit errors when required masters, layouts,
placeholders, or anchors are absent.

M4 ends at extraction and discovery. M13 owns slide construction, M14 owns ODP conversion and
semantic acceptance, and M15 owns rendered acceptance.

Verification:

```bash
source source_me.sh && python3 devel/extract_slide_template.py
source source_me.sh && python3 -m pyflakes devel/extract_slide_template.py
source source_me.sh && python3 -m pytest tests/test_import_requirements.py tests/test_function_typing.py
```

### M5: Establish package boundary

Keep runtime implementation in `slide_maker/`, add a docstring-only `slide_maker/__init__.py`,
convert every runtime, developer, and E2E caller to absolute package-qualified imports, and restore
root-local credential lookup after the move. The ignored `SLIDE_ARTIFACTS/` directory remains local
reference material only. Revalidate completed provider, builder, and conversion work after the
move. M5 creates the only root Python file, the thin `make_movie_slide.py` input/dispatch stub, with
package-based input classification. M12 changes its package dispatch from classification-only to
the completed pipeline without moving runtime logic back to the root.

Use a disposable `_smoke_movie_helpers.py` to check input classification, score boundaries, and
mandatory `MovieData` validation. It uses inline values plus `tempfile.TemporaryDirectory()`, then
is removed and its cleanup verified. Do not add a product-specific permanent pytest file.

Verification:

```bash
source source_me.sh && python3 -m pyflakes slide_maker devel/probe_sources.py tests/e2e/
source source_me.sh && python3 -m pytest tests/test_import_dot.py tests/test_import_requirements.py tests/test_function_typing.py tests/test_init_files.py
source source_me.sh && python3 -m pyflakes _smoke_movie_helpers.py
source source_me.sh && python3 _smoke_movie_helpers.py
rm _smoke_movie_helpers.py
test ! -e _smoke_movie_helpers.py
source source_me.sh && python3 tests/e2e/e2e_build_her.py
source source_me.sh && python3 tests/e2e/e2e_convert.py
```

### M6-M9: Implement providers

Each provider owns one module and one live E2E:

- M6: `slide_maker/tmdb_client.py` plus `tests/e2e/e2e_tmdb.py`
- M7: `slide_maker/imdb_ratings.py` plus `tests/e2e/e2e_imdb.py`
- M8: `slide_maker/rt_scraper.py` plus `tests/e2e/e2e_rt.py`
- M9: `slide_maker/metacritic_scraper.py` plus `tests/e2e/e2e_metacritic.py`

Use the M0 report evidence to guide each parser implementation. Each live E2E queries a real current
movie, anchors identity to IMDb id, verifies required field presence, and checks plausible numeric
ranges. RT and Metacritic candidates also match at least two identity attributes. Provider paths
may select any valid current canonical URL or slug; acceptance concerns resolved identity and
returned meaning. RT requires consensus and raises a source error that identifies a missing
consensus. Metacritic requires Metascore and raises an equivalent source error.

The four live E2Es own provider identity, presence, and range assertions. M8 and M9 consume the
score semantics from `D-CONTRACT`; M5 verifies those pure boundary helpers with inline inputs in a
disposable smoke script.

Verification:

```bash
source source_me.sh && python3 -m pyflakes slide_maker/tmdb_client.py slide_maker/imdb_ratings.py slide_maker/rt_scraper.py slide_maker/metacritic_scraper.py
source source_me.sh && python3 -m pyflakes tests/e2e/e2e_tmdb.py tests/e2e/e2e_imdb.py tests/e2e/e2e_rt.py tests/e2e/e2e_metacritic.py
source source_me.sh && python3 -m pytest tests/test_import_requirements.py tests/test_function_typing.py
source source_me.sh && python3 tests/e2e/e2e_tmdb.py
source source_me.sh && python3 tests/e2e/e2e_imdb.py
source source_me.sh && python3 tests/e2e/e2e_rt.py
source source_me.sh && python3 tests/e2e/e2e_metacritic.py
```

### M10: Classify input

Classify title/year, IMDb id, IMDb URL, TMDB URL, and `tmdb:` prefix. Treat a bare integer as a
title. Normalize extracted IMDb ids as part of classification. M5 checks the classifier and IMDb
URL/id extraction behavior with disposable inline smoke inputs.

Verification:

```bash
source source_me.sh && python3 -m pyflakes slide_maker/movie_input.py
source source_me.sh && python3 -m pytest tests/test_import_requirements.py tests/test_function_typing.py
```

### M11: Resolve interactively

Search TMDB and present a numbered menu for ambiguous title results. The E2E supplies a short
inline result list and scripted input solely to exercise user choice; it verifies selected movie
identity rather than provider serialization or candidate ordering. The harness must complete from
one command without a person typing at the terminal.

Verification:

```bash
source source_me.sh && python3 -m pyflakes slide_maker/movie_resolver.py tests/e2e/e2e_resolver_menu.py
source source_me.sh && python3 -m pytest tests/test_import_requirements.py tests/test_function_typing.py
source source_me.sh && python3 tests/e2e/e2e_resolver_menu.py
```

### M13: Build one slide

Append one slide to a real extracted template using inline `MovieData` and a poster generated in a
runtime temporary directory. Fill the literal labels and bullet hierarchy required by the product,
apply expected font/autofit properties, and place the poster aspect-preserving within the reference
region. Inspect the resulting presentation by semantic roles and properties; accept serializer and
element-order variation.

Verification:

```bash
source source_me.sh && python3 -m pyflakes slide_maker/slide_builder.py tests/e2e/e2e_build_her.py
source source_me.sh && python3 -m pytest tests/test_import_requirements.py tests/test_function_typing.py
source source_me.sh && python3 tests/e2e/e2e_build_her.py
```

### M14: Convert and clean up

Convert a real M13 presentation through LibreOffice into `./<slug>.odp`. Accept the file after
semantic validation finds one landscape movie slide, required frame roles, required displayed
fields, and a nonempty poster. Remove the scratch PPTX after acceptance. Preserve it and raise a
clear validation exception when the ODP is missing or semantically invalid.

The E2E uses inline `MovieData`, a runtime temporary image, and automatically cleaned temporary
working files.

Verification:

```bash
source source_me.sh && python3 -m pyflakes slide_maker/slide_convert.py tests/e2e/e2e_convert.py
source source_me.sh && python3 -m pytest tests/test_import_requirements.py tests/test_function_typing.py
source source_me.sh && python3 tests/e2e/e2e_convert.py
```

### M12: Run the live Her pipeline

Implement orchestration in `slide_maker/movie_pipeline.py`. Keep `make_movie_slide.py` as the only
root Python file and limit it to CLI input plus package dispatch. Expose the provider bundle and
resolver input at the package boundary so the E2E can drive orchestration without terminal input or
network substitution inside production code.

The single M12 E2E owns two deterministic injected transitions before its live phase:

- a complete inline provider result plus runtime-generated poster reaches build, conversion, and
  semantic validation in a temporary directory;
- the same flow with one mandatory field absent raises the source/identity error and leaves no PPTX
  or ODP behind.

After those transitions pass, the E2E runs the real live `Her (2013)` path with the configured TMDB
credential and real LibreOffice. It uses provider results directly, emits a validated
`./her_2013.odp`, and checks current identity, mandatory field presence, plausible ratings, and
product labels. Validate all providers before writing the product so a provider error stops the
pipeline before output. This one injected harness replaces a broad provider-fixture matrix while
keeping the live deliverable as the product proof.

Verification:

```bash
source source_me.sh && python3 -m pyflakes make_movie_slide.py slide_maker/movie_pipeline.py tests/e2e/e2e_orchestrate_her.py
source source_me.sh && python3 -m pytest tests/test_import_requirements.py tests/test_function_typing.py
source source_me.sh && python3 tests/e2e/e2e_orchestrate_her.py
```

### M15: Accept ODP semantics and rendering

`tests/e2e/e2e_visual_accept.py` constructs normal and long-text `MovieData` inline, generates
runtime temporary posters, builds real files, converts them with LibreOffice, parses the ODP, and
renders each slide to PNG. It writes the accepted product renders to
`output_smoke/visual_accept/her_2013.png` and
`output_smoke/visual_accept/her_2013_long_text.png`; intermediate decks and the matching empty-title
and empty-outline control renders remain temporary.

The automated acceptance checks:

- one landscape page with dimensions and aspect consistent with the reference;
- title, outline, and poster frames identified by semantic role;
- expected literal labels, movie text, rating marks, and bullet meaning;
- OpenDyslexic font references and text-autofit properties;
- poster containment within the intended region, approximate centering, and preserved aspect ratio;
- converted frame geometry within 0.1 cm of the intended coordinates after unit conversion;
- a successful normal and long-text render whose output files exist and are nonempty;
- visible text activity contained inside the intended title and outline regions. The harness renders
  otherwise identical empty-title and empty-outline controls, computes each text role's changed-pixel
  bounds with Pillow, and rejects text activity outside the corresponding frame tolerance.

These checks compare parsed meaning, tolerant geometry, and render relationships; they do not use a
perceptual hash or exact whole-image identity. The two retained PNGs are durable evidence for the
final independent subagent review. Optional maintainer viewing is informational rather than an
acceptance gate.

Verification:

```bash
source source_me.sh && python3 -m pyflakes tests/e2e/e2e_visual_accept.py
source source_me.sh && python3 -m pytest tests/test_import_requirements.py tests/test_function_typing.py
source source_me.sh && python3 tests/e2e/e2e_visual_accept.py
```

### M18: Build review deck

Run the short batch through live resolution and providers, append one slide per successful movie,
convert with LibreOffice, and write `output_smoke/review_deck.odp`. The E2E verifies each accepted
record appears once with mandatory fields and that failures are reported by source and identity.
With no movie arguments, the module uses this built-in deterministic list in this exact order:
`Her (2013)`, `Cooties (2014)`, `It (2017)`, `Sinners (2025)`, and `A Ghost Waits (2020)`.
`A Ghost Waits (2020)` exercises mandatory-data failure reporting when the current sources remain
absent. Neither the no-argument module run nor its E2E reads stdin; both must finish with stdin
closed. The batch uses current provider results and the real template/file pipeline. Render every
accepted page to `output_smoke/review_deck_pages/slide_<NN>.png`. The E2E verifies that the ODP slide
count, accepted movie count, and PNG count agree; each expected title and mandatory field occurs on
exactly one slide; every PNG exists and is nonempty; and every rejected movie has a
source-and-identity entry in the run summary. These checks, plus final independent subagent review
of the deck semantics and page renders, close `D-DECK` without interactive viewing.

Verification:

```bash
source source_me.sh && python3 -m pyflakes slide_maker/review_deck.py tests/e2e/e2e_review_deck.py
source source_me.sh && python3 -m pytest tests/test_import_requirements.py tests/test_function_typing.py
source source_me.sh && python3 -m slide_maker.review_deck < /dev/null
source source_me.sh && python3 tests/e2e/e2e_review_deck.py < /dev/null
```

### M17: Document and close out

M17 completed after M18 released `D-DECK`. It added `docs/USAGE.md` and `docs/INSTALL.md`, updated
`README.md` and [`docs/CHANGELOG.md`](../CHANGELOG.md), documented both product entry points, and
linked the generated acceptance evidence. A fresh independent subagent approved the integrated
implementation, required product behavior, command results, and captured artifacts. The manager
resolved the review findings, reran the documentation checks, updated inbound references and moved
this completed plan to the archive. The filesystem move and the maintainer-owned Git index are not
acceptance gates; all product and documentation acceptance completed autonomously.

Verification:

```bash
source source_me.sh && python3 -m pytest tests/test_markdown_links.py
source source_me.sh && python3 -m pytest tests/test_ascii_compliance.py
git diff --check
# Archived-plan and inbound-link verification:
source source_me.sh && python3 -m pytest tests/test_markdown_links.py
git diff --check
```

## Workstreams

| Lane | Milestones | Outcome |
| --- | --- | --- |
| Foundations | M1, M2, M3, M3b, M5, M10 | Data, config, dependencies, HTTP, package boundary, input parsing |
| Evidence | M0 | Shared-client provider paths and identity evidence after `D-CONFIG` and `D-HTTP` |
| Template | M4 | Required master/layout/placeholders and anchor map |
| Providers | M6, M7, M8, M9 | Four independently verified live data sources |
| Interaction | M11 | Deterministic user selection over ambiguous results |
| Presentation | M13, M14, M15 | Real template build, ODP conversion, semantic/render acceptance |
| Product | M12, M18 | Live single-movie output followed by the live batch review artifact |
| Closeout | M17 | Final documentation, integrated subagent review, and autonomous archival |

Each lane hands off only its named dependency artifact. The manager records milestone command
results as work completes; targeted review remains available for a risky or failed lane. One fresh
independent subagent performs the required integrated review after all implementation and
documentation artifacts exist. The Closeout lane starts after `D-ORCH`, `D-VISUAL`, and `D-DECK`
are released.

## Test inventory

### Permanent pytest

No product-specific permanent pytest file is added. The existing repository hygiene suite remains
the fast pytest lane. Pure movie-helper behavior is verified during its owning implementation work
with a disposable underscore-prefixed smoke script that is removed before handoff.

### Direct E2E

- `tests/e2e/e2e_tmdb.py`
- `tests/e2e/e2e_imdb.py`
- `tests/e2e/e2e_rt.py`
- `tests/e2e/e2e_metacritic.py`
- `tests/e2e/e2e_resolver_menu.py`
- `tests/e2e/e2e_build_her.py`
- `tests/e2e/e2e_convert.py`
- `tests/e2e/e2e_orchestrate_her.py`
- `tests/e2e/e2e_visual_accept.py`
- `tests/e2e/e2e_review_deck.py`

Provider and orchestration E2Es use live HTTP. Build, conversion, visual, and review checks use the
real template/file/LibreOffice path with inline `MovieData` where provider integration is outside
that script's ownership, runtime-generated images, and automatically cleaned temporary working
directories. The M11 resolver uses scripted input, and M12 runs injected success/abort transitions
before its live product phase. M15 and M18 retain accepted PNG renders under `output_smoke/` for
review evidence. Every direct E2E imports runtime code through `slide_maker.<module>`.

## Acceptance gates

- Python quality: every changed Python file passes its focused sourced pyflakes command, then the
  sourced fast pytest suite passes. Full annotations, import grouping, tabs, ASCII, and shebang
  policy pass the repository hygiene suite. Plain scripts use explicit validation exceptions and
  tests own assertions.
- Package quality: runtime logic lives under `slide_maker/`, package callers use absolute qualified
  imports, and `slide_maker/__init__.py` contains only its docstring. The final repository root has
  only the thin `make_movie_slide.py` CLI input/dispatch stub and no root batch implementation.
- Provider quality: M0 report evidence guides parser implementation; live E2Es verify that identity
  matches the requested movie, ratings lie in provider ranges, votes are positive, and mandatory
  RT consensus and Metascore are present. Current canonical URL and slug details may evolve without
  changing the contract.
- Presentation quality: literal product labels and bullet meaning are present; frame roles,
  font/autofit properties, poster containment, centering, aspect preservation, and page orientation
  are semantically correct. Converted geometry uses a 0.1 cm tolerance.
- Render quality: LibreOffice produces a render file with nonzero content. Render pixels are an
  evidence artifact rather than a machine identity contract. Normal and long-text changed-pixel
  bounds remain inside the intended text frames relative to matching empty-title and empty-outline
  controls.
- Product quality: the real live Her path writes `./her_2013.odp`; mandatory sources validate before
  output, and failures stop creation with a diagnostic exception. The same orchestration boundary
  also passes one injected success transition and one injected mandatory-field abort transition.
- Batch quality: `output_smoke/review_deck.odp` passes semantic slide/field accounting and every
  accepted page has one retained nonempty PNG render.
- Review quality: one fresh independent subagent checks the integrated diff, automated command
  results, normal and long-text render evidence, batch semantics, and batch page renders. Optional
  maintainer viewing does not affect acceptance or closure.

## Verification strategy

Run the existing fast hygiene pytest suite frequently and direct E2Es at their owning integration
milestones. Implementation-only smoke scripts use underscore-prefixed names, create every
file-shaped input inside `tempfile.TemporaryDirectory()`, and run through sourced file-based lint
and behavior commands. The owning task removes each scratch script and verifies cleanup in its
handoff. Direct E2Es likewise use runtime temporary directories for generated posters,
intermediate decks, and damaged-file cases. Keep the stable `output_smoke/` location for the final
review artifact, render evidence, and probe evidence.

Semantic checks allow XML namespace, serializer, element-order, generated id, canonical provider
path, and harmless rendering variation. Assertions focus on product labels, parsed values, identity,
field presence, plausible ranges, relationships, and documented geometry tolerances.

Final repository verification:

```bash
source source_me.sh && python3 -m pytest tests/
source source_me.sh && python3 -m pytest tests/test_pyflakes_code_lint.py
source source_me.sh && python3 -m pytest tests/test_markdown_links.py
source source_me.sh && python3 -m pytest tests/test_ascii_compliance.py
source source_me.sh && python3 -m pytest tests/test_import_dot.py tests/test_init_files.py
```

Run each E2E directly with the sourced Python 3.12 pattern after its required credentials and
dependencies exist.

## Risks and mitigations

| Risk | Trigger | Mitigation |
| --- | --- | --- |
| Provider markup changes | Required structured field is absent | M0 evidence guides the parser path; live E2Es detect drift; runtime errors name source and identity |
| Cross-provider title collision | Candidate metadata conflicts | Anchor on IMDb id and require two supporting identity attributes for RT and Metacritic |
| Live values drift | Ratings differ from an older deck or run | Check identity, field presence, and plausible provider ranges |
| Rate limiting | 403 or 429 response | Shared browser-like client, randomized polite delay, one bounded retry, short batches |
| TMDB credential issue | `read_token` missing or rejected | Required-key config validation and a clear credential error before output |
| Template changes | Required layout or anchor absent | M4 discovers named roles and raises an extraction error; later E2Es validate semantic roles |
| LibreOffice conversion variation | XML ordering, ids, or minor geometry changes | Parse semantics and use 0.1 cm converted-geometry tolerance |
| Long text overflows | Plot or consensus is unusually long | Apply text autofit; compare normal and long-text renders with empty-title and empty-outline controls; require each role's changed-pixel bounds inside its text frame |
| Batch includes unavailable mandatory data | One movie lacks consensus or Metascore | Report that movie's source error and include only fully validated records |
| Hidden interactive dependency stalls unattended work | A command waits for terminal input or application viewing | Drive resolver input from the E2E, inject orchestration transitions, retain render evidence, and close through independent subagent review |

## Rollout checklist

- [x] M1 releases `slide_maker/moviedata.py`, `slide_maker/emoji_marks.py`, and the shared
  RT/Metascore boundary semantics under `D-CONTRACT`.
- [x] Required `read_token` configuration, five direct dependencies, and shared HTTP policy are
  complete.
- [x] M0 runs after `D-CONFIG` and `D-HTTP`, imports their production config and HTTP policy, records
  live identity and field evidence, and stores run-scoped captures under the ignored probe path.
- [x] M4 extracts the required master/layout and records placeholder and anchor discovery.
- [x] Four provider live E2Es pass identity, presence, and plausible-range checks.
- [x] Input classifier handles every locked form and the resolver menu completes with scripted input.
- [x] M13 builds from the real template using inline `MovieData` and a runtime poster.
- [x] M14 converts a real file, validates ODP semantics, and applies conditional scratch cleanup.
- [x] M5 revalidates the `slide_maker/` package boundary, qualified imports, root-local config,
  ignored local `SLIDE_ARTIFACTS/` role, and disposable pure-behavior smoke checks.
- [x] M12's single injected harness passes the complete success and mandatory-field abort
  transitions; the live phase writes the single-movie product deliverable.
- [x] M15 passes semantic ODP, 0.1 cm geometry, page, poster, font/autofit, normal/long-text
  changed-pixel containment, and retained-render gates.
- [x] Sourced pytest, pyflakes, link, ASCII, typing, indentation, and shebang checks pass.
- [x] M18 writes `output_smoke/review_deck.odp`, self-checks slide/field accounting, and retains one
  verified page render per accepted movie.
- [x] M17 runs after M18 and documents the implemented single-movie workflow and review-deck
  artifact, then records implementation changes in the changelog.
- [x] One fresh independent subagent approves the integrated implementation, command results, and
  M15/M18 captured evidence; the manager resolves every actionable finding.
- [x] M17 completes documentation checks, records final status, and archives the plan without a
  maintainer interaction gate.

## Rollout waves and patches

The plan contains 19 milestone patches across 19 milestone nodes. M5 replaces the retired M16
permanent-pytest patch with one package-migration and revalidation patch. M1 owns two shared contract
files in one atomic `D-CONTRACT` patch. The execution waves honor the required
M13 -> M14 -> M5 -> M11 -> M12 dependency chain:

- Wave 1a, parallel: M1, M2, M3, M10.
- Wave 1b: M3b after D-DEPS.
- Wave 2, parallel: M0 after D-CONFIG and D-HTTP; M4 after D-DEPS.
- Wave 3, parallel: M6, M7, M8, M9.
- Wave 4a: M13 after D-CONTRACT and D-TEMPLATE.
- Wave 4b: M14 after D-BUILD.
- Package correction: M5 after D-BUILD and D-CONVERT, before remaining interaction,
  orchestration, visual, and review-deck work.
- Wave 4c: M11 after D-PACKAGE, D-INPUT, and D-TMDB.
- Wave 4d: M12 after resolver, provider, builder, and converter dependencies.
- Wave 5, parallel as ready: M15 after D-PACKAGE and D-CONVERT; M18 after D-PACKAGE, D-ORCH,
  D-BUILD, and D-CONVERT.
- Wave 6, final: M17 after D-ORCH, D-VISUAL, and D-DECK.

Report progress by patch name, such as `Patch M8`, plus verification result. Patch M18 releases
`D-DECK`; Patch M17 consumes the implemented review-deck artifact, includes the single integrated
independent-review status, and is the final documentation and closeout patch.

## Work-package handoff

Every work package returns:

- changed files and dependency id produced;
- sourced verification commands and outcomes;
- generated inspectable artifacts under their prescribed path;
- explicit errors or environmental blockers;
- verified cleanup of underscore-prefixed implementation smoke scripts, when used;
- a changelog bullet under the current date;
- a status of `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`, with residual risks.

The implementation manager received the validated `output_smoke/review_deck.odp`, page renders,
self-check results, M15 normal and long-text renders, final command results, and residual-risk notes.
Independent review accepted the integrated result after its actionable findings were repaired and
rechecked. Documentation checks passed, the completed plan moved to this archive path, inbound and
relative links were recalculated, and [`docs/CHANGELOG.md`](../CHANGELOG.md) records closure.
Optional maintainer inspection and maintainer-owned Git staging do not reopen or gate the completed
plan.

## Decisions locked

- TMDB v4 Bearer authentication uses `read_token` from `tmdb_key.yml`; M0 imports the production
  config loader and routes every live request through the production HTTP client.
- Runtime implementation lives under `slide_maker/`; imports are absolute and package-qualified.
  The final root has only the thin `make_movie_slide.py` CLI stub, while batch execution uses
  `python3 -m slide_maker.review_deck`.
- `SLIDE_ARTIFACTS/` is ignored local reference material for planning, comparison, and optional
  maintainer regeneration. It is not a runtime dependency or permanent repository artifact.
- `D-CONTRACT` comprises `slide_maker/moviedata.py`, `slide_maker/emoji_marks.py`, and the shared RT
  fresh/rotten and Metascore band semantics.
- The direct Python dependency list is `python-pptx`, `imdbinfo`, `curl_cffi`, `pyyaml`, and
  `pillow`.
- Metadata and poster come from TMDB; rating and votes come from IMDb; critics consensus and
  Tomatometer come from Rotten Tomatoes; Metascore comes from Metacritic.
- The single-movie deliverable is `./<slug>.odp`.
- The batch review artifact is `output_smoke/review_deck.odp`.
- M18 releases `D-DECK` before M17 documents the implemented review artifact and closes the plan.
- Autonomous acceptance uses scripted resolver input, one injected orchestration harness, captured
  normal/long-text renders, self-checked batch page renders, and one integrated independent subagent
  review. It intentionally omits a broad fixture matrix, perceptual hashes, permanent product
  pytest, and interactive sign-off.
- The reference controls literal labels, bullet meaning, and layout intent; automated acceptance
  uses semantic identities and documented tolerances.

## Open decisions

Product decisions are complete. Provider implementation details follow the M0 evidence while
preserving the locked identity and mandatory-field contracts.

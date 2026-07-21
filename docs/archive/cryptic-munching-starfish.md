# Plan: Interactive movie-slide generator (TMDB + IMDB + RT + Metacritic to pptx/odp)

## Context

The repo (`movie-slide-maker`, fresh python template) holds a set of lecture decks in `SLIDES/`.
Each deck contains movie-intro slides in a fixed layout: a big centered `Title (Year)` header, a
left bulleted column (plot synopsis; nested IMDB rating+votes and a `Critics: RT <emoji> % / MS ##`
line; Genre; Director; Run time; Review Summary), and a right-side poster. The visual styling
(pink gradient header, OpenDyslexic font, placeholder geometry) comes from the master slide
`lecture99-template_2017`; most decks carry that movie-slide layout as a hidden final slide that is
excluded from the PDF export. Building each slide by hand is slow and repetitive.

Goal: a Python tool the user runs interactively ("input movie here"), that resolves one movie from
a title+year, an IMDB URL/id, or a TMDB URL/id (offering a choice menu on ambiguity), gathers the
required data from public sources without a paid API, and emits one movie slide in the same format
by filling a `.pptx` template (via python-pptx) and converting it to `.odp` with LibreOffice. The
master supplies all styling; the tool only injects text and the poster.

Reference format verified from `SLIDES/class02b-pre-film_content.odp` (movie "Her (2013)"):
title frame `Her (2013)`; left `outline` list (L2 bullets) with the structure above; IMDB label run
highlighted yellow, MS run highlighted green; poster frame at `x=17.78cm y=3.81cm w=8.458cm
h=12.7cm`, centered, aspect-fit. Page is 28cm x 17.5cm landscape.

## Locked requirements (product decisions, not open for review)

These are set by the user as product requirements. A plan reviewer should audit how the plan
*achieves* them (resolution/parse reliability, error behavior, verification), not relitigate
whether they should hold.

- RT critics consensus and Metacritic Metascore are mandatory fields. Difficulty of scraping is not
  a reason to weaken them; it is a reason to invest in reliable resolution, identity checks, and
  clear errors.
- Slides carry the latest live values at generation time. The reference slide's numbers are
  historical examples, never copied forward.
- The reference slide is the source of truth for structure/labels/styling; live providers are the
  source of truth for data. (Full split under "Source-of-truth split".)
- Final deliverable is `.odp`; TMDB supplies metadata+poster; genres come from TMDB at its broad
  granularity. These were chosen with the user during planning.

## Objectives

- Resolve exactly one movie from interactive input (title+year, IMDB id/URL, or TMDB id/URL), with
  a numbered disambiguation menu when a title search returns multiple candidates.
- Assemble a single `MovieData` record from TMDB (metadata + poster), IMDB (rating + votes), Rotten
  Tomatoes (tomatometer, fresh/rotten, critics consensus), and Metacritic (Metascore).
- Emit one movie slide matching the reference format: an intermediate `.pptx` filled from a
  master-carrying template, then the final `.odp` via LibreOffice headless convert. The `.odp` is
  the only deliverable the user keeps; the `.pptx` is scratch (removed after convert by default).
- Reproduce the reference slide's structure/labels/styling exactly, with all movie data populated
  from live sources at generation time (latest available values, not the reference's historical
  numbers). The "Her (2013)" slide is the acceptance demo for layout fidelity.

## Design philosophy

Template-fill over template-build: the slide's look is owned by the existing master
(`lecture99-template_2017`), so the tool injects only text and one image into a template `.pptx`
rather than restyling anything. This is the "fix the design, not the symptom" and "long-term over
short-term" trade-off from `docs/REPO_STYLE.md` -- we accept a one-time template-extraction step so
every future slide inherits master changes for free. Rejected alternative: constructing the slide
from scratch in python-pptx with hardcoded fonts/colors/gradients, which would drift from the master
and duplicate styling the master already provides. Data sources are split by strength (TMDB for
metadata+poster, IMDB for ratings, RT/Metacritic scraped for scores) behind one `MovieData`
contract so each provider is an independent, replaceable lane.

Autonomy stance ("be efficient with time", `docs/REPO_STYLE.md`): every milestone completes and
verifies using only manager + subagents, with no human step on the critical path. The single human
touchpoint is the very last close-out (M18): a person skims the multi-movie `review_deck.odp` to
sign off on text content. Every earlier gate is automated; M18 produces and self-checks the deck
autonomously, and the human review is the final close-out step, not a mid-run blocker. Live sources and
LibreOffice are driven by subagents, but each milestone's *verification* runs against captured
fixtures (recorded provider responses, a canonical `MovieData`, a sample poster) and automated
harnesses (odp-to-pdf render checks, generated-XML structural asserts, scripted-stdin drives) so the
plan finishes even if the human is asleep or a live source is briefly down. Live retrieval is
proven separately by `tests/e2e/` freshness checks that are not on the build path's critical chain.
Milestones are decomposed to the smallest independently completable, single-owner, single-verify
tasks so independent lanes dispatch in parallel and progress stays visible.

## Source-of-truth split

- Reference slide (`SLIDES/class02b-pre-film_content.odp` and the hidden template slide): the sole
  source of truth for layout, frame geometry, bullet structure, field labels, and styling. Its
  ratings/votes/scores are historical examples only and are never copied into generated slides.
- Live providers (TMDB, IMDB, RT, Metacritic): the sole source of truth for movie information and
  ratings. Every generated slide carries the latest values available at generation time.

## Mandatory-field policy (user-locked)

- Rotten Tomatoes critics consensus is mandatory. Metacritic Metascore is mandatory.
- When a mandatory source resolves and parses, the tool emits the slide with the live value. When a
  mandatory source cannot be resolved or parsed, the tool stops with a clear error naming the source,
  the movie, and the URL/id attempted, so the value is always current and real.
- The slide shows the director name(s). Auto-selecting the director's "other notable films" is out
  of scope (subjective); the slide is complete with the director name, and the user adds films by
  hand when wanted.

## Scope

- Interactive resolver accepting title+year, IMDB id/URL (`tt\d+`), and TMDB id/URL, with a choice
  menu on ambiguity.
- TMDB client (v4 `read_token` Bearer auth from the gitignored `tmdb_key.yml`, via the shared
  `http_client.py` helper) for title, year, plot, genres, runtime, director, and poster image; and
  for id cross-mapping (IMDB id <-> TMDB id).
- IMDB rating + vote count via `imdbinfo`, with a `curl_cffi` + JSON-LD fallback parser.
- Rotten Tomatoes scraper (`curl_cffi`) parsing `ld+json` and `media-scorecard-json` for
  tomatometer %, fresh/rotten (>=60% rule), optional audience score, and critics consensus.
- Metacritic scraper (`curl_cffi`) parsing `ld+json` `aggregateRating.ratingValue` for the
  Metascore.
- `MovieData` dataclass as the single provider->builder contract.
- Slide builder: python-pptx fills the template's title + body placeholders and inserts the poster
  at the fixed frame (aspect-fit, centered); then LibreOffice `soffice --headless --convert-to odp`.
  The builder appends into a given presentation, so it drives both a single-slide run and a
  multi-slide batch.
- Batch review deck: generate several movies into one multi-slide `.odp` for human review, where the
  focus is verifying the text content across movies (poster fidelity is secondary).
- One-time template `.pptx` (master + movie-slide layout) extracted from an existing deck.
- Repo wiring: `pip_requirements.txt`, `Brewfile` (LibreOffice), config sample, docs, changelog,
  and pytest for the pure-function helpers.

## Non-goals

- Merging generated slides into the user's existing external lecture decks (the batch review deck is
  a standalone file, not an insert into another deck).
- A non-interactive CLI-args-only workflow. Interactive prompting is the single interface for the
  single-movie tool; `make_review_deck.py` reads a movie list for batch. This version succeeds this
  way because the user drives it interactively per the request.
- Auto-selecting the director's "other notable films" (subjective). The slide succeeds with the
  director name; the user adds films by hand when wanted.
- TV shows, episodes, or non-movie titles.
- Caching layers, proxy rotation, or high-volume scraping hardening beyond polite throttling.
- Reproducing the reference's text-background highlight via oxml (python-pptx cannot; colored emoji
  squares stand in instead -- decided).

## Current state summary

Fresh template repo: empty `pip_requirements.txt`, empty `README.md`, `Brewfile` present, `tests/`
scaffolding with hygiene tests, `REPO_TYPE=python`. No application code yet. `SLIDES/` holds the
`.odp`/`.pptx`/`.pdf` decks that define the target format. Reference dated code exists at
`/Users/vosslab/nsh/junk-drawer/old_shell_folder/movielib.py` (IMDbPY + interactive
disambiguation + TMDB-from-IMDB patterns) -- useful as a pattern reference only; it is file-based
and uses now-dead scraping paths.

## Architecture boundaries and ownership

Small single-purpose modules at repo root (per `docs/REPO_STYLE.md`). Only `make_movie_slide.py`
is a runnable script (shebang + `__main__`); the rest are imported library modules (no shebang).

- `moviedata.py` -- `MovieData` dataclass (the provider->builder contract). Shared; owned by one WP.
- `config.py` -- load TMDB key + settings from a gitignored config file (yaml; explicit path,
  optional `--config`). Read every credential from `tmdb_key.yml`.
- `http_client.py` -- shared live-HTTP helper (curl_cffi impersonate, headers, jittered sleep,
  timeout, one retry). Every provider that hits the network calls it.
- `tmdb_client.py` -- TMDB REST calls (Bearer `read_token`): search, find-by-imdb-id, movie detail,
  credits, poster URL build.
- `imdb_ratings.py` -- `imdbinfo` wrapper for rating+votes; `curl_cffi`+JSON-LD fallback.
- `rt_scraper.py` -- Rotten Tomatoes slug resolve + `ld+json`/`media-scorecard-json` parse.
- `metacritic_scraper.py` -- Metacritic slug resolve + `ld+json` Metascore parse.
- `movie_input.py` -- pure input classifier (title+year vs `tt\d+` id/URL vs TMDB id/URL).
- `movie_resolver.py` -- interactive disambiguation menu over TMDB search; returns resolved ids.
- `slide_builder.py` -- python-pptx template fill + poster placement; appends one movie slide into a
  given presentation (reused by single and batch).
- `make_review_deck.py` -- batch entry: build several movies into one multi-slide review `.odp`.
- `slide_convert.py` -- LibreOffice odp convert + scratch pptx cleanup.
- `emoji_marks.py` -- fresh/rotten and colored-square mark constants as escaped unicode.
- `make_movie_slide.py` -- entry script: prompt, resolve, assemble `MovieData`, build slide.
- `template/movie_slide_template.pptx` -- master + movie-slide layout, auto-extracted by script.
- `devel/extract_slide_template.py` -- builds the template pptx from a `SLIDES/*.pptx` deck (no
  human step).
- `tests/fixtures/movie/` -- captured provider responses, canonical `MovieData`, sample poster,
  and the golden Her-slide structure descriptor (fixture dir approved by acceptance of this plan).
- `tests/e2e/visual_accept.py` -- odp render + structural-XML (primary) + perceptual-imagehash
  (advisory) acceptance harness.

### Mapping (milestones -> components / patches)

Each milestone is one atomic, single-owner, single-verify unit (per `docs/REPO_STYLE.md` atomic
decomposition). Dependency IDs, not milestone numbers, define ordering.

| M | Dep ID | Component / artifact | Patches |
| --- | --- | --- | --- |
| M0 probe | D-PROBE | `devel/probe_sources.py`, `docs/active_plans/audits/movie_source_probe_report.md`, raw captures | 1 |
| M1 contract | D-CONTRACT | `moviedata.py` | 1 |
| M2 config | D-CONFIG | `config.py`, `tmdb_key.sample.yml` (`tmdb_key.yml` already present) | 1 |
| M3 deps | D-DEPS | `pip_requirements.txt`, `Brewfile` | 1 |
| M3b http | D-HTTP | `http_client.py` | 1 |
| M4 template | D-TEMPLATE | `devel/extract_slide_template.py`, `template/movie_slide_template.pptx` | 1 |
| M5 fixtures | D-FIX | `tests/fixtures/movie/` (captures, canonical `MovieData`, sample poster, golden structure) | 1 |
| M6 tmdb | D-TMDB | `tmdb_client.py`, `tests/e2e/e2e_tmdb.py` | 1 |
| M7 imdb | D-IMDB | `imdb_ratings.py`, `tests/e2e/e2e_imdb.py` | 1 |
| M8 rt | D-RT | `rt_scraper.py`, `tests/e2e/e2e_rt.py` | 1 |
| M9 metacritic | D-MC | `metacritic_scraper.py`, `tests/e2e/e2e_metacritic.py` | 1 |
| M10 input classifier | D-INPUT | `movie_input.py` | 1 |
| M11 resolver | D-RESOLVE | `movie_resolver.py` | 1 |
| M12 orchestration | D-ORCH | `make_movie_slide.py` | 1 |
| M13 builder | D-BUILD | `slide_builder.py`, `emoji_marks.py` | 1 |
| M14 convert | D-CONVERT | `slide_convert.py` | 1 |
| M15 visual accept | D-VISUAL | `tests/e2e/visual_accept.py`, golden descriptor | 1 |
| M16 unit tests | D-UNIT | `tests/test_movie_helpers.py` | 1 |
| M17 docs | D-DOCS | `docs/USAGE.md`, `docs/INSTALL.md`, `README.md`, `docs/CHANGELOG.md` | 1-2 |
| M18 review deck | D-DECK | `make_review_deck.py`, `review_deck.odp` (human-review artifact) | 1 |

## Cross-cutting conventions (apply to every milestone)

Stated once here so milestone bodies stay focused on behavior and verification.

- Shared network policy: all live HTTP goes through one `http_client.py` helper (curl_cffi
  `impersonate=chrome`, common headers/Referer, per-call jittered `time.sleep(random.random())`,
  a fixed timeout, and one bounded retry on 403/429). The four provider lanes call it rather than
  each rolling their own timeouts/headers/jitter. `http_client.py` is built in Wave 1 (owner:
  expert_coder) as a dependency of the provider lanes (D-HTTP).
- Identity validation: cross-provider matching never relies on title+year alone. The IMDB id is the
  anchor -- TMDB `find` by imdb id gives the authoritative TMDB record and cross-map. RT and
  Metacritic matches are confirmed with at least two of {title, release year, director} (and the
  canonical page URL is recorded); a match that fails the check raises rather than emitting another
  film's data.
- Long-text policy: the body placeholder uses text-autofit (shrink-to-fit) and the plot is capped to
  the first 2-3 sentences; RT consensus is used verbatim. A long-text fixture (a deliberately long
  plot + consensus) is part of D-FIX and must render inside the frame in the M15 round trip.
- Supported environment: macOS + LibreOffice (`soffice`) + the OpenDyslexic font installed (as in
  the reference decks). The visual gate pins to this; structural XML checks are the primary
  invariant and a perceptual image comparison (imagehash, available) with tolerance is secondary --
  no raw exact pixel diff, which is not portable across LibreOffice/font versions.
- Every patch updates `docs/CHANGELOG.md` under the current date (per-milestone changelog lines are
  assumed, not repeated below).
- Testing policy (per `docs/PYTEST_STYLE.md`; prefer few, durable tests): write permanent
  `tests/test_*.py` for stable pure-function invariants that stay valid next week, using inline
  inputs and behavioral/round-trip/range assertions. Place checks that read a fixture, a captured
  page, the network, LibreOffice, or an exact external format in `tests/e2e/`, or use a throwaway
  `_temp.py` during development. Run the PYTEST_STYLE checklist for each permanent test and keep the
  ones that stay stable; move the rest to `tests/e2e/`.

## Milestone plan

Ordering is by dependency ID, not milestone number. Four dependency waves; max useful concurrency
noted per wave.

Sample set for probes and fixtures (chosen to stress edge cases): `Her` (2013, reference),
`Cooties` (2014, both RT critic + audience rotten -> exercises rotten marks), `It` (2017, ambiguous
RT/Metacritic slug -> exercises year disambiguation + identity check), one 2025+ release
(freshness), and one obscure low-vote film (a film that may legitimately lack RT consensus or a
Metascore -> exercises the mandatory-abort path).

| M | Title | Summary | Goal |
| --- | --- | --- | --- |
| M0 | Source probe & evidence | Empirically test each source's parse paths on the sample set, measure success, capture raw responses | Provider design is chosen from measured evidence, not assumption; fixtures captured |
| M1 | Data contract | `MovieData` dataclass | One stable provider->builder contract |
| M2 | Config loader | TMDB key + settings from gitignored config | Config resolves or fails loudly, no env vars |
| M3 | Dependencies | requirements + Brewfile | Every import + LibreOffice declared |
| M4 | Template extract | Script builds template pptx from a deck | Fillable master-carrying template, no human step |
| M5 | Fixtures | Freeze probe captures + canonical `MovieData` + poster + golden structure | Offline verification substrate for all later milestones |
| M6 | TMDB client | metadata + poster + id cross-map | Metadata resolves 3 ways; verified offline + live |
| M7 | IMDB ratings | rating + votes | Ratings resolve; verified offline + live |
| M8 | RT scraper | tomatometer + fresh/rotten + consensus (mandatory) | RT fields resolve or abort clearly |
| M9 | Metacritic scraper | Metascore (mandatory) | Metascore resolves or aborts clearly |
| M10 | Input classifier | pure input-type parse | Every input form classified deterministically |
| M11 | Resolver | interactive disambiguation menu | Ambiguous titles resolve via scriptable menu |
| M12 | Orchestration | assemble `MovieData` from all sources | Full record assembled; mandatory gaps abort |
| M13 | Slide builder | fill title/body/marks + place poster | Template filled from a `MovieData`, verified in XML |
| M14 | Convert + cleanup | odp emit + pptx removal | Deliverable `.odp` produced; scratch removed |
| M15 | Visual acceptance | render + structural-XML match + perceptual imagehash vs golden | Automated visual sign-off, no human |
| M16 | Unit tests | pure-helper pytest | Stable fast tests green |
| M17 | Docs + close-out | usage/install/readme/changelog | Repo documented and reproducible |
| M18 | Review deck | batch several movies into one multi-slide `.odp` | Human-review artifact for text-content sign-off |

Waves (max useful concurrency in parens):

- Wave 1 (~5): M0 probe, M1 contract, M2 config, M3 deps, M10 input classifier.
- Wave 1b: M3b `http_client.py` (needs D-DEPS).
- Wave 2a: M4 template (needs D-DEPS). Wave 2b: M5 fixtures (needs D-PROBE + D-CONTRACT +
  D-TEMPLATE, so strictly after M4 -- not parallel with it).
- Wave 3 (~4): M6, M7, M8, M9 (each needs D-CONTRACT + D-PROBE + D-FIX + D-HTTP; M6 also D-CONFIG).
- Wave 4a: M11 resolver (D-INPUT + D-TMDB + D-FIX), M13 builder (D-CONTRACT + D-TEMPLATE + D-FIX).
- Wave 4b: M14 convert (D-BUILD -- converts M13 output), M12 orchestration (D-RESOLVE + all
  providers).
- Wave 5: M15 visual (D-CONVERT + D-FIX), M16 unit tests, M17 docs.
- Wave 6 (final): M18 review deck (D-BUILD + D-CONVERT) -- builds + self-checks the deck; the human
  close-out review of `review_deck.odp` is the last step.

### Milestone: M0 Source probe & evidence

- Depends on: none
- Parallel-plan ready: yes (4 source lanes: tmdb, imdb, rt, metacritic).
- Exit criteria: `devel/probe_sources.py` fetches each source for all five sample movies and writes
  `docs/active_plans/audits/movie_source_probe_report.md` recording, per source and movie, three
  distinct outcomes so the metric does not penalize correct behavior:
  (a) resolution -- did the movie/page resolve; (b) parse -- when a field exists, was it read
  correctly; (c) absence -- when a field genuinely does not exist (e.g. the obscure film lacking RT
  consensus or a Metascore), was that detected as a clean absence. Success = correct outcome, which
  for the obscure film includes correctly reporting absence (which the tool later turns into a
  mandatory-abort). The report also records the winning parse path (e.g. imdbinfo vs
  `curl_cffi`+JSON-LD; RT `ld+json` vs `media-scorecard-json` vs package; MC `ld+json`; TMDB
  endpoints), the exact JSON keys read, and any block/rate-limit. Raw responses saved under
  `tests/fixtures/movie/captured/`. This is the evidence gate: no provider milestone locks its
  design until its probe rows are filled; a genuine resolution/parse failure (not a true absence)
  forces a documented alternate path before that provider proceeds.

### Milestone: M1 Data contract

- Depends on: none
- Parallel-plan ready: yes (single atomic module, no shared files).
- Exit criteria: `moviedata.py` defines `MovieData` with every field the reference needs (title,
  year, plot, imdb_rating, imdb_votes, rt_score, rt_fresh, rt_audience, rt_consensus, metascore,
  metascore_band, genres, director, runtime_min, poster_path, imdb_id, tmdb_id). The `director`
  field holds the director name(s) only; the reference's parenthetical "other films" is out of scope
  (see Non-goals), so no field carries it. The reference slide's "Review Summary" bullet is
  populated by `rt_consensus`
  (the RT critics consensus is the review summary -- one field, two would duplicate); a field
  docstring states this so the builder and any reviewer see the single owner. `metascore_band`
  (green/yellow/red per Metacritic's 61-100 / 40-60 / 0-39 bands) drives the colored-square mark.
  Pure module; `pyflakes` clean; import verified via a `_temp.py`.

### Milestone: M2 Config loader

- Depends on: none (pyyaml already installed).
- Parallel-plan ready: yes.
- Exit criteria: `config.py` loads `tmdb_key.yml` (already present and gitignored) and returns the
  v4 `read_token`, used as an `Authorization: Bearer` header. `read_token` is the single required
  credential -- the loader raises a clear error (not `sys.exit`) when it is absent, and the tool
  does not use `api_key` (kept in the file for the user's own reference only, not a code fallback).
  A committed `tmdb_key.sample.yml` documents the keys; the loader reads them from the file.

### Milestone: M3 Dependencies

- Depends on: none
- Parallel-plan ready: yes.
- Exit criteria: `pip_requirements.txt` lists `python-pptx`, `imdbinfo` (bundles `imdbinfo-aws`, the
  AWS-WAF solver), `curl_cffi`, `requests`, `pyyaml`, `lxml`, `pillow`, `imagehash` (visual gate);
  `Brewfile` adds LibreOffice. All are already installed (user confirmed); this milestone only
  declares them. `pip show` confirms importability.

### Milestone: M4 Template extract

- Depends on: D-DEPS (python-pptx, soffice).
- Parallel-plan ready: yes.
- Extraction source: the authoritative format is the `.odp` (LibreOffice is the source app). To
  guarantee the template's master/fonts/geometry match the authoritative deck, the script converts a
  chosen authoritative `.odp` deck to `.pptx` via `soffice --convert-to pptx` and then extracts that
  deck's hidden movie-slide layout + master -- rather than trusting a pre-existing `.pptx` export.
  `class02b-pre-film_content.odp` (the single-movie "Her" reference) is the candidate source; the
  script records which deck and slide it used.
- Exit criteria: `devel/extract_slide_template.py` produces `template/movie_slide_template.pptx` (no
  human step) exposing the title placeholder, the body placeholder, and a resolvable poster anchor
  at the reference geometry. Beyond placeholder discovery, the milestone proves the whole round trip
  survives: a minimal fill (title + one bullet + a small image) is written, converted to `.odp`, and
  the resulting `content.xml` is inspected to confirm the master styling, OpenDyslexic font
  references, bullet-level (L2) structure, and the title/outline/poster frame geometry all survive.
  Verified by `devel/extract_slide_template.py` self-check output + a `_temp.py` that asserts those
  survive in the round-tripped odp.

### Milestone: M5 Fixtures

- Depends on: D-PROBE, D-CONTRACT, D-TEMPLATE.
- Parallel-plan ready: no -- single fixtures tree, one owner.
- Exit criteria: `tests/fixtures/movie/` contains frozen captures for the sample movies (from M0),
  a canonical `MovieData` for "Her" built by hand from those captures, a long-text `MovieData`
  variant (deliberately long plot + consensus, to exercise autofit/overflow), a small sample poster
  png, and a golden structural descriptor of the Her slide (expected title text, ordered bullet
  lines with labels, mark glyphs, poster frame rect). This tree is the offline substrate that lets
  M6-M16 verify without a human or live network. (Fixture dir is the standing exception under
  `docs/PYTEST_STYLE.md` fixture policy; user approval of this plan is its sign-off.)

### Milestone: M6-M9 Providers (tmdb / imdb / rt / metacritic)

- Depends on: D-CONTRACT, D-PROBE, D-FIX, D-HTTP (M6 also D-CONFIG). The four are mutually
  independent.
- Parallel-plan ready: yes (4 lanes, distinct files; all share `http_client.py`, none edit it).
- Exit criteria (each): the module implements the probe-chosen parse path via `http_client.py` (so
  timeouts/headers/jitter/retry are uniform); an offline fixture-parse check under `tests/e2e/`
  (reads the captured fixture -- not a permanent pytest, per the testing policy) asserts expected
  parsed values; a `tests/e2e/e2e_<src>.py` proves live retrieval for "Her" asserting
  plausible ranges + identity (per the cross-cutting identity policy -- imdb-id anchored, confirmed
  by >=2 of title/year/director + recorded canonical URL), using the current live values. Required
  behaviors that are part of "done" (not deferred follow-ons): TMDB resolves by title+year, imdb id,
  and tmdb id and downloads the poster; IMDB formats votes as `NNNk`; RT and Metacritic resolve the
  slug with year disambiguation and return consensus / Metascore + band, or raise a clear
  source+movie+URL error, proven by a captured missing-data fixture that must trigger the abort.

### Milestone: M10 Input classifier

- Depends on: none (pure; does not import `MovieData`).
- Parallel-plan ready: yes.
- Exit criteria: `movie_input.py` classifies raw input deterministically: an `imdb.com/title/tt...`
  URL or bare `tt\d+` -> IMDB id; a `themoviedb.org/movie/...` URL or an explicit `tmdb:<n>` prefix
  -> TMDB id; everything else -> a title (with an optional trailing 4-digit year parsed off).
  A bare integer (`1917`, `1984`, `42`) is a TITLE, never a TMDB id -- TMDB ids require the URL or
  `tmdb:` prefix, so numeric titles are never misread. Pure function; covered by unit tests in M16.

### Milestone: M11 Resolver

- Depends on: D-INPUT, D-TMDB, D-FIX.
- Parallel-plan ready: yes.
- Exit criteria: `movie_resolver.py` runs a TMDB search for title inputs, prints a numbered menu on
  multiple hits, reads a selection, and returns resolved `{imdb_id, tmdb_id}`. Verified by a
  scripted-stdin debug harness driving the menu over a captured multi-hit search fixture (no human).

### Milestone: M12 Orchestration

- Depends on: D-RESOLVE, D-TMDB, D-IMDB, D-RT, D-MC, D-CONTRACT.
- Parallel-plan ready: no -- integrates all lanes.
- Exit criteria: `make_movie_slide.py` prompts, resolves, assembles `MovieData` from all providers,
  aborts loudly if a mandatory field (RT consensus, Metascore) is unresolved, and hands off to the
  builder. Verified offline by monkeypatching the providers with fixture returns (both a full-data
  case and a mandatory-missing case that must abort). Shebang + executable bit set.

### Milestone: M13 Slide builder

- Depends on: D-CONTRACT, D-TEMPLATE, D-FIX.
- Parallel-plan ready: no -- single template-fill module.
- Exit criteria: `slide_builder.py` fills the title placeholder `Title (Year)` and the body
  placeholder with the exact bullet structure (plot capped to 2-3 sentences with body autofit;
  nested IMDB and Critics lines; Genre; Director name(s); Run time; Review Summary from
  `rt_consensus`), applies the locked `emoji_marks.py` marks, and inserts the poster at the
  reference frame rect aspect-fit + centered (pillow for fit). Verified by parsing the emitted pptx
  XML against the golden structural descriptor (text lines, order, mark glyphs, poster frame rect)
  -- no human view. Locked marks (escaped unicode, ASCII source): RT fresh = red tomato
  (`\U0001F345`); RT rotten = nauseated green face (`\U0001F922`, matching the reference decks'
  rotten glyph); IMDB label mark = yellow square (`\U0001F7E8`); Metascore mark follows the band --
  green (`\U0001F7E9`) 61-100, yellow (`\U0001F7E8`) 40-60, red (`\U0001F7E5`) 0-39. These glyphs
  are part of the golden fixture and the M15 visual gate; the extract round trip (M4) confirms they
  render in odp/pdf.

### Milestone: M14 Convert + cleanup

- Depends on: D-BUILD (converts M13's built pptx -- no separate fixture pptx to own).
- Parallel-plan ready: yes (distinct module).
- Exit criteria: `slide_convert.py` runs `soffice --headless --convert-to odp` on the built pptx and
  emits `./<slug>.odp`. Before removing the scratch pptx it validates the odp is a zip whose
  `content.xml` contains the expected title text and the title/outline/poster frames; only on that
  success is the scratch pptx removed. A structurally valid-but-damaged odp (missing frames/title)
  fails the check, keeps the pptx, and reports failure -- it is never treated as the deliverable.

### Milestone: M15 Visual acceptance

- Depends on: D-CONVERT, D-FIX (golden).
- Parallel-plan ready: yes.
- Exit criteria: `tests/e2e/visual_accept.py` builds the Her slide from the canonical fixture
  `MovieData` (and the long-text variant), converts to odp, renders to png via `soffice`, and
  asserts against the golden. The primary invariant is structural: parsed odp `content.xml`
  frames/text/marks match the descriptor. A secondary perceptual check uses `imagehash` (Hamming
  distance under a tolerance) rather than a raw exact pixel diff, so the gate is stable across
  LibreOffice/font versions on the supported environment. The long-text case must render inside the
  body frame. This automated harness replaces any human "open it and check" sign-off.

### Milestone: M16 Unit tests

- Depends on: D-INPUT, D-IMDB, D-RT, D-MC (the pure helpers under test come from the classifier and
  the providers).
- Parallel-plan ready: yes.
- Ownership boundary: each provider milestone (M6-M9) owns its own offline fixture-parse check, but
  that check lives in `tests/e2e/` (it reads a captured fixture / exact external format), not in
  permanent pytest. M16 adds only the small set of genuinely stable pure-function invariants to
  permanent `tests/test_movie_helpers.py`, each with INLINE inputs and behavioral/range assertions:
  imdb-id extraction from a URL, input classification (title vs tt-id vs tmdb-id, numeric-is-title),
  ISO-8601 runtime -> minutes, fresh/rotten from a percentage (boundary at 60), metascore-band from
  a score (boundaries 40/61), and a `MovieData` behavioral property. Explicitly excluded from
  permanent pytest as too fragile: exact TMDB poster URL strings and exact RT/MC slug strings (they
  encode current site formats) -- those are exercised in `tests/e2e/` instead. Run the PYTEST_STYLE
  checklist per test; if a candidate is not stable-next-week, drop it. `pytest tests/` and `pyflakes`
  clean.

### Milestone: M17 Docs + close-out

- Depends on: D-VISUAL, D-ORCH.
- Parallel-plan ready: yes (docs lanes independent).
- Exit criteria: `docs/USAGE.md`, `docs/INSTALL.md` (TMDB key setup + LibreOffice), and a
  `README.md` first paragraph (< 250 chars, pure prose) written; `docs/CHANGELOG.md` finalized;
  About-description paragraph ready.

### Milestone: M18 Review deck

- Depends on: D-BUILD, D-CONVERT (reuses the append-capable builder + convert).
- Parallel-plan ready: yes.
- Exit criteria: `make_review_deck.py` takes a list of movies (interactive list, or the sample set),
  runs the full resolve+assemble path per movie, appends each as a slide into one presentation, and
  emits a single multi-slide `review_deck.odp`. The build + a self-check run autonomously (the check
  asserts one slide per input movie with the expected title + mandatory fields present per slide; a
  movie whose mandatory field is unresolved aborts that entry with a clear error, reported in the run
  summary rather than silently dropped). The deck is then the SOLE human-review step in the whole
  plan and the final close-out: a person skims the one file to sign off on text content (title, plot,
  ratings line, genres, director, runtime, consensus) across movies at once; poster fidelity is
  secondary. Human sign-off closes the project; it does not block any earlier milestone.

## Workstream breakdown

Each milestone is a single atomic workstream (one owner, one outcome, one verification) so lanes
dispatch in parallel by dependency wave. Owner tiers: `expert_coder` for design-sensitive scraping,
XML/template, and integration; `coder` for mechanical modules; `tester` for the pytest lane.

| Lane (milestone) | Owner | Provides (dep ID) | Verify |
| --- | --- | --- | --- |
| M0 probe | expert_coder x4 | probe report + captures (D-PROBE) | report rows filled, captures saved |
| M1 contract | expert_coder | `moviedata.py` (D-CONTRACT) | pyflakes + import |
| M2 config | coder | `config.py` + sample (D-CONFIG) | raises on missing key |
| M3 deps | coder | requirements + Brewfile (D-DEPS) | `pip show` |
| M3b http | expert_coder | `http_client.py` (D-HTTP) | `_temp.py` fetch returns 200 |
| M4 template | expert_coder | extract script + template (D-TEMPLATE) | placeholders locatable |
| M5 fixtures | expert_coder | `tests/fixtures/movie/` (D-FIX) | golden + canonical load |
| M6 tmdb | coder | `tmdb_client.py` (D-TMDB) | fixture unit + live e2e |
| M7 imdb | coder | `imdb_ratings.py` (D-IMDB) | fixture unit + live e2e |
| M8 rt | expert_coder | `rt_scraper.py` (D-RT) | fixture + missing-abort + e2e |
| M9 metacritic | expert_coder | `metacritic_scraper.py` (D-MC) | fixture + missing-abort + e2e |
| M10 input | coder | `movie_input.py` (D-INPUT) | unit tests |
| M11 resolver | coder | `movie_resolver.py` (D-RESOLVE) | scripted-stdin harness |
| M12 orchestration | expert_coder | `make_movie_slide.py` (D-ORCH) | monkeypatched full + abort |
| M13 builder | expert_coder | `slide_builder.py`, `emoji_marks.py` (D-BUILD) | pptx XML vs golden |
| M14 convert | coder | `slide_convert.py` (D-CONVERT) | odp valid, pptx removed |
| M15 visual | expert_coder | `tests/e2e/visual_accept.py` (D-VISUAL) | render diff vs golden |
| M16 unit tests | tester | `tests/test_movie_helpers.py` (D-UNIT) | `pytest tests/` green |
| M17 docs | coder | docs + changelog (D-DOCS) | markdown-link + ascii tests |
| M18 review deck | expert_coder | `make_review_deck.py` (D-DECK) | one slide/movie, fields present |

## Work packages

One atomic work package per milestone (one owner, one outcome, one verification). All verification
paths are autonomous: no "open it and look", no live-network dependency on the critical chain
(offline fixture checks gate; live e2e checks freshness off-chain).

### WP M0: Source probe & evidence

- Owner: expert_coder (4 parallel source lanes)
- Touch points: `devel/probe_sources.py`, `docs/active_plans/audits/movie_source_probe_report.md`,
  `tests/fixtures/movie/captured/`
- Depends on: none
- Acceptance criteria: for each of the 5 sample movies and each source, fetch and record which parse
  path succeeded, a success count (n/5), the JSON keys used, and any blocking; save raw responses.
- Verification commands: `source source_me.sh && python3 devel/probe_sources.py`; report has a
  filled row per source; `tests/fixtures/movie/captured/` non-empty.
- Obvious follow-ons: flag any source scoring < 5/5 as a risk row here; changelog entry.

### WP M1: MovieData contract

- Owner: expert_coder
- Touch points: `moviedata.py`
- Depends on: none
- Acceptance criteria: `MovieData` holds every reference field (see M1 exit criteria list).
- Verification commands: `pyflakes moviedata.py`; import via a `_temp.py`.
### WP M2: Config loader

- Owner: coder
- Touch points: `config.py`, `tmdb_key.sample.yml`
- Depends on: none (pyyaml installed; `tmdb_key.yml` present and gitignored)
- Acceptance criteria: `config.load()` reads `tmdb_key.yml`, returns `read_token` (Bearer; the
  single required credential, `api_key` unused by code), and raises a clear error (not `sys.exit`)
  when `read_token` is absent.
- Verification commands: `_temp.py` loads the real `tmdb_key.yml` (token present) and a copy with
  `read_token` removed (confirms the clear error).
- Obvious follow-ons: `tmdb_key.sample.yml`; changelog entry.

### WP M3: Dependencies

- Owner: coder
- Touch points: `pip_requirements.txt`, `Brewfile`
- Depends on: none
- Acceptance criteria: all imports declared; Brewfile adds LibreOffice.
- Verification commands: `pip show python-pptx imdbinfo curl_cffi pillow`.
### WP M4: Template extract

- Owner: expert_coder
- Touch points: `devel/extract_slide_template.py`, `template/movie_slide_template.pptx`
- Depends on: D-DEPS
- Acceptance criteria: script converts an authoritative `.odp` deck
  (`class02b-pre-film_content.odp` candidate) to pptx via `soffice` and extracts its hidden
  movie-slide layout + master; then proves the full round trip -- a minimal fill (title + one bullet
  + small image) is written, converted back to `.odp`, and `content.xml` inspected to confirm master
  styling, OpenDyslexic font refs, L2 bullet structure, and title/outline/poster geometry all
  survive. Records which deck/slide was used.
- Verification commands: `source source_me.sh && python3 devel/extract_slide_template.py` (self-check
  asserts the round-tripped odp retains styling/fonts/geometry).
- Obvious follow-ons: document extraction in `docs/INSTALL.md`.

### WP M5: Fixtures

- Owner: expert_coder
- Touch points: `tests/fixtures/movie/` (captures, `her_moviedata.json`, `sample_poster.png`,
  `her_golden_structure.json`)
- Depends on: D-PROBE, D-CONTRACT, D-TEMPLATE
- Acceptance criteria: canonical Her `MovieData` loads and matches the contract; golden descriptor
  enumerates expected title, ordered bullet lines, mark glyphs, and poster rect.
- Verification commands: `_temp.py` loads canonical `MovieData` + golden; asserts field presence.
### WP M3b: Shared HTTP helper

- Owner: expert_coder
- Touch points: `http_client.py`
- Depends on: D-DEPS
- Acceptance criteria: one `get()` wrapping curl_cffi `impersonate=chrome` with common headers,
  jittered `time.sleep(random.random())`, a fixed timeout, and one bounded 403/429 retry.
- Verification commands: `_temp.py` fetches a known page and returns 200.

### WP M6-M9: Providers (one WP each)

- Owner: coder (M6 tmdb, M7 imdb), expert_coder (M8 rt, M9 metacritic)
- Touch points: `tmdb_client.py` / `imdb_ratings.py` / `rt_scraper.py` / `metacritic_scraper.py`;
  matching `tests/e2e/e2e_<src>.py`; an offline fixture-parse check under `tests/e2e/` (not a
  permanent pytest).
- Depends on: D-CONTRACT, D-PROBE, D-FIX, D-HTTP (M6 also D-CONFIG)
- Acceptance criteria (part of "done", not deferred): implements the probe-chosen path via
  `http_client.py`; offline fixture-parse check asserts expected values; live e2e asserts plausible
  ranges
  + imdb-id-anchored identity. TMDB resolves 3 ways + downloads poster; IMDB formats votes `NNNk`;
  RT/MC do year-disambiguated slug resolution and return the mandatory field (+ RT fresh/rotten, MC
  band) or raise a clear source+movie+URL error, proven by a captured missing-data fixture that must
  abort.
- Verification commands: offline unit test; `source source_me.sh && python3 tests/e2e/e2e_<src>.py`.

### WP M10: Input classifier

- Owner: coder
- Touch points: `movie_input.py`
- Depends on: none (pure; does not import `MovieData`)
- Acceptance criteria: classifies imdb id/URL, tmdb URL/`tmdb:` prefix, and title(+year); a bare
  integer is a title, never a tmdb id.
- Verification commands: unit tests (M16).

### WP M11: Resolver

- Owner: coder
- Touch points: `movie_resolver.py`, `tests/e2e/e2e_resolver_menu.py`
- Depends on: D-INPUT, D-TMDB, D-FIX
- Acceptance criteria: TMDB search + numbered menu returns resolved ids; ambiguous case resolved via
  scripted stdin over a captured multi-hit fixture (no human).
- Verification commands: `source source_me.sh && python3 tests/e2e/e2e_resolver_menu.py`.
### WP M12: Orchestration

- Owner: expert_coder
- Touch points: `make_movie_slide.py`, `tests/e2e/e2e_orchestrate_her.py`
- Depends on: D-RESOLVE, D-TMDB, D-IMDB, D-RT, D-MC, D-CONTRACT
- Acceptance criteria: assembles `MovieData` from all providers; aborts loudly on a missing
  mandatory field. Verified offline by monkeypatching providers with a full-data fixture and a
  mandatory-missing fixture (must abort).
- Verification commands: `source source_me.sh && python3 tests/e2e/e2e_orchestrate_her.py`.
- Obvious follow-ons: shebang + executable bit; changelog entry.

### WP M13: Slide builder

- Owner: expert_coder
- Touch points: `slide_builder.py`, `emoji_marks.py`
- Depends on: D-CONTRACT, D-TEMPLATE, D-FIX
- Acceptance criteria: exposes an append-a-slide function (takes a presentation + `MovieData`) so
  single and batch runs share it; from the canonical `MovieData`, fills title + bullet structure +
  marks and places the poster (aspect-fit, centered) at the reference rect; emitted pptx XML matches
  the golden descriptor. Marks are escaped unicode (ASCII source).
- Verification commands: `source source_me.sh && python3 tests/e2e/e2e_build_her.py` (XML asserts).
### WP M14: Convert + cleanup

- Owner: coder
- Touch points: `slide_convert.py`
- Depends on: D-BUILD (converts M13's built pptx)
- Acceptance criteria: converts the built pptx to `./<slug>.odp`; validates the odp `content.xml`
  contains the title + title/outline/poster frames before removing the scratch pptx; on a damaged
  odp, keeps the pptx and reports failure (odp is the only success artifact).
- Verification commands: `source source_me.sh && python3 tests/e2e/e2e_build_her.py` (build ->
  convert -> asserts odp valid + pptx gone).

### WP M15: Visual acceptance

- Owner: expert_coder
- Touch points: `tests/e2e/visual_accept.py`
- Depends on: D-CONVERT, D-FIX
- Acceptance criteria: builds Her (and the long-text variant) from fixtures -> odp -> png; the hard
  gate is that odp `content.xml` frames/text/marks match the golden; a perceptual `imagehash`
  comparison under tolerance is an advisory secondary check. Long-text case renders inside the body
  frame.
- Verification commands: `source source_me.sh && python3 tests/e2e/visual_accept.py`.
- Obvious follow-ons: store golden pdf/png under `tests/fixtures/movie/`; changelog entry.

### WP M16: Unit tests

- Owner: tester
- Touch points: `tests/test_movie_helpers.py`
- Depends on: D-INPUT, D-IMDB, D-RT, D-MC
- Acceptance criteria: the enumerated stable pure invariants (imdb-id extraction, input
  classification, ISO-8601 runtime -> minutes, fresh/rotten at the 60 boundary, metascore-band at
  the 40/61 boundaries, `MovieData` behavioral property) covered with inline inputs per
  `docs/PYTEST_STYLE.md`.
- Verification commands: `pytest tests/`; `pytest tests/test_pyflakes_code_lint.py`.
### WP M17: Docs + close-out

- Owner: coder
- Touch points: `docs/USAGE.md`, `docs/INSTALL.md`, `README.md`, `docs/CHANGELOG.md`
- Depends on: D-VISUAL, D-ORCH
- Acceptance criteria: usage/install (TMDB key + LibreOffice) written; README first paragraph
  < 250 chars pure prose; changelog finalized.
- Verification commands: `pytest tests/test_markdown_links.py tests/test_ascii_compliance.py`.
- Obvious follow-ons: About-description paragraph; rotate changelog if needed.

### WP M18: Review deck

- Owner: expert_coder
- Touch points: `make_review_deck.py`, `tests/e2e/e2e_review_deck.py`
- Depends on: D-BUILD, D-CONVERT
- Acceptance criteria: builds a multi-slide `review_deck.odp` from a movie list (sample set default),
  one slide per movie via the append-capable builder; self-check asserts slide count == movie count
  and each slide has the expected title + mandatory fields; unresolved-mandatory entries abort with a
  clear per-movie error in the summary. This deck is the single, final human-review artifact.
- Verification commands: `source source_me.sh && python3 tests/e2e/e2e_review_deck.py`.

## Acceptance criteria and gates

- Per-patch gate: `pyflakes <changed.py>` clean; `pytest tests/` green; new imports added to
  `pip_requirements.txt`; source is tab-indented and ASCII-only per `docs/PYTHON_STYLE.md`.
- Integration gate: `make_movie_slide.py` run on "Her (2013)" produces an `.odp` whose structure,
  labels, and styling match the reference slide and whose data comes from live sources at generation
  time: title `Her (2013)`, a plot line, IMDB rating+votes present and plausible, RT tomatometer
  with correct fresh/rotten mark, a non-empty RT consensus sentence, all genres, director, runtime,
  and a present Metascore, with the poster centered in the frame. Values are checked for
  plausibility and source identity, not against the reference's historical numbers. If RT consensus
  or Metascore cannot be resolved, the run aborts with a clear error and emits no slide.
- Autonomous acceptance gate (replaces any human sign-off): `tests/e2e/visual_accept.py` builds Her
  from the canonical fixture, converts to odp, renders to png, and asserts the parsed `content.xml`
  structure (primary invariant) plus a perceptual `imagehash` comparison under tolerance (not a raw
  pixel diff) against the golden. No human step is on the critical path; a human may optionally
  spot-check but the plan completes without one.

## Test and verification strategy

- Pure-function pytest (fast, offline, `tests/test_*.py`) -- deliberately minimal, inline inputs,
  behavioral/range assertions only: imdb-id extraction, input classification, ISO-8601 duration ->
  minutes, fresh/rotten from percentage (60 boundary), metascore-band (40/61 boundaries), and a
  `MovieData` behavioral property. Exact TMDB poster URLs and RT/MC slug strings are NOT permanent
  tests (they encode current site formats -> fragile); they are exercised in `tests/e2e/`. No
  collection-length, required-key, or hardcoded-default assertions, per `docs/PYTEST_STYLE.md`.
- E2E (network/LibreOffice, `tests/e2e/e2e_*.py`, excluded from pytest): each provider's live
  retrieval for "Her"; full build-to-odp for "Her". Assertions check plausible ranges (rating
  0-10, tomatometer/metascore 0-100, votes > 0), source identity (resolved title/year matches the
  request), and mandatory-field presence -- using current live values (which drift as sources
  update). Self-contained, non-zero exit on failure.
- Autonomous integration (`tests/e2e/visual_accept.py`): fixture-driven build -> odp -> render ->
  structural XML match (primary) + perceptual `imagehash` comparison under tolerance (secondary,
  not a raw pixel diff) vs golden. This is the acceptance gate; no human view required.
- Evidence first (scientific method): the M0 probe measures each source's parse-path success on the
  5-movie sample before providers lock their design, and the report row is the go/no-go for each
  provider milestone -- methods are chosen from data, not assumed.

## Migration and compatibility policy

- Additive rollout: new modules only; no existing repo behavior to preserve.
- Backward compatibility: none required (greenfield).
- Legacy deletion criteria: none; old `junk-drawer/movielib.py` is reference only, not imported.
- Rollback strategy: revert the feature patches; the repo returns to the empty template.

## Risk register

| Risk | Impact | Trigger | Owner | Mitigation |
| --- | --- | --- | --- | --- |
| RT/Metacritic markup churn breaks scraping | High (required fields) | e2e parse returns empty | expert_coder | Pin to `ld+json`/`media-scorecard-json` JSON blobs, not DOM selectors; on failure raise a clear source+movie+URL error and abort (no silent/manual substitution) -- the error message is diagnostic guidance for a human to fix later, not a fallback that emits a slide |
| IMDb WAF blocks `imdbinfo` | Medium | rating lookup empty/blocked | coder | `curl_cffi`+JSON-LD fallback; throttle; single-lookup use |
| TMDB key handling | Medium | missing/committed key | expert_coder | gitignored config + sample; loader raises clearly; never env-var per style |
| No text highlight in python-pptx | Low | reference highlights absent | expert_coder | Use colored emoji squares (yellow before IMDB, green by Metascore) as escaped unicode -- survives odp convert, no oxml hack |
| LibreOffice convert fails | Low (soffice present: LibreOffice 26.2.4.2 at /opt/homebrew/bin) | convert errors or produces a damaged odp | coder | Validate the odp's `content.xml` (title + frames) before deleting the scratch pptx; on failure keep the pptx for diagnosis, report failure, and do NOT treat the pptx as the deliverable (the `.odp` is the only success artifact) |
| Cloudflare/rate-limit on bulk runs | Low | 403/429 | expert_coder | `impersonate=chrome`, jittered `time.sleep`, single-movie scope |
| A source's parse path fails on the sample | High (blocks a provider) | M0 probe row shows a genuine resolution/parse failure | expert_coder | Probe runs first; the failing row triggers a documented alternate parse path (an additional JSON blob or endpoint identified in the same probe) that the provider implements before it locks -- design follows evidence |
| Hidden human dependency stalls autonomous run | Medium | a milestone waits on a person | manager | Every gate is fixture/harness-driven; live sources + LibreOffice driven by subagents; live e2e is off the critical chain |
| TMDB key absent in the run environment | Medium | `config.load()` raises | manager | Providers/builder verify against captured fixtures offline, so M5-M16 complete without a live key; live TMDB e2e is off-chain |

## Rollout and release checklist

- [ ] M0 probe report filled; every source row has a measured success count and captured fixture.
- [ ] Contract, config, deps, template, fixtures merged; template opens in python-pptx.
- [ ] Four providers pass offline fixture tests + live e2e; RT/MC missing-data fixtures abort.
- [ ] Resolver menu resolves via the scripted-stdin harness; orchestration assembles + aborts.
- [ ] Builder output matches the golden structural descriptor; convert emits `.odp`, removes pptx.
- [ ] `tests/e2e/visual_accept.py` passes (automated visual sign-off).
- [ ] `pytest tests/` and pyflakes clean; permanent tests limited to stable inline pure invariants.
- [ ] Docs (USAGE, INSTALL, README first paragraph) + changelog done.
- [ ] `review_deck.odp` built + self-checked (one slide per movie, fields present).
- [ ] Human close-out: skim `review_deck.odp` and sign off on text content (the only human step).

## Documentation close-out requirements

- Active plan / progress tracker: this plan; update as milestones close.
- docs/CHANGELOG.md entry: one entry per merged work package under the current date, following the
  repo's category subsection order.
- Archive / closure notes: on completion, `git mv` this plan to `docs/archive/` per REPO_STYLE.

## Patch plan and reporting format

One patch per milestone, dispatched by dependency wave. Report progress as "Patch M<n>". This
mirrors the wave schedule under Milestone plan exactly.

- Wave 1 (parallel): M0 probe, M1 contract, M2 config, M3 deps, M10 input classifier.
- Wave 1b: M3b `http_client.py` (after D-DEPS).
- Wave 2a: M4 template. Wave 2b: M5 fixtures (after M4 -- M5 needs D-TEMPLATE, not parallel with M4).
- Wave 3 (parallel): M6 tmdb, M7 imdb, M8 rt, M9 metacritic.
- Wave 4a (parallel): M11 resolver, M13 builder. Wave 4b: M14 convert (needs D-BUILD), M12
  orchestration.
- Wave 5: M15 visual acceptance, M16 unit tests, M17 docs.
- Wave 6: M18 review deck (final; sole human-review close-out).

## Decisions locked

- Metadata (plot, genres, runtime, director, poster) from TMDB (single keyed source). Ratings from
  IMDB; RT/Metacritic scores scraped. TMDB genres are broad (comparable to RT's), which is the
  desired granularity -- IMDB's newer genres are too specific.
- TMDB auth uses the v4 `read_token` (Bearer header) from the gitignored `tmdb_key.yml`; it is the
  single required credential and covers every read endpoint used. `api_key` is not used by the code.
- Final deliverable is `./<slug>.odp` in the current directory; the `.pptx` is a scratch
  intermediate removed after convert.
- No text highlight (python-pptx limitation): use colored emoji squares -- a yellow square before
  the IMDB label and a green square by the Metascore -- as escaped unicode.

## Open questions and decisions needed

- None outstanding. All prior open items (marker glyphs, TMDB auth, metadata source, output path,
  highlighting) are resolved and recorded under "Decisions locked" and the milestone bodies.

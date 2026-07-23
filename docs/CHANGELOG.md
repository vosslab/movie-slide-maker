# Changelog

## 2026-07-23

### Additions and New Features

- Added the optional Rotten Tomatoes Popcornmeter to the provider contract and slide, with popcorn
  for scores of at least 60, popcorn with a thumbs-down below 60, and `N/A` when no audience score
  is published.
- Added tiered Tomatometer marks: a green sick mark below 60, a tomato from 60 through 80, and a
  tomato with a trophy above 80.
- Added a yellow IMDb score highlight and compact vote-count formatting such as `435k`, `2.3k`, and
  `1.2M`.

### Fixes and Maintenance

- Normalized the runtime template and every built presentation to exactly 28 by 17.5 cm, eliminating
  the 28.002 by 17.502 cm ODP round-trip drift that prompted LibreOffice to scale copied slides.
- Strengthened converted-page validation to require the exact lecture page dimensions.
- Launched headless LibreOffice through macOS LaunchServices instead of directly registering its
  application binary, preventing intermittent AppKit aborts and intrusive crash dialogs.
- Split critics and Popcornmeter values across readable secondary bullets and refreshed the tracked
  Her slide screenshot from the current validated output.

## 2026-07-21

### Additions and New Features

- Added the shared `MovieData` contract with pre-build validation, escaped rating marks, and
  shared Rotten Tomatoes and Metascore boundary helpers.
- Added required-key loading for the TMDB v4 `read_token` and a safe single-key sample
  configuration.
- Declared the five direct Python runtime dependencies used by the movie slide generator.
- Added a shared browser-like HTTP client with common headers, polite randomized delays, a fixed
  timeout, and one retry for HTTP 403 or 429 responses.
- Added movie input classification for IMDb and TMDB identifiers and URLs, bare and
  parenthesized-year titles, while preserving numeric title suffixes.
- Extracted the hidden movie layout from the authoritative lecture deck into a one-slide
  PowerPoint template with recorded title, outline, poster, page, font, and autofit anchors.
- Added a shared-client live source probe covering five representative movies across TMDB, IMDb,
  Rotten Tomatoes, and Metacritic, with secret-safe generated captures and an audit report.
- Validated movie input classification, score boundaries, and mandatory shared movie-data behavior
  with disposable offline smoke coverage rather than a new permanent product pytest file.
- Added the template-based movie slide builder and a direct Her E2E that verifies product labels,
  bullet hierarchy, OpenDyslexic autofit text, and aspect-preserving poster placement.
- Added the TMDB provider client and a direct live E2E covering title search, IMDb cross-mapping,
  movie details, credits, and temporary poster download through the shared HTTP policy.
- Added an identity-bearing IMDb rating client with a shared-HTTP `imdbinfo` path, a JSON-LD
  fallback, and a direct current-movie E2E covering required values and plausible ranges.
- Added an identity-checked Rotten Tomatoes client for Tomatometer state and mandatory critics
  consensus, with a direct current-movie E2E through the shared HTTP policy.
- Added an identity-checked Metacritic client for the mandatory Metascore and shared score band,
  with a direct current-movie E2E through the shared HTTP policy.
- Added LibreOffice Still conversion with semantic ODP validation, tolerant role geometry checks,
  nonempty poster verification, and accepted-scratch cleanup in a direct conversion E2E.
- Moved runtime implementation into the `slide_maker/` package with absolute package-qualified
  imports, a docstring-only package initializer, and a restored root-local TMDB credential path.
- Documented the trusted local XML package boundary for template extraction and LibreOffice output
  parsing so the repository security gate distinguishes those inputs from untrusted XML.
- Defined `make_movie_slide.py` as the sole final root Python entry stub and kept batch execution
  package-based; retained `devel/` scripts as maintainer-only extraction and source-probe tools.
- Classified ignored `SLIDE_ARTIFACTS/` as local planning and comparison material rather than a
  permanent repository artifact or runtime dependency.
- Created an evidence-backed README landing page with honest active-development status, a verified
  classifier quick start, the implemented slide/conversion proof path, provider contracts,
  limitations, documentation routes, and a managed screenshot placeholder.
- Completed the root CLI pipeline from supported movie input through four live providers, template
  fill, LibreOffice conversion, semantic validation, and `./<slug>.odp` output.
- Added the noninteractive `slide_maker.review_deck` batch entry with five built-in movies,
  source-specific failure accounting, a validated review deck, and retained page renders.
- Added installation and usage guides covering Python 3.12, system dependencies, OpenDyslexic,
  TMDB token setup, single-movie generation, batch review, outputs, and failure behavior.

### Fixes and Maintenance

- Completed the IMDb redirect-identity diagnostic so it reports both the attempted URL and the
  final redirected URL.
- Updated the README from implementation status to the verified single-movie and review-deck
  workflows, with current generated acceptance-evidence paths.
- Added the Rotten Tomatoes joined-hyphen slug needed to resolve Spider-Man titles reliably.
- Preserved numeric movie titles while recognizing a trailing release year in title input.
- Established `slide_maker.review_deck` as the permanent package-based batch entry and removed the
  temporary root-script naming from current documentation.
- Made batch publication staged and strict: top-level slide validation, source-failure propagation,
  and configuration faults complete before the final deck replaces its destination.
- Repaired title and outline sizing so LibreOffice renders complete text without clipped labels.
- Added the tracked Her slide screenshot used by the README.
- Completed fresh independent acceptance and archived the finished plan at
  `docs/archive/movie_slide_generator_plan.md`.
- Completed a six-pass code audit and repaired visual title-containment evidence, consolidated
  accented-title identity normalization, removed dead conversion and staging paths, relaxed the
  unused TMDB `original_title` contract, and expanded public API docstrings.
- Added side-effect-free maintainer-tool help, corrected failure-artifact documentation, ignored
  root CLI ODP products, centralized the sourced repo import path, and removed redundant E2E path
  bootstraps and stale milestone diagnostics.
- Removed the orphaned provider milestone status report after the completed plan was archived; the
  archived plan and live E2E scripts remain the durable provider acceptance record.
- Accepted slash-delimited release years while preserving numeric and punctuated movie titles.
- Made the exact IMDb id the cross-provider identity anchor instead of fragile title and release-year
  label equality; presentation titles and years continue to use TMDB's English-language data.

### Decisions and Failures

- Moved the completed movie-slide generator plan to
  `docs/archive/movie_slide_generator_plan.md` and aligned it with repository rules:
  permanent pytest remains the repository hygiene lane, disposable smoke scripts cover pure product
  behavior during implementation, live providers and LibreOffice use direct E2E scripts, generated
  inputs use temporary directories, and ODP acceptance uses semantic checks with realistic geometry
  tolerances plus retained render evidence and independent review.
- Refined the movie-slide implementation plan around inline E2E inputs, runtime temporary images,
  reproducibly generated uncommitted captures, and the production deck as the visual reference.
  Assigned one owner to the integrated source probe; made M3 own only `pip_requirements.txt` while
  treating `cask "libreoffice-still"` as prevalidated; added milestone-owned E2E harnesses, a
  sourced M10 check, one-patch accounting, independent review, and corrected dependency subwaves.
  Made M0 depend on production configuration and the shared HTTP policy, assigned
  `slide_maker/emoji_marks.py` and score-boundary semantics to M1's `D-CONTRACT`, and replaced inline
  Python verification with sourced file- and module-based checks.
  Scheduled M18 to release the implemented review deck before the final M17 documentation and
  closeout wave, made M17 consume `D-DECK`, and standardized implementation-only smoke scripts on
  underscore-prefixed names, `tempfile.TemporaryDirectory()` file-shaped inputs, and verified
  handoff cleanup.
- Replaced the planned M16 permanent product pytest with M5 package migration and disposable pure
  behavior smoke checks after the runtime files moved under `slide_maker/`.
- Replaced interactive visual and closeout dependencies with a lean autonomous path: scripted
  resolver input, one injected orchestration success/abort harness, retained normal/long-text and
  batch-page renders, semantic self-checks, and one integrated independent subagent review. Kept the
  broad fixture matrix, perceptual hashing, and permanent product pytest retired.

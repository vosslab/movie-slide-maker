# Changelog

## 2026-10-16

### Behavior or Interface Changes

- Prefer separate rating rows when the whole outline fits with at most 15% font shrinking;
  compact crowded slides with RT critics and audience paired before combining other ratings.
  Replace Sinners with Parasite in the example deck and README to demonstrate non-English metadata.
- Convert the four README screenshots to WebP at quality 90 and update their links and
  reproducible conversion instructions; retain the compact grid and full image dimensions.
- Pack independent rating items into compact rows using measured text width and the whole
  outline's content budget. Keep each rating together and preserve the IMDb score highlight.
- Require a poster in single-movie and batch retrieval. Try alternate TMDB posters if the
  primary is absent or fails; stop that movie if no usable poster is retrieved. Remove the
  old title-only fallback after failed or mismatched TMDB retrieval.
- Present four README examples in a compact 2 by 2 grid; 400-pixel previews link to full-size PNGs.
- Omit the original-language line for English movies and make generated movie titles bold.
- Refocus README onboarding on movie summary slides for non-coders, including film clubs,
  presentations, classrooms, and movie nights; move recent verification out of the opening.
- Build movie slides from available information without a metadata-completeness threshold.
  Preserve independent ratings, vote counts, reviews, and descriptive fields; report source
  omissions while retaining the requested or selected movie.
- Display exactly one original language using its English name, without inferring subtitles.
- Replace OpenDyslexic with Atkinson Hyperlegible Next in generated text, the runtime template,
  and template extraction output. Omit absent rows and use the poster area for text when needed.
- Validate converted ODP content against the actual included source text and roles, supporting
  title-only and poster-free slides while detecting conversion loss.

### Fixes and Maintenance

- Preserve selected movie identity when enrichment fails, reject mismatched returned TMDB ids,
  and count only present identity attributes when matching scraped provider pages.
- Document the design in HUMAN_GUIDANCE.md and refresh installation, usage, and the Her screenshot.

### Developer Tests and Notes

- Rebuilt the five live examples with the repository review-deck script and inspected all four
  refreshed WebP previews. Her uses two rating rows with RT critics and audience together;
  Cooties, Parasite, and A Ghost Waits keep separate ratings. Parasite shows Korean. Normal
  and long-text LibreOffice visual acceptance passed; the full pytest suite passed 758 checks.
  Focused layout checks cover separate rows, RT-only pairing, and further compaction.
- Verified all four WebP files decode at the original dimensions and all eight README image
  references resolve. Total screenshot size fell from 2,615,719 to 653,324 bytes (75% smaller).
  Inspected the converted Her slide; 21 Markdown-link checks and `git diff --check` passed.
- Rating-layout checks cover complete-item wrapping and the effect of prose on row choices.
  Poster checks recover absent/broken primary artwork and stop publication on exhausted artwork.
  The full suite passed 721 tests. The existing normal and long-text LibreOffice visual-acceptance
  script passed; dense prose uses two compact rating rows while the shorter example uses three
  rows at the larger font size.
- Rebuilt all five live examples with the existing review-deck module, then inspected and copied
  Her, Cooties, Sinners, and A Ghost Waits into the README grid. All four are 1654 by 1034 pixels,
  below 1 MB, and linked at full resolution; every preview and image link resolves locally.
  No managed screenshot is unreferenced. Capture commands remain in [DEVEL_README.md](../devel/DEVEL_README.md).
- Final full pytest run passed 753 checks, including the newly discovered source and test files.
- Follow-up validation: 715 pytest checks passed, plus 197 documentation checks after the
  audience rewrite. Seven adaptive cases passed source inspection and LibreOffice conversion;
  converted ODP text omits English while retaining Korean and Spanish, and titles retain bold.
- Rebuilt the five-movie live review deck and visually checked the Her and A Ghost Waits pages.
  Refreshed both README screenshots and alt text for bold titles and omitted English language
  lines; both PNGs remain 1654 by 1034 pixels and below 1 MB.
- Verified the documented single-movie CLI with `tmdb:152601`; it produced `her_2013.odp`.
  The final README opening and local-link checks passed all 27 checks.
- Full pytest suite passed: 689 tests. Added focused protection for original-language selection,
  independent IMDb values, and mismatched TMDB detail responses.
- Provider and pipeline correction checks passed with deterministic injected responses.
- Built, converted, and visually inspected seven complete/sparse cases, including no poster,
  title-only, non-English language, zero scores, missing votes, and long text. PDF inspection
  confirmed embedded Atkinson Hyperlegible Next.
- Injected single-movie and two-page batch checks passed through LibreOffice. Normal and long-text
  visual acceptance passed. Fresh ODP/PNG examples are under output_smoke/.
- LibreOffice checks needed execution outside the sandbox for macOS LaunchServices.
- After the TMDB credential became available, live single-movie orchestration passed for Her.
  The default live batch passed with five accepted movies and zero rejected movies; all five
  rendered pages were visually inspected. A Ghost Waits retained its available ratings while
  omitting its absent Metascore and review summary.
- Refreshed README onboarding and navigation with readme-docs, then replaced the illustrative
  image with current live Her and A Ghost Waits renders using screenshot-docs. Both managed PNGs
  are 1654 by 1034 pixels and below 1 MB; no stale or unreferenced managed assets remain.
  The capture backend is the existing LibreOffice/Poppler batch renderer. Recapture commands
  are in [DEVEL_README.md](../devel/DEVEL_README.md).
- README rubric review: 78/100 before, 99/100 after. Purpose 11->15 (teaching outcomes);
  identity 11->15 (adaptive slides); proof 15->20 (live full and partial examples);
  first success 11->15 (explicit movie id); orientation 10->10 (inputs and providers);
  navigation 8->10 (setup first); adoption 4->4 (license attribution gap);
  presentation 8->10 (current accessible screenshots). Strongest gain: live visual proof.
- README quick-start CLI and batch CLI both passed live. Documentation checks passed 111 tests;
  the Git-tracked-only link check flags the new, unstaged A Ghost Waits PNG. Direct working-tree
  link validation passed for all three edited documents, and managed-block idempotence passed.
  The tracked-link gate remains pending inclusion of the new screenshot in Git; nothing was staged.
- Remaining documentation follow-up: the maintainer should replace the existing Author Name
  placeholder in [LICENSE.MIT.md](../LICENSE.MIT.md) with the confirmed copyright holder.
  Verify the attribution with the owner; the README's MIT license label matches the license text.

## 2026-10-15

### Fixes and Maintenance

- Fixed exact-title selection in review batches to accept resolver menu lines with plot
  excerpts, allowing ambiguous searches such as Vesper (2022) to resolve automatically.
- Made the Rotten Tomatoes critics consensus optional across fetching, validation, and
  rendering. Slides omit the Review Summary bullet when no consensus is published.
- Read Rotten Tomatoes directors from Movie JSON-LD instead of optional streaming metadata.
  Missing release dates remain unknown; title and director must then both match the movie.
- Allowed explicitly assembled movie data to omit an unavailable Metascore and its display.
  Used this for the user-approved White Plastic Sky slide; live automatic fetching still reports
  Metacritic failures instead of silently suppressing them.

### Developer Tests and Notes

- Verified batch menu selection with and without overview excerpts. Targeted lint, typing,
  and Markdown-link checks passed (132 tests).
- Ran LibreOffice conversion outside the sandbox because sandboxed LaunchServices could not
  find the installed application.
- Generated all six requested movies in `output_movies/2026-10-15/recent_movies.odp`, verified
  the approved omissions in the ODP, and visually checked all six rendered pages.

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

- Added compact TMDB overview excerpts to ambiguous title menus so same-title, same-year
  candidates can be distinguished before selection.
- Resolved Metacritic pages from the validated IMDb title as well as the TMDB title, fixing movies
  such as Dune (2021) whose Metacritic canonical title and slug include `Part One`.
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

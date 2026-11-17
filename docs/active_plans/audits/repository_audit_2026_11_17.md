# Repository audit and test pruning

## Findings requiring follow-up

- **High: optional IMDb failures abort movie generation.**
  `slide_maker/parental_guidance.py:102` calls the IMDb fetcher, which can raise
  `ImdbSourceError`. The optional guidance branch in `movie_pipeline.py` catches only
  `ParentalGuidanceSourceError`. Translate the error at the guidance provider boundary so
  other movie information and the explicit unavailable-guidance notice remain usable.
- **High: CSM identity checks accept an IMDb ID prefix.**
  `slide_maker/parental_guidance.py:182` uses substring membership on `sameAs`.
  For example, `tt1234567` matches `tt12345678`, allowing another film's guidance.
  Extract the linked title ID and compare exact normalized IDs.
- **Medium: malformed CSM structured data escapes optional-source handling.**
  `slide_maker/parental_guidance.py:161` calls `.get()` on decoded JSON without checking
  its root type. Valid array/scalar JSON raises an uncaught exception. Validate the
  source shape and report `ParentalGuidanceSourceError` when it is unsupported.
- **Medium: unknown spoiler status is accepted as non-spoiler.**
  `slide_maker/parental_guidance.py:130` accepts entries whose `isSpoiler` field is absent.
  The agreed behavior requires explicitly non-spoiler entries. Require `isSpoiler is False`.
- **Low: the summary builder depends on guidance rendering for a generic text box.**
  `slide_maker/slide_builder.py:314` imports guidance rendering just to construct its footer.
  Consider local footer construction if this coupling causes maintenance problems; no helper
  framework or cross-file refactor was added during this audit.
- **Low: temporary artifacts are tracked.**
  The checkout includes tracked `_temp/` render/profile artifacts. The existing ignore pattern
  does not cover that directory. Review those artifacts before committing; this audit
  did not alter the index or delete unrelated working material.

The functional findings remain findings: the audit authorizes obvious low-risk fixes, while
test pruning was separately authorized. No new permanent tests were added.

## Independent passes

All six fresh reviewers completed: Plan, Test, Style, Docs, Legacy, and Comment.
Plan and Style independently identified the optional-source and identity defects. They
disagreed on severity; this report prioritizes wrong-film guidance as high and unsupported
source shape as medium. Test reviewed every repository-owned executable test module.

Legacy found no actionable dead code in repository-owned production files. Its compatibility
shim observation concerned vendored Graphify utilities and was excluded from local changes.
Comment found one stale subprocess docstring, corrected locally.

## Low-risk corrections

- Describe the direct soffice subprocess and multi-slide movie section accurately.
- Describe Python 3.12 as a requirement rather than claiming the shell pins it.
- Remove obsolete milestone labels from user-facing output documentation.
- Correct the test README's bootstrap command and per-test timing guidance.

The all-E2E command in vendored `docs/E2E_TESTS.md` refers to a missing optional runner.
That upstream documentation issue remains; no runner was added just to preserve duplicate tests.

## Test-pruning boundary

Eligible starting inventory: four repository-owned pytest modules and twelve E2E scripts,
2,905 lines total. Vendored hygiene tests and shared support were excluded before evaluation.
The baseline full suite passed 1,235 checks in 2.52 seconds.

Retain identity checks, optional metadata preservation, poster recovery, whole-item rating
packing, real provider integrations, sparse/adaptive rendering, native guidance conversion,
batch accounting, and real LibreOffice visual acceptance. These protect distinct user-visible
behavior rather than merely proving the current implementation.

Prune duplicate build/conversion scripts, the mock-heavy resolver runner, injected orchestration
machinery, fixed seven-page guidance expectations, and redundant exact rating arrangements.
The known protection loss is direct scripted verification of resolver menus and particular
internal call sequences. The user-facing resolution behavior remains implemented; no speculative
replacement test was introduced.

## Verification

The eligible suite is now four pytest modules and nine E2E scripts, 1,970 lines total:
21 lines added and 956 deleted, a net reduction of 935 lines. This removes three independent
runner/fixture maintenance surfaces and the injected orchestration harness. No development
dependency or shared support file became unused; retained consumers still need them.

- Final full suite: 1,198 passed in 2.51 seconds (including vendored hygiene checks).
- Focused retained behavior checks: 14 passed.
- Retained guidance E2E: passed using headless LibreOffice outside the sandbox.
- `git diff --check`: clean; no bytecode cache directories remain.
- Deleted-script references survive only in historical archived plans, preserved as history.

This audit did not revalidate every live provider or rerun the entire multi-movie live review deck.

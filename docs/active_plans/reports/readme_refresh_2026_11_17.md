# Visual README refresh

## Reader journey

Lead with editable movie decks, show the summary and guidance pages, then show four other
films before the quick start. Preserve the existing compact, full-detail-on-click gallery
convention. Use actual slide output rather than promotional mockups or animation: detailed
text and ratings need time to read.

The two highest-value improvements are current visual proof of the parental-guidance workflow
and a verified direct-ID first-success path. Provider limitations remain explicit before the
onboarding command. Detailed usage and setup stay in their existing documentation.

## Editorial score

| Category | Before | After | Evidence |
| --- | ---: | ---: | --- |
| Purpose, audience, value | 15 | 15 | Plain opening names editable decks and screening audiences |
| Project identity | 11 | 11 | Teaching-template page size, native tables, and provider guidance |
| Proof | 15 | 20 | Current summary, age overview, category ratings, and IMDb guidance |
| First success | 11 | 15 | Canonical interactive CLI generated Jurassic Park from tt0107290 |
| Usage orientation | 8 | 10 | Inputs, expected ODP, continuation pages, and batch behavior |
| Documentation navigation | 10 | 10 | Six task-oriented documentation routes |
| Adoption context | 4 | 4 | Prerequisites and known source-error limitations are visible |
| Presentation and currency | 8 | 10 | Fresh WebP gallery, alt text, source captions, and compact links |
| Total | 82 | 95 | Editorial assessment against the readme-docs rubric |

The remaining adoption limitation belongs to provider implementation: the existing repository
audit identifies the error and identity paths requiring hardening. Its owner is the movie-data
pipeline, target `slide_maker/parental_guidance.py` and its pipeline boundary. Success means
unavailable optional guidance preserves the deck and only exact movie identities are accepted;
verify those cases offline before a fresh live run. No additional documentation workstream or
animation is needed for this refresh.

## Verification

The exact README entrypoint was executed with the documented environment and tt0107290 input.
It produced `jurassic_park_1993.odp` through headless LibreOffice outside the sandbox.
Image-capture details and final documentation checks are recorded in the companion screenshot
receipt and changelog. No new production behavior or permanent test was introduced.

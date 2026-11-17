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

At the initial capture, the remaining adoption limitation was provider error and identity handling.
The subsequent authorized audit fixes closed those findings, with offline error/identity checks
and successful live retrieval. The known batch table-expansion failure was also fixed through
smaller fixed table pages. No additional documentation workstream or animation was needed.

## Verification

The exact README entrypoint was executed with the documented environment and tt0107290 input.
It produced `jurassic_park_1993.odp` through headless LibreOffice outside the sandbox.
Image-capture details are recorded in
[readme_screenshots_2026_11_17.md](readme_screenshots_2026_11_17.md).
Opening-paragraph, typing, pyflakes, and shebang checks passed 286 cases; Markdown links,
ASCII, and whitespace checks passed 256 cases. All eight final WebPs were inspected.
No new production behavior or permanent test was introduced.

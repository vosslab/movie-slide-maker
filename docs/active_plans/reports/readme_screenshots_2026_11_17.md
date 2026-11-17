# README screenshot capture receipt - 2026-11-17

## Capture command

```bash
source source_me.sh && python3 devel/capture_readme.py
```

The capture harness wrote its transient PDF, PNG, LibreOffice profile, and WebP work under
`_temp/readme_capture_*`. It ran LibreOffice only through the repository helper, whose command
uses `soffice --headless --norestore --convert-to`.

## Published views

Every final WebP was encoded with `cwebp -q 90`, visually inspected as a contact sheet, and is
1654 x 1034 pixels (a 1.60:1 landscape frame). All are below the 1 MB ceiling.

| Screenshot | Fresh source page | Final size |
| --- | --- | ---: |
| `movie_slide_her.webp` | live summary-only deck, page 1 | 178,610 bytes |
| `movie_slide_cooties.webp` | live summary-only deck, page 2 | 118,144 bytes |
| `movie_slide_parasite.webp` | live summary-only deck, page 3 | 215,408 bytes |
| `movie_slide_a_ghost_waits.webp` | live summary-only deck, page 4 | 192,926 bytes |
| `movie_slide_jurassic_park.webp` | `output_smoke/guidance_live/jurassic_park_1993.odp`, PDF page 1 | 148,098 bytes |
| `guidance_csm_overview.webp` | Jurassic Park PDF page 2 | 161,244 bytes |
| `guidance_csm_categories.webp` | Jurassic Park PDF page 3 | 73,704 bytes |
| `guidance_imdb.webp` | Jurassic Park PDF page 4 (IMDb guide, 1/3) | 71,804 bytes |

## Scope and gaps

The four non-Jurassic summaries came from a newly resolved live-source batch. It intentionally
omits *It* because the README has no corresponding screenshot slot. Their capture uses
summary-only slides, so it does not claim that the optional guidance pages for all four movies
converted in this run.

The full multi-movie review-deck attempt resolved all five default movies but stopped at the
existing ODP geometry validation for a guidance table (`0.597 cm` height difference). This receipt
does not represent that failed full guidance batch as accepted evidence. Jurassic Park's four views
were exported successfully from the current staged ODP and include its summary, Common Sense Media
overview, Common Sense Media category table, and IMDb parental-guide table.

## Embedding and cleanup

All eight assets are embedded in the README's single managed screenshot block with descriptive
alt text and links to the full-size WebPs. The existing compact HTML gallery format follows the
repository's human guidance. No managed assets were left unreferenced, removed, or retained as
historical references. No animation or window capture was needed for these static slide outputs.

## Follow-up after audit fixes

The IMDb preview was re-exported and inspected after reducing each table page to two categories.
The fresh Jurassic Park ODP passed conversion and PDF export. The batch-height failure above is
historical evidence from the initial capture, not a reason to bypass conversion validation.
After the pagination and scratch-file ordering fixes, the full five-movie live batch passed and
published a validated 28-page ODP with renders. The IMDb preview now shows page 1 of 3.

## Dedicated refresh verification

The README now documents the capture command and its prerequisites. The script always rebuilds
Jurassic Park through the public pipeline instead of reusing `output_smoke/` artifacts.
A complete rerun refreshed all eight WebPs successfully; the final contact sheet was inspected.
Pyflakes and 38 README/link checks passed. No new options or dependencies were added.

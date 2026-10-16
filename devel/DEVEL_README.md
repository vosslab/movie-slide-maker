# devel scripts

`devel/` holds maintainer-only tools for developing, validating, and releasing
this repository. These files are not product code and are not part of the fast
pytest lane.

Use this folder for scripts that help maintainers do repo-level work:

- Version and release preparation.
- Changelog querying, commit-message drafting, and changelog rotation.
- Documentation repair and repo hygiene cleanup.
- Build-output cleanup that is useful across repo types.
- Template-only developer helpers that should ship into consumer repos under
  their own `devel/` folders.

Do not put reusable library code, runtime application code, or permanent tests
here. Shared test helpers belong in `tests/`; shipped runtime files belong in
the appropriate repo root, package, or `templates/<type>/` path.

## Current root scripts

| File | Kind of work |
| --- | --- |
| [bump_version.py](bump_version.py) | Set or bump repo versions across version files. |
| [changelog_lib.py](changelog_lib.py) | Shared parser and helpers for changelog tools. |
| [commit_changelog.py](commit_changelog.py) | Draft a commit message from new changelog entries. |
| [query_changelog.py](query_changelog.py) | Search active and archived changelog entries. |
| [rotate_changelog.py](rotate_changelog.py) | Move old changelog day blocks into archive files. |
| [flatten_broken_md_links.py](flatten_broken_md_links.py) | Repair or flatten broken Markdown links. |
| [dist_clean.sh](dist_clean.sh) | Remove build artifacts, caches, and dependency installs. |
| [extract_slide_template.py](extract_slide_template.py) | Rebuild the runtime template from local reference decks. |
| [probe_sources.py](probe_sources.py) | Capture live provider evidence and refresh the source-probe report. |

## Template devel scripts

Some developer tools ship into consumer repos via propagation and appear in `devel/` when present.

`templates/shared/devel/` holds tools that propagate to non-PyPI python, rust, swift, and other
consumer repo types (repos with `pyproject.toml` are excluded by the `lacks_file` condition).
When present in a consumer repo, `devel/make_release.py` prepares a GitHub source
release: CalVer freshness check, free-tag check, committed-LICENSE verification, zip and tgz
archive build with byte-level LICENSE spot-check, LLM-prompt generation for the release
description, optional `docs/RELEASE_HISTORY.md` and `docs/NEWS.md` updates, and printed
`git tag` + `gh release create` commands. Use `--dry-run` to preview or `--write` to update
doc files. See [docs/REPO_STYLE.md](../docs/REPO_STYLE.md) versioning section for the full flow.

Some developer tools are type-specific and live under `templates/<type>/devel/`
so they propagate only to matching consumer repos. Examples include Python
release publishing helpers and TypeScript setup/rendering helpers.

## Running scripts

For Python scripts, use the repo bootstrap environment:

```bash
source source_me.sh && python3 devel/<script>.py
```

Use `--help` only for scripts that document that option. The two movie-slide
maintainer tools provide non-mutating help:

```bash
source source_me.sh && python3 devel/extract_slide_template.py --help
source source_me.sh && python3 devel/probe_sources.py --help
```

## Extract the slide template

`extract_slide_template.py` validates the hidden movie slide and rebuilds the
committed runtime template. It requires these ignored, maintainer-owned inputs:

- `SLIDE_ARTIFACTS/class02b-pre-film_content.odp`
- `SLIDE_ARTIFACTS/class02b-pre-film_content.pptx`

Run it only when intentionally refreshing the design authority:

```bash
source source_me.sh && python3 devel/extract_slide_template.py
```

The command replaces `template/movie_slide_template.pptx` after validating the
source page, master, layout, dimensions, fonts, and semantic anchors.

## Probe live sources

`probe_sources.py` exercises TMDB, IMDb, Rotten Tomatoes, and Metacritic for the
five maintained sample movies. It requires network access, installed project
dependencies, and a valid `read_token` in `tmdb_key.yml`.

```bash
source source_me.sh && python3 devel/probe_sources.py
```

The command replaces ignored captures and runtime cache data under
`output_smoke/movie_source_probe/`, then refreshes
`../docs/active_plans/audits/movie_source_probe_report.md`. Captures can include
provider response content; the manifest records that credential values are not
captured.

## Refresh README screenshots

Use the existing batch renderer from the repository root. It generates the actual ODP,
converts it to PDF with LibreOffice, and renders pages with Poppler. Install the maintainer
image encoder with `brew install webp`, then convert the selected pages with `cwebp -q 90`:

```bash
source source_me.sh && python3 -m slide_maker.review_deck < /dev/null
cp output_smoke/review_deck_pages/slide_01.png /tmp/movie_slide_her.png
cp output_smoke/review_deck_pages/slide_02.png /tmp/movie_slide_cooties.png
cp output_smoke/review_deck_pages/slide_04.png /tmp/movie_slide_parasite.png
cp output_smoke/review_deck_pages/slide_05.png /tmp/movie_slide_a_ghost_waits.png
for name in her cooties parasite a_ghost_waits; do
  cwebp -q 90 "/tmp/movie_slide_${name}.png" -o "/tmp/movie_slide_${name}.webp" &&
    cp "/tmp/movie_slide_${name}.webp" docs/screenshots/
done
```

Before copying, confirm the accepted page order is Her, Cooties, It, Parasite, A Ghost Waits.
Inspect the four selected images for clipping and verify the README captions match provider coverage.
Check that A Ghost Waits keeps its ratings on separate rows, crowded slides pair the two RT
ratings before combining other scores, and Parasite displays `Original language: Korean`.
The README uses a 2 by 2 HTML table with 400-pixel previews linked to the full-size WebP images.
Keep WebP images within 1920 pixels on the longer edge and about 1 MB each. The existing renderer
produces 1654 by 1034 pixel images. Update the capture date in [README.md](../README.md)
and record verification in [CHANGELOG.md](../docs/CHANGELOG.md).

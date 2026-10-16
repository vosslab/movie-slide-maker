# Usage

Movie Slide Maker resolves one movie across TMDB, IMDb, Rotten Tomatoes, and Metacritic, then fills
the committed teaching template and writes a semantically validated ODP presentation.

## Quick start

Run the sole root CLI from the repository root:

```bash
source source_me.sh
./make_movie_slide.py
```

At the prompt, enter a title and optional year, an IMDb id or URL, or a TMDB id or URL. For example:

```text
Movie title/year, IMDb id or URL, or TMDB id or URL: https://www.imdb.com/title/tt0316654/
Resolving movie identity with TMDB...
Resolved Spider-Man 2; fetching available ratings...
Available movie data assembled; building the presentation...
Created movie slide: spider_man_2_2004.odp
```

The resulting `spider_man_2_2004.odp` is a standalone one-movie deck in the repository root. Its
scratch PPTX is removed after the ODP passes semantic validation. Generated slides use the lecture
deck's exact 28 by 17.5 cm page size, so copying a slide into that deck does not require scaling.

The ratings block highlights the IMDb score in yellow and abbreviates large vote counts, such as
`435k` or `1.2M`. Rotten Tomatoes critics use a rotten mark below 60, a tomato from 60 through 80,
and a tomato with a trophy above 80. Ratings use separate rows when the plot, review, and
metadata leave enough space. Crowded slides combine ratings, pairing RT critics and RT audience
first; each rating stays together and keeps its provider label. Missing ratings and reviews
are omitted.
The slide displays one `Original language:` value when known and non-English. This is the movie's
original language, not a list of spoken languages or a claim about subtitles in a particular viewing copy.
Text uses Atkinson Hyperlegible Next with a bold title. Generated movie slides require a poster.

## Accepted movie inputs

The prompt accepts these forms:

- Title with year, such as `Her (2013)`, `Her/2013`, or `Her 2013`.
- Title without year, including numeric or punctuated titles such as `2001` or
  `2001: A Space Odyssey`.
- IMDb id or URL, such as `tt0316654` or `https://www.imdb.com/title/tt0316654/`.
- TMDB URL or prefixed id, such as `https://www.themoviedb.org/movie/152601` or `tmdb:152601`.

When a title search has multiple matches, the CLI prints a numbered menu and waits for one choice.
A successful run names the output from the resolved title and year as `./<slug>.odp`.

## Build the review deck

Run the permanent package-based batch entry with stdin closed:

```bash
source source_me.sh && python3 -m slide_maker.review_deck < /dev/null
```

With no arguments, the module resolves this exact built-in list in order:

1. `Her (2013)`
2. `Cooties (2014)`
3. `It (2017)`
4. `Parasite (2019)`
5. `A Ghost Waits (2020)`

Each movie becomes a page using its available information. Source omissions are reported in the
console and do not exclude a movie. An unresolved ambiguity still needs clarification; the batch
reports that request without choosing a different movie.

The module writes `output_smoke/review_deck.odp` and one PNG per accepted page under
`output_smoke/review_deck_pages/`.

## Inputs and outputs

- `tmdb_key.yml` supplies the local TMDB v4 `read_token` documented in
  [INSTALL.md](INSTALL.md).
- `template/movie_slide_template.pptx` is the committed runtime design authority.
- `make_movie_slide.py` is the only root Python entry and writes `./<slug>.odp`.
- `slide_maker/` contains provider, orchestration, builder, and conversion modules.
- `output_smoke/review_deck.odp` is the generated multi-movie review artifact.
- `output_smoke/visual_accept/her_2013.png` and
  `output_smoke/visual_accept/her_2013_long_text.png` are generated M15 render evidence.
- `output_smoke/review_deck_pages/slide_<NN>.png` is generated M18 page evidence.
- `output_smoke/adaptive_slides/adaptive_slides.odp` covers complete and sparse examples.
- `output_smoke/example/her_2013.odp` is the illustrated documentation example, using fixed
  example ratings rather than a live provider snapshot.

`SLIDE_ARTIFACTS/` is ignored local reference material for comparison and planning. The runtime does
not read it.

## Failure behavior

Optional metadata has no minimum completeness threshold. Missing ratings or descriptions produce
source diagnostics while other information remains usable. Movie identity and a poster are required.
If the primary poster is absent or fails, the tool tries alternative posters from the same movie's
[TMDB images endpoint](https://developer.themoviedb.org/reference/movie-images). If none can be
retrieved, generation stops with a poster error before writing a slide. No missing value is invented.

The low-level builder can render explicitly supplied sparse `MovieData` for diagnostics; the normal
single-movie and batch workflows require a poster. Absent scalar values use `None`, text uses empty
strings, and lists are empty.
Rating marks are derived from the available scores. Unknown years are omitted from titles and
filenames. Original language is a single English display name.

Conversion checks that the included content survives into the ODP. If LibreOffice conversion or
ODP validation fails, the scratch PPTX remains available for diagnosis and no validated ODP is
published. Configuration errors and unexpected programming errors remain visible.

On macOS, the converter launches LibreOffice through LaunchServices in headless mode. This avoids
the intermittent AppKit registration abort and visible crash dialog caused by starting the
application binary directly.

Live ratings, canonical provider URLs, and source markup can change between runs. The program checks
current identity and required meaning instead of expecting old rating values.

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
Resolved Spider-Man 2 (2004); fetching ratings...
All provider data validated; building the presentation...
Created validated movie slide: spider_man_2_2004.odp
```

The resulting `spider_man_2_2004.odp` is a standalone one-movie deck in the repository root. Its
scratch PPTX is removed after the ODP passes semantic validation.

## Accepted movie inputs

The prompt accepts these forms:

- Title with year, such as `Her (2013)` or `Her 2013`.
- Title without year, such as `Her`.
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
4. `Sinners (2025)`
5. `A Ghost Waits (2020)`

Each movie either becomes one accepted page or receives a contextual source-and-identity failure.
The current acceptance run produced four pages and rejected `A Ghost Waits (2020)` at Rotten
Tomatoes because its required data was unavailable. This count can change when live provider data
changes; the batch never includes a partially validated movie.

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

`SLIDE_ARTIFACTS/` is ignored local reference material for comparison and planning. The runtime does
not read it.

## Failure behavior

All four provider results and the poster must pass identity and mandatory-field validation before
the builder writes a product. Provider and contract failures name the source and movie identity and
create no new PPTX or ODP. If LibreOffice conversion or ODP validation fails, the command preserves
the scratch PPTX for diagnosis but does not publish a validated ODP. A Rotten Tomatoes critics
consensus and a Metacritic score are required by design.

Live ratings, canonical provider URLs, and source markup can change between runs. The program checks
current identity and required meaning instead of expecting old rating values.

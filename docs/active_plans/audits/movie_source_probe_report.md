# Movie source probe report

Generated: `2026-07-21T16:00:30.199518+00:00`

This live probe separates page resolution, parsing of fields that exist, and clean
absence of fields that genuinely do not exist. A clean absence is a correct M0 outcome;
the later product still treats missing RT consensus or Metascore as a mandatory abort.
Every live request uses the production `slide_maker/http_client.py` policy, and TMDB
credentials come from `slide_maker/config.py`.
Credential values are never written to captures or this report.
Raw responses are reproducibly generated under
`output_smoke/movie_source_probe/captured/`. That gitignored directory contains probe
evidence, not committed test inputs. Probe-specific runtime cache data stays under
`output_smoke/movie_source_probe/runtime_cache/`.

## Sample

| Movie | IMDB id | Stress case |
| --- | --- | --- |
| Her (2013) | `tt1798709` | reference film |
| Cooties (2014) | `tt2490326` | rotten critic and audience scores |
| It (2017) | `tt1396484` | ambiguous title and slug |
| Sinners (2025) | `tt31193180` | current-release freshness |
| A Ghost Waits (2020) | `tt6048638` | low-vote film with mandatory-field absences |

## Source totals

- TMDB: resolution 5/5; parse 5/5 applicable; clean absence 0; correct outcome 5/5
- IMDB: resolution 5/5; parse 5/5 applicable; clean absence 0; correct outcome 5/5
- Rotten Tomatoes: resolution 5/5; parse 5/5 applicable; clean absence 1; correct outcome 5/5
- Metacritic: resolution 5/5; parse 4/4 applicable; clean absence 1; correct outcome 5/5

## Evidence rows

| Source | Movie | Resolution | Parse | Absence | Correct | Path | Observed | Blocking | Target URL or id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TMDB | Her (2013) | OK | OK | none | YES | search/movie + movie/{id}?append_to_response=credits,external_ids | tmdb_id=152601; imdb_id=tt1798709; directors=Spike Jonze | none | https://api.themoviedb.org/3/movie/152601?append_to_response=credits%2Cexternal_ids&language=en-US |
| IMDB | Her (2013) | OK | OK | none | YES | imdbinfo | imdb_id=tt1798709; rating=8.0; votes=730005 | direct HTML HTTP 202 challenge; imdbinfo succeeded | https://www.imdb.com/title/tt1798709/ |
| Rotten Tomatoes | Her (2013) | OK (2/3 identity checks) | OK | none | YES | media-scorecard-json + What to Know HTML | tomatometer=95; consensus=present | none | https://www.rottentomatoes.com/m/her |
| Metacritic | Her (2013) | OK (3/3 identity checks) | OK | none | YES | ld+json | metascore=91 | none | https://www.metacritic.com/movie/her/ |
| TMDB | Cooties (2014) | OK | OK | none | YES | search/movie + movie/{id}?append_to_response=credits,external_ids | tmdb_id=241843; imdb_id=tt2490326; directors=Cary Murnion, Jonathan Milott | none | https://api.themoviedb.org/3/movie/241843?append_to_response=credits%2Cexternal_ids&language=en-US |
| IMDB | Cooties (2014) | OK | OK | none | YES | imdbinfo | imdb_id=tt2490326; rating=5.7; votes=31031 | direct HTML HTTP 202 challenge; imdbinfo succeeded | https://www.imdb.com/title/tt2490326/ |
| Rotten Tomatoes | Cooties (2014) | OK (2/3 identity checks) | OK | none | YES | media-scorecard-json + What to Know HTML | tomatometer=44; consensus=present | none | https://www.rottentomatoes.com/m/cooties |
| Metacritic | Cooties (2014) | OK (2/3 identity checks) | OK | none | YES | ld+json | metascore=49 | none | https://www.metacritic.com/movie/cooties/ |
| TMDB | It (2017) | OK | OK | none | YES | search/movie + movie/{id}?append_to_response=credits,external_ids | tmdb_id=346364; imdb_id=tt1396484; directors=Andy Muschietti | none | https://api.themoviedb.org/3/movie/346364?append_to_response=credits%2Cexternal_ids&language=en-US |
| IMDB | It (2017) | OK | OK | none | YES | imdbinfo | imdb_id=tt1396484; rating=7.3; votes=702624 | direct HTML HTTP 202 challenge; imdbinfo succeeded | https://www.imdb.com/title/tt1396484/ |
| Rotten Tomatoes | It (2017) | OK (3/3 identity checks) | OK | none | YES | media-scorecard-json + What to Know HTML | tomatometer=85; consensus=present | none | https://www.rottentomatoes.com/m/it_2017 |
| Metacritic | It (2017) | OK (3/3 identity checks) | OK | none | YES | ld+json | metascore=69 | none | https://www.metacritic.com/movie/it/ |
| TMDB | Sinners (2025) | OK | OK | none | YES | search/movie + movie/{id}?append_to_response=credits,external_ids | tmdb_id=1233413; imdb_id=tt31193180; directors=Ryan Coogler | none | https://api.themoviedb.org/3/movie/1233413?append_to_response=credits%2Cexternal_ids&language=en-US |
| IMDB | Sinners (2025) | OK | OK | none | YES | imdbinfo | imdb_id=tt31193180; rating=7.5; votes=503883 | direct HTML HTTP 202 challenge; imdbinfo succeeded | https://www.imdb.com/title/tt31193180/ |
| Rotten Tomatoes | Sinners (2025) | OK (3/3 identity checks) | OK | none | YES | media-scorecard-json + What to Know HTML | tomatometer=97; consensus=present | none | https://www.rottentomatoes.com/m/sinners_2025 |
| Metacritic | Sinners (2025) | OK (3/3 identity checks) | OK | none | YES | ld+json | metascore=84 | none | https://www.metacritic.com/movie/sinners/ |
| TMDB | A Ghost Waits (2020) | OK | OK | none | YES | search/movie + movie/{id}?append_to_response=credits,external_ids | tmdb_id=665109; imdb_id=tt6048638; directors=Adam Stovall | none | https://api.themoviedb.org/3/movie/665109?append_to_response=credits%2Cexternal_ids&language=en-US |
| IMDB | A Ghost Waits (2020) | OK | OK | none | YES | imdbinfo | imdb_id=tt6048638; rating=6.2; votes=991 | direct HTML HTTP 202 challenge; imdbinfo succeeded | https://www.imdb.com/title/tt6048638/ |
| Rotten Tomatoes | A Ghost Waits (2020) | OK (2/3 identity checks) | OK | CLEAN: critics consensus missing | YES | media-scorecard-json + What to Know HTML | tomatometer=96; consensus=absent | none | https://www.rottentomatoes.com/m/a_ghost_waits |
| Metacritic | A Ghost Waits (2020) | OK (2/3 identity checks) | N/A: field absent | CLEAN: Metascore missing | YES | ld+json | metascore=absent | none | https://www.metacritic.com/movie/a-ghost-waits/ |

## Parse contracts

| Source | Winning path | Exact keys or selector |
| --- | --- | --- |
| TMDB | search/movie + movie/{id}?append_to_response=credits,external_ids | results[].{id,title,original_title,release_date}; {id,title,release_date,overview,genres,runtime,poster_path}; credits.crew[].{job,name}; external_ids.imdb_id |
| IMDB | imdbinfo | props.pageProps.mainColumnData.ratingsSummary.{aggregateRating,voteCount} |
| Rotten Tomatoes | media-scorecard-json + What to Know HTML | vanity.{title,lifecycleWindow.date}; where-to-watch-json.director; media-scorecard-json.criticsScore.score; Critics Consensus + p |
| Metacritic | ld+json | name; datePublished; director[].name; aggregateRating.ratingValue |

## Capture index

Manifest: `output_smoke/movie_source_probe/captured/manifest.json`

The manifest and response captures are generated output and remain uncommitted.
Each SHA-256 value below is computed from the corresponding raw response.

| Source | Movie | Target URL or id | Capture | SHA-256 |
| --- | --- | --- | --- | --- |
| TMDB | Her (2013) | https://api.themoviedb.org/3/movie/152601?append_to_response=credits%2Cexternal_ids&language=en-US | `output_smoke/movie_source_probe/captured/tmdb_her_2013_search.json` | `01ae6039e9ce5277dc750cb98122b509af7e9c835dfe3d8b5886318d52816228` |
| TMDB | Her (2013) | https://api.themoviedb.org/3/movie/152601?append_to_response=credits%2Cexternal_ids&language=en-US | `output_smoke/movie_source_probe/captured/tmdb_her_2013_details.json` | `ee03a2b4b70fbdba255dbc6890a0461628facb07fddf2d2125fc45be17334ee7` |
| IMDB | Her (2013) | https://www.imdb.com/title/tt1798709/ | `output_smoke/movie_source_probe/captured/imdb_her_2013_direct.html` | `9f05666ad31c8966c4b441c9494e670a075bbd7d68d06459da635c321c039cbe` |
| IMDB | Her (2013) | https://www.imdb.com/title/tt1798709/ | `output_smoke/movie_source_probe/captured/imdb_her_2013_imdbinfo.json` | `72dd8c34f6a2f2cf24a6b0250f6ad795d69cb91e97fee0fad373979874918a0d` |
| Rotten Tomatoes | Her (2013) | https://www.rottentomatoes.com/m/her | `output_smoke/movie_source_probe/captured/rt_her_2013.html` | `6b0f94f5d98d2d1a8be356d27d5e3bd284f71be20f1a124ac68b3c2967a14fb0` |
| Metacritic | Her (2013) | https://www.metacritic.com/movie/her/ | `output_smoke/movie_source_probe/captured/metacritic_her_2013.html` | `aab95885f529dc99a816ed2c6c374fd2d862abb7cd7664606090bf898ac53de5` |
| TMDB | Cooties (2014) | https://api.themoviedb.org/3/movie/241843?append_to_response=credits%2Cexternal_ids&language=en-US | `output_smoke/movie_source_probe/captured/tmdb_cooties_2014_search.json` | `12744f67a58d555f3498469eaef5c3ae53bf0f14433bac12675a5b94728484d6` |
| TMDB | Cooties (2014) | https://api.themoviedb.org/3/movie/241843?append_to_response=credits%2Cexternal_ids&language=en-US | `output_smoke/movie_source_probe/captured/tmdb_cooties_2014_details.json` | `772359daaf8adc510ab811c13093d697436b50d25024991828f3648afb276c9f` |
| IMDB | Cooties (2014) | https://www.imdb.com/title/tt2490326/ | `output_smoke/movie_source_probe/captured/imdb_cooties_2014_direct.html` | `4ad5df9974248a017af846be6059b0dde818eeee0290c387863d81cab90878c9` |
| IMDB | Cooties (2014) | https://www.imdb.com/title/tt2490326/ | `output_smoke/movie_source_probe/captured/imdb_cooties_2014_imdbinfo.json` | `487b9eeca223ab88a96071495da4e386b71770f880fc9baca4b342116f818d39` |
| Rotten Tomatoes | Cooties (2014) | https://www.rottentomatoes.com/m/cooties | `output_smoke/movie_source_probe/captured/rt_cooties_2014.html` | `0f1db4334105d9b2bbe035e2b8864460417ff0cd4b05568aecef3dbb4a4c24bf` |
| Metacritic | Cooties (2014) | https://www.metacritic.com/movie/cooties/ | `output_smoke/movie_source_probe/captured/metacritic_cooties_2014.html` | `7fdbee7f8eec689383b52c2525c20bbbdf6e92df243b434b586b8c5c94b5069e` |
| TMDB | It (2017) | https://api.themoviedb.org/3/movie/346364?append_to_response=credits%2Cexternal_ids&language=en-US | `output_smoke/movie_source_probe/captured/tmdb_it_2017_search.json` | `fd1fdecafab12f17c1af1018f3d1ad7caf13c24baf888fb4f482266b10fac2fb` |
| TMDB | It (2017) | https://api.themoviedb.org/3/movie/346364?append_to_response=credits%2Cexternal_ids&language=en-US | `output_smoke/movie_source_probe/captured/tmdb_it_2017_details.json` | `5aa4473cce05c394695c86379d428e72625205516379209b6eb8333887b7d668` |
| IMDB | It (2017) | https://www.imdb.com/title/tt1396484/ | `output_smoke/movie_source_probe/captured/imdb_it_2017_direct.html` | `e90142891e812624040b90899802460a268bbf114c97005f97158203e682cf40` |
| IMDB | It (2017) | https://www.imdb.com/title/tt1396484/ | `output_smoke/movie_source_probe/captured/imdb_it_2017_imdbinfo.json` | `2d34ee6362087ee9842ff0b8379cd94f6373cb3090581178c0103ce6196deb6a` |
| Rotten Tomatoes | It (2017) | https://www.rottentomatoes.com/m/it_2017 | `output_smoke/movie_source_probe/captured/rt_it_2017.html` | `dac5055cdf31d53a2b8fe516d5e21125e173400fbb557655a0be324d5017fe46` |
| Metacritic | It (2017) | https://www.metacritic.com/movie/it/ | `output_smoke/movie_source_probe/captured/metacritic_it_2017.html` | `f4aa9efe0955b2b90f8722da10707845a79de86c8420f28ad058bb76362eee79` |
| TMDB | Sinners (2025) | https://api.themoviedb.org/3/movie/1233413?append_to_response=credits%2Cexternal_ids&language=en-US | `output_smoke/movie_source_probe/captured/tmdb_sinners_2025_search.json` | `f62829739e2b0353880513c6e11ac0da185c771bd459a41a2b75ce618296dc26` |
| TMDB | Sinners (2025) | https://api.themoviedb.org/3/movie/1233413?append_to_response=credits%2Cexternal_ids&language=en-US | `output_smoke/movie_source_probe/captured/tmdb_sinners_2025_details.json` | `85e2ac0fe35934b249313792f76dfee74a005ec86bb8acbbb7913496f09e6e81` |
| IMDB | Sinners (2025) | https://www.imdb.com/title/tt31193180/ | `output_smoke/movie_source_probe/captured/imdb_sinners_2025_direct.html` | `0f34251728ee79b19ff5e36b80a4ee938eecabffdd0e7b35ccef226dd5f78d10` |
| IMDB | Sinners (2025) | https://www.imdb.com/title/tt31193180/ | `output_smoke/movie_source_probe/captured/imdb_sinners_2025_imdbinfo.json` | `fec77be0f491059b6c7cdcd81fd4f573f31f2d95c35c678628b62936a39893eb` |
| Rotten Tomatoes | Sinners (2025) | https://www.rottentomatoes.com/m/sinners_2025 | `output_smoke/movie_source_probe/captured/rt_sinners_2025.html` | `b75dfe7b9e79bb20778fbc46f581e11536db187f7f0d419abb5f9439bd434bba` |
| Metacritic | Sinners (2025) | https://www.metacritic.com/movie/sinners/ | `output_smoke/movie_source_probe/captured/metacritic_sinners_2025.html` | `33338bc170d5af544f28d7389768c4d2850a39666e831768948040abcfa7b1d0` |
| TMDB | A Ghost Waits (2020) | https://api.themoviedb.org/3/movie/665109?append_to_response=credits%2Cexternal_ids&language=en-US | `output_smoke/movie_source_probe/captured/tmdb_a_ghost_waits_2020_search.json` | `4ed36ad6e24c88eddc4fde4d1cd83de07d6fbec383560e162404d7a0b1cf14ab` |
| TMDB | A Ghost Waits (2020) | https://api.themoviedb.org/3/movie/665109?append_to_response=credits%2Cexternal_ids&language=en-US | `output_smoke/movie_source_probe/captured/tmdb_a_ghost_waits_2020_details.json` | `9e1181f4f486b477d860bf6b4d1c05dc228562b7b052a8a477f4c992e5082e94` |
| IMDB | A Ghost Waits (2020) | https://www.imdb.com/title/tt6048638/ | `output_smoke/movie_source_probe/captured/imdb_a_ghost_waits_2020_direct.html` | `0c5db9e916a6db0a7cdee5c8a3da5d55559393f7458ebaa1b0c99559494c2412` |
| IMDB | A Ghost Waits (2020) | https://www.imdb.com/title/tt6048638/ | `output_smoke/movie_source_probe/captured/imdb_a_ghost_waits_2020_imdbinfo.json` | `fd2dd634e03b267f719a37fd5fa734bff589a76132c750ae2173b1ed1bd49f62` |
| Rotten Tomatoes | A Ghost Waits (2020) | https://www.rottentomatoes.com/m/a_ghost_waits | `output_smoke/movie_source_probe/captured/rt_a_ghost_waits_2020.html` | `bee3762656b07480b9b5a7a60e7a377098c248b9b58e656c11e4fdfae60d7488` |
| Metacritic | A Ghost Waits (2020) | https://www.metacritic.com/movie/a-ghost-waits/ | `output_smoke/movie_source_probe/captured/metacritic_a_ghost_waits_2020.html` | `c7c85e45900b1e02fb4fa0175de1cb5fb39da94a82f26be5c2af2f929f3d5546` |

## Provider gate

- TMDB: GO. All five outcomes were classified correctly.
- IMDB: GO. All five outcomes were classified correctly.
- Rotten Tomatoes: GO. All five outcomes were classified correctly.
- Metacritic: GO. All five outcomes were classified correctly.

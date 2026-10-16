"""Protect independent metadata and original-language selection."""

# Standard Library
import json
import types
import pathlib
import unittest.mock

# local repo modules
import slide_maker.imdb_ratings
import slide_maker.movie_pipeline
import slide_maker.movie_resolver
import slide_maker.tmdb_client


#============================================
def test_original_language_ignores_spoken_order() -> None:
	"""Select the original code even when another spoken language appears first."""
	data = {
		"original_language": "ko",
		"spoken_languages": [
			{"iso_639_1": "en", "english_name": "English"},
			{"iso_639_1": "ko", "english_name": "Korean"},
		],
	}
	assert slide_maker.tmdb_client._original_language_name(data, "unused") == "Korean"


#============================================
def test_original_language_needs_english_name() -> None:
	"""A native name is not mislabeled as the English display name."""
	data = {
		"original_language": "ko",
		"spoken_languages": [{"iso_639_1": "ko", "name": "\ud55c\uad6d\uc5b4"}],
	}
	response = types.SimpleNamespace(status_code=200, text="[]")
	with unittest.mock.patch("slide_maker.http_client.fetch_url", return_value=response):
		assert slide_maker.tmdb_client._original_language_name(data, "unused") is None


#============================================
def test_imdb_keeps_score_without_valid_votes() -> None:
	"""Malformed optional votes do not erase a usable score."""
	url = "https://www.imdb.com/title/tt1234567/"
	record = {"@type": "Movie", "aggregateRating": {"ratingValue": 8.2, "ratingCount": "bad"}}
	body = f"<script type='application/ld+json'>{json.dumps(record)}</script>"
	response = types.SimpleNamespace(status_code=200, url=url, text=body)
	with unittest.mock.patch("slide_maker.imdb_ratings.fetch_imdb_page", return_value=response):
		rating = slide_maker.imdb_ratings.rating_from_json_ld("tt1234567", url)
	assert rating.imdb_rating == 8.2
	assert rating.imdb_votes is None


#============================================
def test_pipeline_keeps_selection_when_details_return_wrong_id(tmp_path: pathlib.Path) -> None:
	"""Wrong-film details cannot replace the selected movie or prevent its slide."""
	selection = slide_maker.movie_resolver.ResolvedTmdbMovie(42, "Selected Movie", 1999)
	wrong = slide_maker.tmdb_client.TmdbMovie(
		title="Selected Movie", year=1999, tmdb_id=43, plot="Wrong-film information",
	)
	providers = slide_maker.movie_pipeline.ProviderBundle(
		resolve_tmdb_id=unittest.mock.Mock(return_value=42),
		resolve_tmdb_movie=unittest.mock.Mock(return_value=selection),
		fetch_tmdb_movie=unittest.mock.Mock(return_value=wrong),
		fetch_imdb_rating=unittest.mock.Mock(side_effect=AssertionError("Wrong movie enriched")),
		fetch_rt_rating=unittest.mock.Mock(side_effect=AssertionError("Wrong movie enriched")),
		fetch_metacritic_rating=unittest.mock.Mock(side_effect=AssertionError("Wrong movie enriched")),
	)
	result = slide_maker.movie_pipeline.resolve_movie_data(
		"Selected Movie (1999)", tmp_path, providers, write_line=unittest.mock.Mock(),
	)
	assert (result.title, result.year) == ("Selected Movie", 1999)
	assert result.tmdb_id is None and result.plot == ""

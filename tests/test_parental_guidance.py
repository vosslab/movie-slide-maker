"""Protect editable parental-guidance source parsing."""

# Standard Library
import json
import types
import unittest.mock

# PIP3 modules
import pytest

# local repo modules
import slide_maker.parental_guidance
import slide_maker.imdb_ratings


#============================================
def test_imdb_guidance_keeps_non_spoiler_example() -> None:
	"""IMDb parsing retains the first safe example and category severity."""
	url = "https://www.imdb.com/title/tt1234567/parentalguide/"
	content = {
		"data": {"title": {"id": "tt1234567", "certificate": {"rating": "PG-13"}}},
		"contentRatingData": {"ratingReason": "Rated PG-13 for science fiction peril."},
		"categories": [
			{
				"title": "Violence & Gore",
				"severitySummary": {"text": "Moderate"},
				"items": [
					{"isSpoiler": True, "text": "Spoiler text"},
					{"text": "Unknown spoiler status"},
					{"isSpoiler": False, "text": "A <b>brief</b> chase occurs."},
				],
			}
		],
	}
	page = {"props": {"pageProps": {"contentData": content}}}
	body = '<script id="__NEXT_DATA__" type="application/json">' + json.dumps(page) + "</script>"
	response = types.SimpleNamespace(status_code=200, url=url, text=body)
	with unittest.mock.patch("slide_maker.imdb_ratings.fetch_imdb_page", return_value=response):
		guidance = slide_maker.parental_guidance.fetch_imdb_guidance("tt1234567")
	assert guidance.categories[0].severity == "Moderate"
	assert guidance.categories[0].example == "A brief chase occurs."


#============================================
@pytest.mark.parametrize("linked_id", ["tt0000001", "tt12345678"])
def test_csm_guidance_requires_linked_imdb_id(linked_id: str) -> None:
	"""A similarly named Common Sense page cannot supply another movie's guidance."""
	movie = {"@type": "Movie", "sameAs": f"https://www.imdb.com/title/{linked_id}/"}
	page = (
		'<script type="application/ld+json">'
		+ json.dumps({"@graph": [movie]}) + "</script>"
	)
	response = types.SimpleNamespace(status_code=200, text=page)
	with unittest.mock.patch("slide_maker.http_client.fetch_url", return_value=response):
		with pytest.raises(slide_maker.parental_guidance.ParentalGuidanceSourceError):
			slide_maker.parental_guidance.fetch_csm_guidance("example", "tt1234567")


#============================================
def test_imdb_failure_uses_optional_guidance_error() -> None:
	"""Network errors reach the pipeline's existing unavailable-source handler."""
	with unittest.mock.patch(
		"slide_maker.imdb_ratings.fetch_imdb_page",
		side_effect=slide_maker.imdb_ratings.ImdbSourceError("Network unavailable"),
	):
		with pytest.raises(slide_maker.parental_guidance.ParentalGuidanceSourceError):
			slide_maker.parental_guidance.fetch_imdb_guidance("tt1234567")


#============================================
@pytest.mark.parametrize("data", [[], {"@graph": None}])
def test_csm_bad_shape_uses_optional_guidance_error(data: object) -> None:
	"""Unsupported structured data is a source omission rather than an uncaught error."""
	page = '<script type="application/ld+json">' + json.dumps(data) + "</script>"
	with pytest.raises(slide_maker.parental_guidance.ParentalGuidanceSourceError):
		slide_maker.parental_guidance._csm_json_ld(page, "https://www.commonsensemedia.org/movie-reviews/example")

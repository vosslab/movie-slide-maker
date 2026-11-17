"""Protect editable parental-guidance source parsing."""

# Standard Library
import json
import types
import unittest.mock

# local repo modules
import slide_maker.parental_guidance


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
def test_csm_guidance_requires_linked_imdb_id() -> None:
	"""A similarly named Common Sense page cannot supply another movie's guidance."""
	page = (
		'<script type="application/ld+json">'
		'{"@graph":[{"@type":"Movie","sameAs":"https://www.imdb.com/title/tt0000001/"}]}'
		"</script>"
	)
	response = types.SimpleNamespace(status_code=200, text=page)
	with unittest.mock.patch("slide_maker.http_client.fetch_url", return_value=response):
		with unittest.mock.patch("slide_maker.http_client.request_once"):
			try:
				slide_maker.parental_guidance.fetch_csm_guidance("example", "tt1234567")
			except slide_maker.parental_guidance.ParentalGuidanceSourceError as error:
				message = str(error)
			else:
				raise AssertionError("Expected a mismatched CSM identity to fail")
	assert "identity did not match" in message

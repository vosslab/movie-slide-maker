"""Fetch concise, identity-checked parental guidance for movie slides."""

# Standard Library
import re
import json
import html
import dataclasses
import urllib.parse

# local repo modules
import slide_maker.http_client
import slide_maker.imdb_ratings


CSM_MOVIE_ROOT = "https://www.commonsensemedia.org/movie-reviews"
CSM_CATEGORY_NAMES = {
	"Violence & Scariness",
	"Language",
	"Products & Purchases",
	"Sex, Romance & Nudity",
	"Drinking, Drugs & Smoking",
	"Positive Messages",
	"Positive Role Models",
	"Diverse Representations",
}


@dataclasses.dataclass(frozen=True, slots=True)
class GuidanceCategory:
	"""One source-supplied content category suitable for a compact table."""

	name: str
	score: int | None = None
	severity: str = ""
	example: str = ""


@dataclasses.dataclass(frozen=True, slots=True)
class SourceGuidance:
	"""Guidance retained from one provider after identity validation."""

	provider: str
	url: str
	overview: str = ""
	age: str = ""
	certificate: str = ""
	rating_reason: str = ""
	categories: tuple[GuidanceCategory, ...] = ()


@dataclasses.dataclass(frozen=True, slots=True)
class ParentalGuidance:
	"""Available parental-guidance sources and concise omission diagnostics."""

	csm: SourceGuidance | None = None
	imdb: SourceGuidance | None = None
	diagnostics: tuple[str, ...] = ()


class ParentalGuidanceSourceError(RuntimeError):
	"""Report a provider response that cannot safely supply parental guidance."""


#============================================
def _plain_html(value: str) -> str:
	"""Return compact readable text from one provider-supplied HTML fragment."""
	unescaped = html.unescape(value)
	text = re.sub(r"<[^>]+>", " ", unescaped)
	plain = " ".join(text.split())
	return plain


#============================================
def _short_text(value: str, maximum_words: int) -> str:
	"""Keep a readable provider excerpt within one slide's content budget."""
	words = value.split()
	if len(words) <= maximum_words:
		return value
	shortened = " ".join(words[:maximum_words]).rstrip(".,;:") + "..."
	return shortened


#============================================
def _next_data(page: str, source_url: str) -> dict:
	"""Read IMDb's embedded Next data object from one parental-guide page."""
	match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', page, re.DOTALL)
	if match is None:
		raise ParentalGuidanceSourceError(f"IMDb guide has no embedded data at {source_url}")
	try:
		data = json.loads(match.group(1))
	except json.JSONDecodeError as error:
		raise ParentalGuidanceSourceError(f"IMDb guide data was invalid at {source_url}") from error
	if not isinstance(data, dict):
		raise ParentalGuidanceSourceError(f"IMDb guide data was not an object at {source_url}")
	return data


#============================================
def fetch_imdb_guidance(imdb_id: str) -> SourceGuidance:
	"""Fetch severity summaries and non-spoiler examples from IMDb's guide."""
	normalized_id = slide_maker.imdb_ratings.normalize_imdb_id(imdb_id)
	url = f"https://www.imdb.com/title/{normalized_id}/parentalguide/"
	try:
		response = slide_maker.imdb_ratings.fetch_imdb_page(url)
	except slide_maker.imdb_ratings.ImdbSourceError as error:
		raise ParentalGuidanceSourceError(f"IMDb guidance request failed at {url}: {error}") from error
	if response.status_code != 200:
		raise ParentalGuidanceSourceError(f"IMDb returned HTTP {response.status_code} at {url}")
	if f"/title/{normalized_id}/" not in str(response.url):
		raise ParentalGuidanceSourceError(f"IMDb returned a different title at {url}")
	data = _next_data(response.text, url)
	try:
		content_data = data["props"]["pageProps"]["contentData"]
		title = content_data["data"]["title"]
		actual_id = title["id"]
		categories_data = content_data["categories"]
	except (KeyError, TypeError) as error:
		raise ParentalGuidanceSourceError(f"IMDb guide fields were missing at {url}") from error
	if actual_id != normalized_id:
		raise ParentalGuidanceSourceError(f"IMDb guide identity did not match {normalized_id}")
	if not isinstance(categories_data, list):
		raise ParentalGuidanceSourceError(f"IMDb guide categories were invalid at {url}")
	categories = []
	for category in categories_data:
		if not isinstance(category, dict):
			continue
		name = category.get("title")
		severity_data = category.get("severitySummary")
		severity = severity_data.get("text") if isinstance(severity_data, dict) else ""
		if not isinstance(name, str) or not name.strip() or not isinstance(severity, str):
			continue
		example = ""
		for item in category.get("items", []):
			if not isinstance(item, dict) or item.get("isSpoiler") is not False:
				continue
			value = item.get("text")
			if isinstance(value, str) and value.strip():
				example = _short_text(_plain_html(value), 35)
				break
		categories.append(GuidanceCategory(name=name.strip(), severity=severity.strip(), example=example))
	certificate_data = title.get("certificate")
	certificate = certificate_data.get("rating") if isinstance(certificate_data, dict) else ""
	rating_data = content_data.get("contentRatingData")
	rating_reason = rating_data.get("ratingReason") if isinstance(rating_data, dict) else ""
	guide = SourceGuidance(
		provider="IMDb Parents' Guide",
		url=url,
		certificate=certificate.strip() if isinstance(certificate, str) else "",
		rating_reason=_short_text(rating_reason.strip(), 35) if isinstance(rating_reason, str) else "",
		categories=tuple(categories),
	)
	return guide


#============================================
def _csm_json_ld(page: str, source_url: str) -> dict:
	"""Return the movie object from Common Sense Media's JSON-LD graph."""
	match = re.search(r'<script type="application/ld\+json">(.*?)</script>', page, re.DOTALL)
	if match is None:
		raise ParentalGuidanceSourceError(f"Common Sense Media has no JSON-LD at {source_url}")
	try:
		data = json.loads(match.group(1))
	except json.JSONDecodeError as error:
		raise ParentalGuidanceSourceError(f"Common Sense Media JSON-LD was invalid at {source_url}") from error
	if not isinstance(data, dict) or not isinstance(data.get("@graph"), list):
		raise ParentalGuidanceSourceError(f"Common Sense Media JSON-LD shape was invalid at {source_url}")
	for record in data["@graph"]:
		if isinstance(record, dict) and record.get("@type") == "Movie":
			return record
	raise ParentalGuidanceSourceError(f"Common Sense Media movie identity was absent at {source_url}")


#============================================
def fetch_csm_guidance(slug: str, imdb_id: str) -> SourceGuidance:
	"""Fetch Common Sense Media overview and category scores for an IMDb id."""
	if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) is None:
		raise ValueError(f"Invalid Common Sense Media movie slug: {slug!r}")
	normalized_id = slide_maker.imdb_ratings.normalize_imdb_id(imdb_id)
	url = f"{CSM_MOVIE_ROOT}/{slug}"
	try:
		response = slide_maker.http_client.fetch_url(url)
	except slide_maker.http_client.HttpSourceError as error:
		raise ParentalGuidanceSourceError(f"Common Sense Media network request failed at {url}") from error
	if response.status_code != 200:
		raise ParentalGuidanceSourceError(f"Common Sense Media returned HTTP {response.status_code} at {url}")
	movie = _csm_json_ld(response.text, url)
	same_as = movie.get("sameAs")
	linked_url = urllib.parse.urlsplit(same_as) if isinstance(same_as, str) else None
	linked_id = re.fullmatch(r"/title/(tt[0-9]{7,10})/?", linked_url.path) if linked_url else None
	if (
		linked_url is None or linked_url.hostname not in ("imdb.com", "www.imdb.com")
		or linked_id is None or linked_id.group(1) != normalized_id
	):
		raise ParentalGuidanceSourceError(f"Common Sense Media identity did not match {normalized_id}")
	age_match = re.search(r'<span class="rating__age">\s*([^<]+)', response.text)
	age = " ".join(age_match.group(1).split()) if age_match is not None else ""
	overview_match = re.search(
		r'<h3>Parents Need to Know</h3>.*?<div class="paragraph-inline paragraph-formatted">\s*<p>(.*?)</p>',
		response.text,
		re.DOTALL,
	)
	overview = _plain_html(overview_match.group(1)) if overview_match is not None else ""
	overview = _short_text(overview, 140)
	category_pattern = re.compile(
		r'<div class="content-grid-content" data-text="(.*?)">.*?'
		r'<span class="rating__label">(.*?)</span>.*?'
		r'<span class="rating__score"[^>]*>(.*?)</span>',
		re.DOTALL,
	)
	categories = []
	for match in category_pattern.finditer(response.text):
		name = _plain_html(match.group(2))
		if name not in CSM_CATEGORY_NAMES:
			continue
		active = len(re.findall(r'icon-circle-solid active', match.group(3)))
		example = _short_text(_plain_html(match.group(1)), 35)
		if name:
			categories.append(GuidanceCategory(name=name, score=active, example=example))
	guide = SourceGuidance(
		provider="Common Sense Media",
		url=url,
		overview=overview,
		age=age,
		certificate=movie.get("contentRating", "") if isinstance(movie.get("contentRating"), str) else "",
		categories=tuple(categories),
	)
	return guide

"""Fetch IMDb rating data for one identity-anchored movie."""

# Standard Library
import re
import json
import math
import datetime
import dataclasses
import html.parser

# PIP3 modules
import imdbinfo.services
import imdbinfo.exceptions

# local repo modules
import slide_maker.http_client


@dataclasses.dataclass(frozen=True, slots=True)
class ImdbRating:
	"""IMDb values used to assemble the shared MovieData contract."""

	imdb_id: str
	title: str
	year: int
	imdb_rating: float
	imdb_votes: int


class ImdbSourceError(RuntimeError):
	"""Raised when IMDb cannot supply required rating data for a movie."""


class JsonLdParser(html.parser.HTMLParser):
	"""Collect JSON-LD script bodies from an IMDb page."""

	def __init__(self) -> None:
		super().__init__()
		self.records: list[str] = []
		self._in_json_ld = False
		self._parts: list[str] = []

	def handle_starttag(self, tag: str, attributes: list[tuple[str, str | None]]) -> None:
		"""Start collecting a JSON-LD script body."""
		attribute_map = dict(attributes)
		if tag == "script" and attribute_map.get("type") == "application/ld+json":
			self._in_json_ld = True
			self._parts = []

	def handle_data(self, data: str) -> None:
		"""Collect text inside the active JSON-LD script."""
		if self._in_json_ld:
			self._parts.append(data)

	def handle_endtag(self, tag: str) -> None:
		"""Finish the active JSON-LD script body."""
		if tag == "script" and self._in_json_ld:
			body = "".join(self._parts)
			self.records.append(body)
			self._in_json_ld = False
			self._parts = []


#============================================
def normalize_imdb_id(imdb_id: str) -> str:
	"""Return a canonical IMDb title id.

	Args:
		imdb_id: IMDb title id with its ``tt`` prefix.

	Returns:
		The stripped, lowercase IMDb title id.

	Raises:
		ValueError: The value is not an IMDb title id.
	"""
	normalized = imdb_id.strip().lower()
	if re.fullmatch(r"tt[0-9]{7,10}", normalized) is None:
		raise ValueError(f"Invalid IMDb title id: {imdb_id!r}")
	return normalized


#============================================
def fetch_imdb_page(url: str) -> object:
	"""Fetch one IMDb page through shared HTTP, solving an HTTP 202 challenge."""
	headers = dict(imdbinfo.services.HEADERS)
	response = slide_maker.http_client.fetch_url(url, headers)
	if response.status_code == 202:
		cookies = imdbinfo.services.get_cookies(
			response.text,
			imdbinfo.services.USER_AGENT,
		)
		headers["Cookie"] = "; ".join(
			f"{name}={value}" for name, value in cookies.items()
		)
		response = slide_maker.http_client.fetch_url(url, headers)
	return response


#============================================
def validate_rating(result: ImdbRating, attempted_url: str) -> ImdbRating:
	"""Validate the identity and required MovieData rating fields."""
	if not result.title.strip() or result.year <= 0:
		raise ImdbSourceError(
			f"IMDb identity fields are missing for {result.imdb_id} at {attempted_url}"
		)
	if not 0.0 <= result.imdb_rating <= 10.0:
		raise ImdbSourceError(
			f"IMDb rating is outside 0-10 for {result.imdb_id} at {attempted_url}"
		)
	if result.imdb_votes <= 0:
		raise ImdbSourceError(
			f"IMDb vote count is missing for {result.imdb_id} at {attempted_url}"
		)
	return result


#============================================
def rating_from_imdbinfo(imdb_id: str, movie: object, attempted_url: str) -> ImdbRating | None:
	"""Convert a complete imdbinfo movie model to the shared rating fields."""
	model_id = getattr(movie, "imdbId")
	model_title = getattr(movie, "title")
	model_year = getattr(movie, "year")
	model_rating = getattr(movie, "rating")
	model_votes = getattr(movie, "votes")
	if model_title is None or model_rating is None or model_votes is None or model_year is None:
		return None
	if model_id != imdb_id:
		raise ImdbSourceError(
			f"IMDb returned identity {model_id!r} for {imdb_id} at {attempted_url}"
		)
	result = ImdbRating(
		imdb_id=imdb_id,
		title=str(model_title),
		year=int(model_year),
		imdb_rating=float(model_rating),
		imdb_votes=int(model_votes),
	)
	validated = validate_rating(result, attempted_url)
	return validated


#============================================
def parse_json_ld(body: str, imdb_id: str, attempted_url: str) -> object:
	"""Decode one JSON-LD body with source context on failure."""
	try:
		parsed = json.loads(body)
	except json.JSONDecodeError as error:
		message = f"IMDb JSON-LD decode failed for {imdb_id} at {attempted_url}: {error.msg}"
		raise ImdbSourceError(message) from error
	return parsed


#============================================
def movie_json_ld(parser: JsonLdParser, imdb_id: str, attempted_url: str) -> dict:
	"""Return the Movie JSON-LD record from an IMDb page."""
	for body in parser.records:
		parsed = parse_json_ld(body, imdb_id, attempted_url)
		if not isinstance(parsed, (dict, list)):
			message = (
				f"IMDb JSON-LD has invalid type {type(parsed).__name__} "
				f"for {imdb_id} at {attempted_url}"
			)
			raise ImdbSourceError(message)
		candidates = parsed if isinstance(parsed, list) else [parsed]
		for candidate in candidates:
			if isinstance(candidate, dict) and candidate.get("@type") == "Movie":
				return candidate
	message = f"IMDb Movie JSON-LD is missing for {imdb_id} at {attempted_url}"
	raise ImdbSourceError(message)


#============================================
def required_json_ld_value(
	record: dict,
	field: str,
	imdb_id: str,
	attempted_url: str,
) -> object:
	"""Return one required JSON-LD field with source context when absent."""
	if field not in record:
		message = f"IMDb JSON-LD field {field!r} is missing for {imdb_id} at {attempted_url}"
		raise ImdbSourceError(message)
	value = record[field]
	return value


#============================================
def json_ld_text(value: object, field: str, imdb_id: str, attempted_url: str) -> str:
	"""Validate one required nonempty JSON-LD text value."""
	if not isinstance(value, str):
		message = (
			f"IMDb JSON-LD field {field!r} has invalid type {type(value).__name__} "
			f"for {imdb_id} at {attempted_url}"
		)
		raise ImdbSourceError(message)
	if not value.strip():
		message = f"IMDb JSON-LD field {field!r} is empty for {imdb_id} at {attempted_url}"
		raise ImdbSourceError(message)
	return value


#============================================
def json_ld_mapping(value: object, field: str, imdb_id: str, attempted_url: str) -> dict:
	"""Validate one required JSON-LD mapping."""
	if not isinstance(value, dict):
		message = (
			f"IMDb JSON-LD field {field!r} has invalid type {type(value).__name__} "
			f"for {imdb_id} at {attempted_url}"
		)
		raise ImdbSourceError(message)
	return value


#============================================
def json_ld_number(value: object, field: str, imdb_id: str, attempted_url: str) -> float:
	"""Validate one finite JSON-LD numeric value before conversion."""
	if isinstance(value, bool) or not isinstance(value, (int, float)):
		message = (
			f"IMDb JSON-LD field {field!r} has invalid type {type(value).__name__} "
			f"for {imdb_id} at {attempted_url}"
		)
		raise ImdbSourceError(message)
	try:
		converted = float(value)
	except OverflowError as error:
		message = f"IMDb JSON-LD field {field!r} is malformed for {imdb_id} at {attempted_url}"
		raise ImdbSourceError(message) from error
	if not math.isfinite(converted):
		message = f"IMDb JSON-LD field {field!r} is malformed for {imdb_id} at {attempted_url}"
		raise ImdbSourceError(message)
	return converted


#============================================
def json_ld_integer(value: object, field: str, imdb_id: str, attempted_url: str) -> int:
	"""Validate one JSON-LD integer value before conversion."""
	if isinstance(value, bool) or not isinstance(value, int):
		message = (
			f"IMDb JSON-LD field {field!r} has invalid type {type(value).__name__} "
			f"for {imdb_id} at {attempted_url}"
		)
		raise ImdbSourceError(message)
	return value


#============================================
def json_ld_year(value: object, imdb_id: str, attempted_url: str) -> int:
	"""Validate an ISO publication date and return its year."""
	date_published = json_ld_text(value, "datePublished", imdb_id, attempted_url)
	try:
		published_date = datetime.date.fromisoformat(date_published)
	except ValueError as error:
		message = f"IMDb JSON-LD datePublished is malformed for {imdb_id} at {attempted_url}"
		raise ImdbSourceError(message) from error
	return published_date.year


#============================================
def rating_from_json_ld(imdb_id: str, attempted_url: str) -> ImdbRating:
	"""Fetch and parse the probe-supported direct-page JSON-LD path."""
	response = fetch_imdb_page(attempted_url)
	if response.status_code != 200:
		raise ImdbSourceError(
			f"IMDb returned HTTP {response.status_code} for {imdb_id} at {attempted_url}"
		)
	if f"/title/{imdb_id}/" not in str(response.url):
		raise ImdbSourceError(
			f"IMDb redirected {imdb_id} from {attempted_url} "
			f"to a different identity at {response.url}"
		)
	parser = JsonLdParser()
	parser.feed(response.text)
	record = movie_json_ld(parser, imdb_id, attempted_url)
	title_value = required_json_ld_value(record, "name", imdb_id, attempted_url)
	date_value = required_json_ld_value(record, "datePublished", imdb_id, attempted_url)
	aggregate_value = required_json_ld_value(record, "aggregateRating", imdb_id, attempted_url)
	title = json_ld_text(title_value, "name", imdb_id, attempted_url)
	year = json_ld_year(date_value, imdb_id, attempted_url)
	aggregate_rating = json_ld_mapping(
		aggregate_value,
		"aggregateRating",
		imdb_id,
		attempted_url,
	)
	rating_value = required_json_ld_value(
		aggregate_rating,
		"ratingValue",
		imdb_id,
		attempted_url,
	)
	vote_value = required_json_ld_value(
		aggregate_rating,
		"ratingCount",
		imdb_id,
		attempted_url,
	)
	rating = json_ld_number(rating_value, "ratingValue", imdb_id, attempted_url)
	votes = json_ld_integer(vote_value, "ratingCount", imdb_id, attempted_url)
	result = ImdbRating(
		imdb_id=imdb_id,
		title=title,
		year=year,
		imdb_rating=rating,
		imdb_votes=votes,
	)
	validated = validate_rating(result, attempted_url)
	return validated


#============================================
def fetch_imdb_ratings(imdb_id: str) -> ImdbRating:
	"""Fetch required IMDb identity, rating, and vote values.

	Args:
		imdb_id: Canonical IMDb title id.

	Returns:
		Identity-bearing rating values aligned with ``MovieData`` field names.

	Raises:
		ValueError: The id is malformed.
		ImdbSourceError: IMDb cannot provide complete, plausible values.
	"""
	normalized_id = normalize_imdb_id(imdb_id)
	reference_url = f"https://www.imdb.com/title/{normalized_id}/reference"
	direct_url = f"https://www.imdb.com/title/{normalized_id}/"
	imdbinfo.services.request_handler = fetch_imdb_page
	movie = None
	try:
		movie = imdbinfo.services.get_movie(normalized_id)
	except imdbinfo.exceptions.ImdbinfoError:
		movie = None
	if movie is not None:
		result = rating_from_imdbinfo(normalized_id, movie, reference_url)
		if result is not None:
			return result
	result = rating_from_json_ld(normalized_id, direct_url)
	return result

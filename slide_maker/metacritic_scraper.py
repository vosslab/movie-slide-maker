"""Fetch Metacritic identity and mandatory Metascore values."""

# Standard Library
import re
import json
import dataclasses
import html.parser
import urllib.parse

# local repo modules
import slide_maker.emoji_marks
import slide_maker.http_client
import slide_maker.movie_identity


METACRITIC_MOVIE_ROOT = "https://www.metacritic.com/movie"
IMDB_ID_PATTERN = re.compile(r"tt[0-9]{7,10}")


class MetacriticSourceError(RuntimeError):
	"""Report an unusable Metacritic result with attempted identity."""


@dataclasses.dataclass(frozen=True, slots=True)
class MetacriticRating:
	"""Identity-bearing Metacritic values aligned with ``MovieData``."""

	imdb_id: str
	title: str
	year: int
	directors: list[str]
	metascore: int
	metascore_band: str
	canonical_url: str


class MetacriticPageParser(html.parser.HTMLParser):
	"""Collect JSON-LD scripts and the canonical URL from one movie page."""

	def __init__(self) -> None:
		super().__init__()
		self.scripts: list[str] = []
		self.canonical_url: str | None = None
		self._script_type: str | None = None
		self._script_parts: list[str] = []

	def handle_starttag(
		self,
		tag: str,
		attributes: list[tuple[str, str | None]],
	) -> None:
		"""Start collecting JSON-LD or record the canonical link."""
		attribute_map = dict(attributes)
		if tag == "script":
			self._script_type = attribute_map.get("type")
			self._script_parts = []
		if tag == "link" and attribute_map.get("rel") == "canonical":
			self.canonical_url = attribute_map.get("href")

	def handle_data(self, data: str) -> None:
		"""Collect text from the active JSON-LD script."""
		if self._script_type == "application/ld+json":
			self._script_parts.append(data)

	def handle_endtag(self, tag: str) -> None:
		"""Finish collecting one JSON-LD script."""
		if tag == "script" and self._script_type is not None:
			if self._script_type == "application/ld+json":
				body = "".join(self._script_parts)
				self.scripts.append(body)
			self._script_type = None
			self._script_parts = []


#============================================
def _source_error(
	title: str,
	year: int,
	imdb_id: str,
	attempted_url: str,
	problem: str,
) -> MetacriticSourceError:
	"""Build a contextual Metacritic source error."""
	identity = f"{title!r} ({year}), IMDb id {imdb_id}"
	message = f"Metacritic source error for {identity} at {attempted_url}: {problem}"
	error = MetacriticSourceError(message)
	return error


#============================================
def _require(
	condition: bool,
	title: str,
	year: int,
	imdb_id: str,
	attempted_url: str,
	problem: str,
) -> None:
	"""Raise a contextual source error when Metacritic data is unusable."""
	if not condition:
		raise _source_error(title, year, imdb_id, attempted_url, problem)


#============================================
def _json_ld_records(
	page: MetacriticPageParser,
	title: str,
	year: int,
	imdb_id: str,
	attempted_url: str,
) -> list[dict]:
	"""Parse mapping records from the page's JSON-LD scripts."""
	records = []
	for body in page.scripts:
		try:
			parsed = json.loads(body)
		except json.JSONDecodeError as error:
			raise _source_error(
				title,
				year,
				imdb_id,
				attempted_url,
				"movie JSON-LD was invalid",
			) from error
		items = parsed if isinstance(parsed, list) else [parsed]
		for item in items:
			if isinstance(item, dict):
				records.append(item)
	return records


#============================================
def _movie_json_ld(
	page: MetacriticPageParser,
	title: str,
	year: int,
	imdb_id: str,
	attempted_url: str,
) -> dict:
	"""Return the required Metacritic movie JSON-LD record."""
	records = _json_ld_records(page, title, year, imdb_id, attempted_url)
	for record in records:
		record_type = record.get("@type")
		if record_type in ("Movie", "CreativeWork") and "name" in record:
			return record
	raise _source_error(title, year, imdb_id, attempted_url, "movie JSON-LD was missing")


#============================================
def _required_value(
	mapping: dict,
	key: str,
	path: str,
	title: str,
	year: int,
	imdb_id: str,
	attempted_url: str,
) -> object:
	"""Return one required JSON-LD value with source context."""
	_require(
		key in mapping,
		title,
		year,
		imdb_id,
		attempted_url,
		f"required page data {path!r} was missing",
	)
	value = mapping[key]
	return value


#============================================
def _required_text(
	value: object,
	path: str,
	title: str,
	year: int,
	imdb_id: str,
	attempted_url: str,
) -> str:
	"""Validate one required nonempty JSON-LD text value."""
	_require(
		isinstance(value, str) and bool(value.strip()),
		title,
		year,
		imdb_id,
		attempted_url,
		f"required page data {path!r} was missing or invalid",
	)
	return value.strip()


#============================================
def _director_names(
	value: object,
	title: str,
	year: int,
	imdb_id: str,
	attempted_url: str,
) -> list[str]:
	"""Validate and return director names from JSON-LD person records."""
	people = value if isinstance(value, list) else [value]
	directors = []
	for person in people:
		_require(
			isinstance(person, dict),
			title,
			year,
			imdb_id,
			attempted_url,
			"director data was malformed",
		)
		name_value = _required_value(
			person,
			"name",
			"director[].name",
			title,
			year,
			imdb_id,
			attempted_url,
		)
		name = _required_text(
			name_value,
			"director[].name",
			title,
			year,
			imdb_id,
			attempted_url,
		)
		directors.append(name)
	_require(
		bool(directors),
		title,
		year,
		imdb_id,
		attempted_url,
		"director data was missing",
	)
	return directors


#============================================
def _canonical_url(
	page: MetacriticPageParser,
	title: str,
	year: int,
	imdb_id: str,
	attempted_url: str,
) -> str:
	"""Validate and return the page's current canonical movie URL."""
	canonical_url = _required_text(
		page.canonical_url,
		"link[rel=canonical].href",
		title,
		year,
		imdb_id,
		attempted_url,
	)
	parsed_url = urllib.parse.urlparse(canonical_url)
	valid_url = (
		parsed_url.scheme == "https"
		and parsed_url.netloc == "www.metacritic.com"
		and parsed_url.path.startswith("/movie/")
	)
	_require(
		valid_url,
		title,
		year,
		imdb_id,
		attempted_url,
		"canonical movie URL was invalid",
	)
	return canonical_url


#============================================
def _metascore(
	record: dict,
	title: str,
	year: int,
	imdb_id: str,
	attempted_url: str,
) -> int:
	"""Validate and return the mandatory Metascore."""
	aggregate_value = _required_value(
		record,
		"aggregateRating",
		"aggregateRating",
		title,
		year,
		imdb_id,
		attempted_url,
	)
	_require(
		isinstance(aggregate_value, dict),
		title,
		year,
		imdb_id,
		attempted_url,
		"Metascore aggregateRating was malformed",
	)
	rating_value = _required_value(
		aggregate_value,
		"ratingValue",
		"aggregateRating.ratingValue",
		title,
		year,
		imdb_id,
		attempted_url,
	)
	valid_score = (
		isinstance(rating_value, int)
		and not isinstance(rating_value, bool)
		or isinstance(rating_value, str) and rating_value.isdigit()
	)
	_require(
		valid_score,
		title,
		year,
		imdb_id,
		attempted_url,
		"Metascore was missing or malformed",
	)
	metascore = int(rating_value)
	_require(
		0 <= metascore <= 100,
		title,
		year,
		imdb_id,
		attempted_url,
		"Metascore was outside 0-100",
	)
	return metascore


#============================================
def fetch_metacritic_rating(
	imdb_id: str,
	metacritic_slug: str,
	expected_title: str,
	expected_year: int,
	expected_directors: list[str],
) -> MetacriticRating:
	"""Fetch an identity-checked Metacritic result.

	Args:
		imdb_id: IMDb id used as the cross-provider identity anchor.
		metacritic_slug: Current canonical Metacritic movie slug.
		expected_title: Title resolved by the upstream TMDB provider.
		expected_year: Release year resolved by the upstream TMDB provider.
		expected_directors: Directors resolved by the upstream TMDB provider.

	Returns:
		The current identity-bearing Metascore and shared display band.

	Raises:
		ValueError: An input identity is malformed or incomplete.
		MetacriticSourceError: The response fails identity or Metascore requirements.
	"""
	normalized_imdb_id = imdb_id.strip().lower()
	if IMDB_ID_PATTERN.fullmatch(normalized_imdb_id) is None:
		raise ValueError(f"Invalid IMDb title id: {imdb_id!r}")
	clean_slug = metacritic_slug.strip().strip("/")
	if not clean_slug:
		raise ValueError("Metacritic movie slug must be nonempty")
	if not expected_title.strip() or expected_year <= 0 or not expected_directors:
		raise ValueError("Metacritic expected identity must be complete")

	url = f"{METACRITIC_MOVIE_ROOT}/{clean_slug}/"
	response = slide_maker.http_client.fetch_url(url)
	attempted_url = str(response.url)
	_require(
		response.status_code == 200,
		expected_title,
		expected_year,
		normalized_imdb_id,
		attempted_url,
		f"HTTP {response.status_code}",
	)
	page = MetacriticPageParser()
	page.feed(response.text)
	record = _movie_json_ld(
		page,
		expected_title,
		expected_year,
		normalized_imdb_id,
		attempted_url,
	)
	title_value = _required_value(
		record,
		"name",
		"name",
		expected_title,
		expected_year,
		normalized_imdb_id,
		attempted_url,
	)
	date_value = _required_value(
		record,
		"datePublished",
		"datePublished",
		expected_title,
		expected_year,
		normalized_imdb_id,
		attempted_url,
	)
	director_value = _required_value(
		record,
		"director",
		"director",
		expected_title,
		expected_year,
		normalized_imdb_id,
		attempted_url,
	)
	title = _required_text(
		title_value,
		"name",
		expected_title,
		expected_year,
		normalized_imdb_id,
		attempted_url,
	)
	date_text = _required_text(
		date_value,
		"datePublished",
		expected_title,
		expected_year,
		normalized_imdb_id,
		attempted_url,
	)
	_require(
		bool(re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", date_text)),
		expected_title,
		expected_year,
		normalized_imdb_id,
		attempted_url,
		"datePublished was malformed",
	)
	year = int(date_text[:4])
	directors = _director_names(
		director_value,
		expected_title,
		expected_year,
		normalized_imdb_id,
		attempted_url,
	)
	matches = slide_maker.movie_identity.count_identity_matches(
		title,
		year,
		directors,
		expected_title,
		expected_year,
		expected_directors,
	)
	_require(
		matches >= 2,
		expected_title,
		expected_year,
		normalized_imdb_id,
		attempted_url,
		"candidate failed two identity attributes",
	)
	canonical_url = _canonical_url(
		page,
		expected_title,
		expected_year,
		normalized_imdb_id,
		attempted_url,
	)
	metascore = _metascore(
		record,
		expected_title,
		expected_year,
		normalized_imdb_id,
		attempted_url,
	)
	result = MetacriticRating(
		imdb_id=normalized_imdb_id,
		title=title,
		year=year,
		directors=directors,
		metascore=metascore,
		metascore_band=slide_maker.emoji_marks.metascore_band_for_score(metascore),
		canonical_url=canonical_url,
	)
	return result

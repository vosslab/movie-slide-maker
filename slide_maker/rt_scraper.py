"""Fetch Rotten Tomatoes identity, Tomatometer, and critics consensus."""

# Standard Library
import re
import json
import dataclasses
import html.parser

# local repo modules
import slide_maker.emoji_marks
import slide_maker.http_client
import slide_maker.movie_identity


RT_MOVIE_ROOT = "https://www.rottentomatoes.com/m"
IMDB_ID_PATTERN = re.compile(r"tt[0-9]{7,10}")


class RtSourceError(RuntimeError):
	"""Report an unusable Rotten Tomatoes result with attempted identity."""


@dataclasses.dataclass(frozen=True, slots=True)
class RtRating:
	"""Identity-bearing Rotten Tomatoes values aligned with ``MovieData``."""

	imdb_id: str
	title: str
	year: int
	directors: list[str]
	rt_tomatometer: int
	rt_state: str
	rt_consensus: str
	canonical_url: str


class RtPageParser(html.parser.HTMLParser):
	"""Collect the structured scripts and critics consensus from one RT page."""

	def __init__(self) -> None:
		super().__init__()
		self.scripts: list[tuple[dict[str, str | None], str]] = []
		self.consensus: str | None = None
		self._script_attributes: dict[str, str | None] | None = None
		self._script_parts: list[str] = []
		self._saw_consensus_label = False
		self._in_consensus = False
		self._consensus_parts: list[str] = []

	def handle_starttag(
		self,
		tag: str,
		attributes: list[tuple[str, str | None]],
	) -> None:
		"""Start collecting a structured script or critics-consensus paragraph."""
		if tag == "script":
			self._script_attributes = dict(attributes)
			self._script_parts = []
		if tag == "p" and self._saw_consensus_label:
			self._in_consensus = True
			self._consensus_parts = []

	def handle_data(self, data: str) -> None:
		"""Collect text for the active script or critics consensus."""
		if self._script_attributes is not None:
			self._script_parts.append(data)
		if data.strip().casefold() == "critics consensus":
			self._saw_consensus_label = True
		if self._in_consensus:
			self._consensus_parts.append(data)

	def handle_endtag(self, tag: str) -> None:
		"""Finish an active script or critics-consensus paragraph."""
		if tag == "script" and self._script_attributes is not None:
			body = "".join(self._script_parts)
			self.scripts.append((self._script_attributes, body))
			self._script_attributes = None
			self._script_parts = []
		if tag == "p" and self._in_consensus:
			consensus = " ".join("".join(self._consensus_parts).split())
			self.consensus = consensus
			self._in_consensus = False
			self._saw_consensus_label = False


#============================================
def _source_error(identity: str, attempted: str, problem: str) -> RtSourceError:
	"""Build a contextual Rotten Tomatoes source error."""
	message = f"Rotten Tomatoes source error for {identity} at {attempted}: {problem}"
	error = RtSourceError(message)
	return error


#============================================
def _require(condition: bool, identity: str, attempted: str, problem: str) -> None:
	"""Raise a contextual source error when an RT response is unusable."""
	if not condition:
		raise _source_error(identity, attempted, problem)


#============================================
def _page_json(
	page: RtPageParser,
	attribute: str,
	value: str,
	identity: str,
	attempted: str,
) -> dict:
	"""Return the required JSON object selected by one script attribute."""
	for attributes, body in page.scripts:
		if attributes.get(attribute) == value:
			try:
				parsed = json.loads(body)
			except json.JSONDecodeError as error:
				raise _source_error(identity, attempted, f"{value} was invalid JSON") from error
			_require(isinstance(parsed, dict), identity, attempted, f"{value} was not an object")
			return parsed
	raise _source_error(identity, attempted, f"required page data {value!r} was missing")


#============================================
def _required_value(
	mapping: dict,
	key: str,
	path: str,
	identity: str,
	attempted: str,
) -> object:
	"""Return one required mapping value with source context."""
	_require(key in mapping, identity, attempted, f"required page data {path!r} was missing")
	value = mapping[key]
	return value


#============================================
def _required_mapping(
	mapping: dict,
	key: str,
	path: str,
	identity: str,
	attempted: str,
) -> dict:
	"""Return one required nested mapping with source context."""
	value = _required_value(mapping, key, path, identity, attempted)
	_require(isinstance(value, dict), identity, attempted, f"{path} was not an object")
	return value


#============================================
def fetch_rt_rating(
	imdb_id: str,
	rt_slug: str,
	expected_title: str,
	expected_year: int,
	expected_directors: list[str],
) -> RtRating:
	"""Fetch an identity-checked Rotten Tomatoes critics result.

	Args:
		imdb_id: IMDb id used as the cross-provider identity anchor.
		rt_slug: Current canonical Rotten Tomatoes movie slug.
		expected_title: Title resolved by the upstream TMDB provider.
		expected_year: Release year resolved by the upstream TMDB provider.
		expected_directors: Directors resolved by the upstream TMDB provider.

	Returns:
		The current identity-bearing Tomatometer values and critics consensus.

	Raises:
		ValueError: An input identity is malformed or incomplete.
		RtSourceError: The response fails identity, score, or consensus requirements.
	"""
	normalized_imdb_id = imdb_id.strip().lower()
	if IMDB_ID_PATTERN.fullmatch(normalized_imdb_id) is None:
		raise ValueError(f"Invalid IMDb title id: {imdb_id!r}")
	clean_slug = rt_slug.strip().strip("/")
	if not clean_slug:
		raise ValueError("Rotten Tomatoes movie slug must be nonempty")
	if not expected_title.strip() or expected_year <= 0 or not expected_directors:
		raise ValueError("Rotten Tomatoes expected identity must be complete")

	identity = f"{expected_title.strip()!r} ({expected_year}), IMDb id {normalized_imdb_id}"
	url = f"{RT_MOVIE_ROOT}/{clean_slug}"
	response = slide_maker.http_client.fetch_url(url)
	attempted = str(response.url)
	_require(response.status_code == 200, identity, attempted, f"HTTP {response.status_code}")
	page = RtPageParser()
	page.feed(response.text)
	vanity = _page_json(page, "data-json", "vanity", identity, attempted)
	scorecard = _page_json(page, "id", "media-scorecard-json", identity, attempted)
	watch_data = _page_json(page, "id", "where-to-watch-json", identity, attempted)

	title = _required_value(vanity, "title", "vanity.title", identity, attempted)
	lifecycle = _required_mapping(
		vanity,
		"lifecycleWindow",
		"vanity.lifecycleWindow",
		identity,
		attempted,
	)
	date_text = _required_value(
		lifecycle,
		"date",
		"vanity.lifecycleWindow.date",
		identity,
		attempted,
	)
	director = _required_value(
		watch_data,
		"director",
		"where-to-watch-json.director",
		identity,
		attempted,
	)
	_require(isinstance(title, str) and bool(title.strip()), identity, attempted, "title was missing")
	_require(
		isinstance(date_text, str) and bool(re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", date_text)),
		identity,
		attempted,
		"release date was missing or invalid",
	)
	_require(
		isinstance(director, str) and bool(director.strip()),
		identity,
		attempted,
		"director was missing",
	)
	year = int(date_text[:4])
	directors = [director]
	matches = slide_maker.movie_identity.count_identity_matches(
		title,
		year,
		directors,
		expected_title,
		expected_year,
		expected_directors,
	)
	_require(matches >= 2, identity, attempted, "candidate failed two identity attributes")

	critics_data = _required_mapping(
		scorecard,
		"criticsScore",
		"media-scorecard-json.criticsScore",
		identity,
		attempted,
	)
	critics_score = _required_value(
		critics_data,
		"score",
		"media-scorecard-json.criticsScore.score",
		identity,
		attempted,
	)
	_require(
		isinstance(critics_score, (str, int)) and str(critics_score).isdigit(),
		identity,
		attempted,
		"Tomatometer was missing or invalid",
	)
	tomatometer = int(critics_score)
	_require(0 <= tomatometer <= 100, identity, attempted, "Tomatometer was outside 0-100")
	_require(
		page.consensus is not None and bool(page.consensus.strip()),
		identity,
		attempted,
		"critics consensus was missing",
	)
	result = RtRating(
		imdb_id=normalized_imdb_id,
		title=title,
		year=year,
		directors=directors,
		rt_tomatometer=tomatometer,
		rt_state=slide_maker.emoji_marks.rt_state_for_score(tomatometer),
		rt_consensus=page.consensus,
		canonical_url=attempted,
	)
	return result

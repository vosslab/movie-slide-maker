"""Fetch Rotten Tomatoes identity, critic, audience, and consensus values."""

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

	imdb_id: str | None = None
	title: str | None = None
	year: int | None = None
	directors: list[str] = dataclasses.field(default_factory=list)
	rt_tomatometer: int | None = None
	rt_audience_score: int | None = None
	rt_state: str | None = None
	rt_consensus: str = ""
	canonical_url: str | None = None


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
	required: bool,
) -> dict | None:
	"""Return one structured page object when it is present and valid."""
	for attributes, body in page.scripts:
		if attributes.get(attribute) == value:
			try:
				parsed = json.loads(body)
			except json.JSONDecodeError as error:
				if required:
					raise _source_error(identity, attempted, f"{value} was invalid JSON") from error
				return None
			if not isinstance(parsed, dict):
				if required:
					raise _source_error(identity, attempted, f"{value} was not an object")
				return None
			return parsed
	if required:
		raise _source_error(identity, attempted, f"required page data {value!r} was missing")
	return None


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
def _optional_audience_score(
	scorecard: dict,
) -> int | None:
	"""Return the optional Popcornmeter score when Rotten Tomatoes publishes it."""
	if "audienceScore" not in scorecard or scorecard["audienceScore"] is None:
		return None
	audience_data = scorecard["audienceScore"]
	if not isinstance(audience_data, dict):
		return None
	if "score" not in audience_data or audience_data["score"] is None:
		return None
	score_value = audience_data["score"]
	if not isinstance(score_value, (str, int)) or not str(score_value).isdigit():
		return None
	audience_score = int(score_value)
	if not 0 <= audience_score <= 100:
		return None
	return audience_score


#============================================
def fetch_rt_rating(
	imdb_id: str | None,
	rt_slug: str,
	expected_title: str,
	expected_year: int | None,
	expected_directors: list[str],
) -> RtRating:
	"""Fetch identity-checked Rotten Tomatoes critic and audience values.

	Args:
		imdb_id: IMDb id used as the cross-provider identity anchor.
		rt_slug: Current canonical Rotten Tomatoes movie slug.
		expected_title: Title resolved by the upstream TMDB provider.
		expected_year: Release year resolved by the upstream TMDB provider.
		expected_directors: Directors resolved by the upstream TMDB provider.

	Returns:
		The current identity-bearing Tomatometer, optional Popcornmeter, and
		critics consensus.

	Raises:
		ValueError: An input identity is malformed or incomplete.
		RtSourceError: The response fails identity or score requirements.
	"""
	normalized_imdb_id = imdb_id.strip().lower() if isinstance(imdb_id, str) else None
	if normalized_imdb_id is not None and IMDB_ID_PATTERN.fullmatch(normalized_imdb_id) is None:
		raise ValueError(f"Invalid IMDb title id: {imdb_id!r}")
	clean_slug = rt_slug.strip().strip("/")
	if not clean_slug:
		raise ValueError("Rotten Tomatoes movie slug must be nonempty")
	if not expected_title.strip():
		raise ValueError("Rotten Tomatoes expected title must be nonempty")

	identity = f"{expected_title.strip()!r} ({expected_year}), IMDb id {normalized_imdb_id}"
	url = f"{RT_MOVIE_ROOT}/{clean_slug}"
	try:
		response = slide_maker.http_client.fetch_url(url)
	except slide_maker.http_client.HttpSourceError as error:
		raise _source_error(identity, url, "network request failed") from error
	attempted = str(response.url)
	_require(response.status_code == 200, identity, attempted, f"HTTP {response.status_code}")
	page = RtPageParser()
	page.feed(response.text)
	vanity = _page_json(page, "data-json", "vanity", identity, attempted, True)
	scorecard = _page_json(page, "id", "media-scorecard-json", identity, attempted, False)
	metadata = _page_json(page, "type", "application/ld+json", identity, attempted, True)

	# The required calls above establish mappings for identity-bearing page data.
	title = _required_value(vanity, "title", "vanity.title", identity, attempted)
	lifecycle = vanity.get("lifecycleWindow")
	date_text = lifecycle.get("date") if isinstance(lifecycle, dict) else None
	director_records = metadata.get("director")
	_require(isinstance(title, str) and bool(title.strip()), identity, attempted, "title was missing")
	if not isinstance(date_text, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", date_text) is None:
		date_text = None
	directors = []
	if isinstance(director_records, list):
		for record in director_records:
			if isinstance(record, dict):
				name = record.get("name")
				if isinstance(name, str) and name.strip():
					directors.append(name.strip())
	year = int(date_text[:4]) if date_text is not None else None
	matches = slide_maker.movie_identity.count_identity_matches(
		title,
		year,
		directors,
		expected_title,
		expected_year,
		expected_directors,
	)
	_require(matches >= 2, identity, attempted, "candidate failed two identity attributes")

	critics_data = scorecard.get("criticsScore") if scorecard is not None else None
	critics_score = critics_data.get("score") if isinstance(critics_data, dict) else None
	tomatometer = None
	if isinstance(critics_score, (str, int)) and str(critics_score).isdigit():
		candidate_score = int(critics_score)
		if 0 <= candidate_score <= 100:
			tomatometer = candidate_score
	audience_score = _optional_audience_score(scorecard) if scorecard is not None else None
	result = RtRating(
		imdb_id=normalized_imdb_id,
		title=title,
		year=year,
		directors=directors,
		rt_tomatometer=tomatometer,
		rt_audience_score=audience_score,
		rt_state=slide_maker.emoji_marks.rt_state_for_score(tomatometer)
		if tomatometer is not None
		else None,
		rt_consensus=page.consensus if page.consensus is not None else "",
		canonical_url=attempted,
	)
	return result

"""Classify interactive movie input without provider or network access."""

# Standard Library
import re
import enum
import dataclasses


class InputKind(enum.StrEnum):
	"""Supported movie input categories."""

	IMDB = "imdb_id"
	TMDB = "tmdb_id"
	TITLE = "title"


@dataclasses.dataclass(frozen=True, slots=True)
class MovieInput:
	"""Normalized input for the movie resolver."""

	kind: InputKind
	value: str
	year: int | None


IMDB_ID_PATTERN = re.compile(r"^(tt[0-9]+)$", re.IGNORECASE)
IMDB_URL_PATTERN = re.compile(
	r"^https?://(?:www\.|m\.)?imdb\.com/title/(tt[0-9]+)(?:[/?#].*)?$",
	re.IGNORECASE,
)
TMDB_PREFIX_PATTERN = re.compile(r"^tmdb:\s*([0-9]+)$", re.IGNORECASE)
TMDB_URL_PATTERN = re.compile(
	r"^https?://(?:www\.)?themoviedb\.org/movie/([0-9]+)(?:-[^/?#]*)?(?:[/?#].*)?$",
	re.IGNORECASE,
)
PARENTHESIZED_YEAR_PATTERN = re.compile(r"^(.+?)\s+\(([0-9]{4})\)$")
SLASH_YEAR_PATTERN = re.compile(r"^(.+?)\s*/\s*([0-9]{4})$")
TRAILING_YEAR_PATTERN = re.compile(r"^(.+?)\s+([0-9]{4})$")
MINIMUM_MOVIE_YEAR = 1801
MAXIMUM_MOVIE_YEAR = 2999


#============================================
def _title_with_year(match: re.Match[str]) -> MovieInput | None:
	"""Return a classified plausible title-year match, if present."""
	title = match.group(1).strip()
	year = int(match.group(2))
	if not title or not MINIMUM_MOVIE_YEAR <= year <= MAXIMUM_MOVIE_YEAR:
		return None
	movie_input = MovieInput(InputKind.TITLE, title, year)
	return movie_input


#============================================
def classify_movie_input(raw_input: str) -> MovieInput:
	"""Classify and normalize one interactive movie input.

	Args:
		raw_input: User-entered title, provider identifier, or provider URL.

	Returns:
		A normalized input with its category and optional release year.
	"""
	text = raw_input.strip()
	if not text:
		raise ValueError("Movie input must include a title or provider identifier")

	imdb_match = IMDB_ID_PATTERN.fullmatch(text)
	if imdb_match is None:
		imdb_match = IMDB_URL_PATTERN.fullmatch(text)
	if imdb_match is not None:
		movie_input = MovieInput(InputKind.IMDB, imdb_match.group(1).lower(), None)
		return movie_input

	tmdb_match = TMDB_PREFIX_PATTERN.fullmatch(text)
	if tmdb_match is None:
		tmdb_match = TMDB_URL_PATTERN.fullmatch(text)
	if tmdb_match is not None:
		movie_input = MovieInput(InputKind.TMDB, tmdb_match.group(1), None)
		return movie_input

	title_match = PARENTHESIZED_YEAR_PATTERN.fullmatch(text)
	if title_match is not None:
		movie_input = _title_with_year(title_match)
		if movie_input is not None:
			return movie_input

	title_match = SLASH_YEAR_PATTERN.fullmatch(text)
	if title_match is not None:
		movie_input = _title_with_year(title_match)
		if movie_input is not None:
			return movie_input

	# A four-digit value is a movie title when it is the complete input.
	title_match = TRAILING_YEAR_PATTERN.fullmatch(text)
	if title_match is not None:
		movie_input = _title_with_year(title_match)
		if movie_input is not None:
			return movie_input

	movie_input = MovieInput(InputKind.TITLE, text, None)
	return movie_input

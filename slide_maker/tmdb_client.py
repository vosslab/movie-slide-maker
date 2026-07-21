"""Fetch TMDB identity, movie details, credits, and posters."""

# Standard Library
import re
import json
import pathlib
import dataclasses

# local repo modules
import slide_maker.config
import slide_maker.http_client


TMDB_API_ROOT = "https://api.themoviedb.org/3"
TMDB_IMAGE_ROOT = "https://image.tmdb.org/t/p/original"
IMDB_ID_PATTERN = re.compile(r"tt[0-9]+")


class TmdbSourceError(RuntimeError):
	"""Report a TMDB failure with the attempted movie identity."""


@dataclasses.dataclass(frozen=True)
class TmdbSearchResult:
	"""One movie candidate returned by TMDB search."""

	tmdb_id: int
	title: str
	year: int | None


@dataclasses.dataclass(frozen=True)
class TmdbMovie:
	"""TMDB-owned values that map directly into ``moviedata.MovieData``."""

	title: str
	year: int
	plot: str
	genres: list[str]
	runtime_minutes: int
	directors: list[str]
	tmdb_id: int
	imdb_id: str
	poster_path: str


#============================================
def _source_error(identity: str, attempted: str, problem: str) -> TmdbSourceError:
	"""Build a source-specific error with identity and attempted location."""
	message = f"TMDB source error for {identity} at {attempted}: {problem}"
	error = TmdbSourceError(message)
	return error


#============================================
def _require(condition: bool, identity: str, attempted: str, problem: str) -> None:
	"""Raise a contextual source error when a TMDB response is unusable."""
	if not condition:
		raise _source_error(identity, attempted, problem)


#============================================
def _required_value(data: dict, key: str, identity: str, attempted: str) -> object:
	"""Return a required response value with a contextual missing-key error."""
	_require(key in data, identity, attempted, f"required field {key!r} was missing")
	value = data[key]
	return value


#============================================
def _fetch_json(
	url: str,
	token: str,
	params: dict[str, str | int] | None,
	identity: str,
) -> tuple[dict, str]:
	"""Fetch one authenticated TMDB JSON object through the shared HTTP policy."""
	headers = {
		"Accept": "application/json",
		"Authorization": f"Bearer {token}",
	}
	response = slide_maker.http_client.fetch_url(url, headers, params)
	attempted = str(response.url)
	_require(response.status_code == 200, identity, attempted, f"HTTP {response.status_code}")
	try:
		data = json.loads(response.text)
	except json.JSONDecodeError as error:
		raise _source_error(identity, attempted, "response was not valid JSON") from error
	_require(isinstance(data, dict), identity, attempted, "response root was not an object")
	return data, attempted


#============================================
def _release_year(
	release_date: object,
	identity: str,
	attempted: str,
	required: bool,
) -> int | None:
	"""Parse the year component of a TMDB release date."""
	if release_date in (None, "") and not required:
		return None
	valid_date = isinstance(release_date, str) and re.fullmatch(
		r"[0-9]{4}-[0-9]{2}-[0-9]{2}",
		release_date,
	)
	_require(bool(valid_date), identity, attempted, "release_date was missing or invalid")
	year = int(release_date[:4])
	return year


#============================================
def search_movies(title: str, year: int | None = None) -> list[TmdbSearchResult]:
	"""Search TMDB for movie candidates by title and optional release year.

	Args:
		title: Movie title sent to TMDB after surrounding whitespace is removed.
		year: Optional positive release year used to narrow the search.

	Returns:
		Identity-bearing candidates in TMDB response order.

	Raises:
		ValueError: The title is empty or the optional year is not positive.
		TmdbSourceError: The authenticated request or response contract fails.

	Note:
		This function reads the configured TMDB token and performs one network request.
	"""
	query = title.strip()
	if not query:
		raise ValueError("TMDB movie title must be nonempty")
	if year is not None and year <= 0:
		raise ValueError("TMDB movie year must be positive")

	params: dict[str, str | int] = {"language": "en-US", "query": query}
	if year is not None:
		params["year"] = year
	identity = f"title {query!r}"
	data, attempted = _fetch_json(
		f"{TMDB_API_ROOT}/search/movie",
		slide_maker.config.load(),
		params,
		identity,
	)
	results_data = _required_value(data, "results", identity, attempted)
	_require(isinstance(results_data, list), identity, attempted, "results was not a list")

	results: list[TmdbSearchResult] = []
	for item in results_data:
		_require(isinstance(item, dict), identity, attempted, "a search result was not an object")
		tmdb_id = _required_value(item, "id", identity, attempted)
		result_title = _required_value(item, "title", identity, attempted)
		_require(type(tmdb_id) is int and tmdb_id > 0, identity, attempted, "id was invalid")
		_require(
			isinstance(result_title, str) and bool(result_title.strip()),
			identity,
			attempted,
			"title was missing",
		)
		release_date = _required_value(item, "release_date", identity, attempted)
		result_year = _release_year(release_date, identity, attempted, False)
		result = TmdbSearchResult(tmdb_id, result_title, result_year)
		results.append(result)
	return results


#============================================
def find_tmdb_id_by_imdb_id(imdb_id: str) -> int:
	"""Resolve a normalized IMDb id through TMDB's external-id cross-map.

	Args:
		imdb_id: IMDb title id in ``tt``-prefixed numeric form.

	Returns:
		The positive TMDB movie id for the first movie result.

	Raises:
		ValueError: The IMDb id is malformed.
		TmdbSourceError: The authenticated request, response, or mapping fails.

	Note:
		This function reads the configured TMDB token and performs one network request.
	"""
	normalized_id = imdb_id.strip().lower()
	if IMDB_ID_PATTERN.fullmatch(normalized_id) is None:
		raise ValueError(f"Invalid IMDb id: {imdb_id!r}")
	identity = f"IMDb id {normalized_id}"
	data, attempted = _fetch_json(
		f"{TMDB_API_ROOT}/find/{normalized_id}",
		slide_maker.config.load(),
		{"external_source": "imdb_id"},
		identity,
	)
	movie_results = _required_value(data, "movie_results", identity, attempted)
	_require(isinstance(movie_results, list), identity, attempted, "movie_results was not a list")
	_require(bool(movie_results), identity, attempted, "no matching movie was found")
	first_result = movie_results[0]
	_require(isinstance(first_result, dict), identity, attempted, "movie result was not an object")
	tmdb_id = _required_value(first_result, "id", identity, attempted)
	_require(type(tmdb_id) is int and tmdb_id > 0, identity, attempted, "id was invalid")
	return tmdb_id


#============================================
def _download_poster(
	tmdb_id: int,
	remote_path: str,
	poster_directory: str | pathlib.Path,
	identity: str,
) -> str:
	"""Download the original TMDB poster into the requested directory."""
	url = f"{TMDB_IMAGE_ROOT}{remote_path}"
	suffix = pathlib.PurePosixPath(remote_path).suffix
	_require(bool(suffix), identity, url, "poster path had no file extension")
	response = slide_maker.http_client.fetch_url(url, {"Accept": "image/*"})
	attempted = str(response.url)
	_require(response.status_code == 200, identity, attempted, f"HTTP {response.status_code}")
	_require(bool(response.content), identity, attempted, "poster response was empty")

	output_directory = pathlib.Path(poster_directory)
	output_directory.mkdir(parents=True, exist_ok=True)
	output_path = output_directory / f"tmdb_{tmdb_id}_poster{suffix}"
	output_path.write_bytes(response.content)
	return str(output_path)


#============================================
def fetch_movie(tmdb_id: int, poster_directory: str | pathlib.Path) -> TmdbMovie:
	"""Fetch TMDB details, credits, cross-provider id, and the original poster.

	Args:
		tmdb_id: Positive TMDB movie id to fetch.
		poster_directory: Directory that will receive the downloaded poster file.

	Returns:
		Validated TMDB-owned movie data with the local poster path.

	Raises:
		ValueError: The TMDB id is not positive.
		TmdbSourceError: A request, response field, identity, or poster is invalid.

	Note:
		This function performs movie-detail and poster network requests, reads the
		configured TMDB token, creates ``poster_directory``, and writes the poster.
	"""
	if tmdb_id <= 0:
		raise ValueError("TMDB id must be positive")
	identity = f"TMDB id {tmdb_id}"
	params = {
		"append_to_response": "credits,external_ids",
		"language": "en-US",
	}
	data, attempted = _fetch_json(
		f"{TMDB_API_ROOT}/movie/{tmdb_id}",
		slide_maker.config.load(),
		params,
		identity,
	)

	returned_id = _required_value(data, "id", identity, attempted)
	title = _required_value(data, "title", identity, attempted)
	plot = _required_value(data, "overview", identity, attempted)
	runtime_minutes = _required_value(data, "runtime", identity, attempted)
	genres_data = _required_value(data, "genres", identity, attempted)
	credits = _required_value(data, "credits", identity, attempted)
	external_ids = _required_value(data, "external_ids", identity, attempted)
	remote_poster_path = _required_value(data, "poster_path", identity, attempted)
	_require(returned_id == tmdb_id, identity, attempted, "returned id did not match")
	_require(isinstance(title, str) and bool(title.strip()), identity, attempted, "title was missing")
	_require(isinstance(plot, str) and bool(plot.strip()), identity, attempted, "overview was missing")
	_require(
		type(runtime_minutes) is int and runtime_minutes > 0,
		identity,
		attempted,
		"runtime was missing or invalid",
	)
	_require(
		isinstance(genres_data, list) and bool(genres_data),
		identity,
		attempted,
		"genres were missing",
	)
	_require(isinstance(credits, dict), identity, attempted, "credits was not an object")
	_require(isinstance(external_ids, dict), identity, attempted, "external_ids was not an object")
	_require(
		isinstance(remote_poster_path, str) and bool(remote_poster_path.strip()),
		identity,
		attempted,
		"poster_path was missing",
	)

	_require(
		all(isinstance(genre, dict) for genre in genres_data),
		identity,
		attempted,
		"a genre was not an object",
	)
	genres = [
		_required_value(genre, "name", identity, attempted)
		for genre in genres_data
	]
	crew = _required_value(credits, "crew", identity, attempted)
	_require(isinstance(crew, list), identity, attempted, "credits crew was not a list")
	_require(
		all(isinstance(person, dict) for person in crew),
		identity,
		attempted,
		"a credits crew member was not an object",
	)
	directors = [
		_required_value(person, "name", identity, attempted)
		for person in crew
		if _required_value(person, "job", identity, attempted) == "Director"
	]
	imdb_id = _required_value(external_ids, "imdb_id", identity, attempted)
	_require(
		bool(genres) and all(isinstance(genre, str) and genre.strip() for genre in genres),
		identity,
		attempted,
		"genre names were missing",
	)
	_require(
		bool(directors) and all(isinstance(director, str) and director.strip() for director in directors),
		identity,
		attempted,
		"director names were missing",
	)
	_require(
		isinstance(imdb_id, str) and IMDB_ID_PATTERN.fullmatch(imdb_id) is not None,
		identity,
		attempted,
		"IMDb cross-provider id was missing or invalid",
	)
	release_date = _required_value(data, "release_date", identity, attempted)
	year = _release_year(release_date, identity, attempted, True)
	_require(year is not None, identity, attempted, "release year was missing")
	poster_path = _download_poster(tmdb_id, remote_poster_path, poster_directory, identity)

	movie = TmdbMovie(
		title=title.strip(),
		year=year,
		plot=plot.strip(),
		genres=genres,
		runtime_minutes=runtime_minutes,
		directors=directors,
		tmdb_id=returned_id,
		imdb_id=imdb_id,
		poster_path=poster_path,
	)
	return movie

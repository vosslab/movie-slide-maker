"""Fetch TMDB identity, movie details, credits, and posters."""

# Standard Library
import re
import io
import json
import pathlib
import dataclasses

# PIP3 modules
import PIL.Image

# local repo modules
import slide_maker.config
import slide_maker.http_client


TMDB_API_ROOT = "https://api.themoviedb.org/3"
TMDB_IMAGE_ROOT = "https://image.tmdb.org/t/p/original"
IMDB_ID_PATTERN = re.compile(r"tt[0-9]+")
POSTER_PATH_PATTERN = re.compile(r"/[A-Za-z0-9_-]+\.(?:jpg|jpeg|png|webp)", re.IGNORECASE)


class TmdbSourceError(RuntimeError):
	"""Report a TMDB failure with the attempted movie identity."""


@dataclasses.dataclass(frozen=True)
class TmdbSearchResult:
	"""One movie candidate returned by TMDB search."""

	tmdb_id: int
	title: str
	year: int | None
	overview: str


@dataclasses.dataclass(frozen=True)
class TmdbMovie:
	"""TMDB-owned values that map directly into ``moviedata.MovieData``."""

	title: str
	year: int | None = None
	plot: str = ""
	genres: list[str] = dataclasses.field(default_factory=list)
	runtime_minutes: int | None = None
	directors: list[str] = dataclasses.field(default_factory=list)
	tmdb_id: int | None = None
	imdb_id: str | None = None
	poster_path: str | None = None
	original_language: str | None = None


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
	try:
		response = slide_maker.http_client.fetch_url(url, headers, params)
	except slide_maker.http_client.HttpSourceError as error:
		raise _source_error(identity, url, "network request failed") from error
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
	if not valid_date and not required:
		return None
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
		result_overview = _required_value(item, "overview", identity, attempted)
		_require(type(tmdb_id) is int and tmdb_id > 0, identity, attempted, "id was invalid")
		_require(
			isinstance(result_title, str) and bool(result_title.strip()),
			identity,
			attempted,
			"title was missing",
		)
		_require(
			isinstance(result_overview, str),
			identity,
			attempted,
			"overview was invalid",
		)
		release_date = _required_value(item, "release_date", identity, attempted)
		result_year = _release_year(release_date, identity, attempted, False)
		result = TmdbSearchResult(tmdb_id, result_title, result_year, result_overview)
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
) -> tuple[str | None, str | None]:
	"""Download a decodable original TMDB poster with an absence diagnostic."""
	# ASVS 5.3.2: image metadata may name a file, never an arbitrary URL or output path.
	if POSTER_PATH_PATTERN.fullmatch(remote_path) is None:
		return None, "poster path was not a supported TMDB image path"
	url = f"{TMDB_IMAGE_ROOT}{remote_path}"
	suffix = pathlib.PurePosixPath(remote_path).suffix
	try:
		response = slide_maker.http_client.fetch_url(url, {"Accept": "image/*"})
	except slide_maker.http_client.HttpSourceError:
		return None, "poster download failed"
	if response.status_code != 200 or not response.content:
		return None, f"poster download returned HTTP {response.status_code}"
	try:
		with PIL.Image.open(io.BytesIO(response.content)) as image:
			image.verify()
	except (PIL.UnidentifiedImageError, OSError):
		return None, "poster data was not a decodable image"

	output_directory = pathlib.Path(poster_directory)
	output_directory.mkdir(parents=True, exist_ok=True)
	output_path = output_directory / f"tmdb_{tmdb_id}_poster{suffix}"
	output_path.write_bytes(response.content)
	return str(output_path), None


#============================================
def _fetch_poster(
	tmdb_id: int,
	primary_path: str | None,
	poster_directory: str | pathlib.Path,
	token: str,
	identity: str,
) -> str:
	"""Recover from a missing or broken primary poster using this movie's images."""
	problem = "TMDB did not provide a primary poster"
	if primary_path is not None:
		poster_path, problem = _download_poster(tmdb_id, primary_path, poster_directory)
		if poster_path is not None:
			return poster_path
	images_url = f"{TMDB_API_ROOT}/movie/{tmdb_id}/images"
	images, attempted = _fetch_json(images_url, token, None, identity)
	_require(images.get("id") == tmdb_id, identity, attempted, "poster images returned a different id")
	posters = images.get("posters")
	_require(isinstance(posters, list), identity, attempted, "poster images were not a list")
	tried = {primary_path}
	for poster in posters:
		if not isinstance(poster, dict):
			continue
		remote_path = _optional_text(poster, "file_path")
		if remote_path is None or remote_path in tried:
			continue
		tried.add(remote_path)
		poster_path, problem = _download_poster(tmdb_id, remote_path, poster_directory)
		if poster_path is not None:
			return poster_path
	raise _source_error(identity, images_url, f"poster retrieval failed: {problem}")


#============================================
def _optional_text(data: dict, key: str) -> str | None:
	"""Return a stripped optional text field when TMDB supplied one."""
	value = data.get(key)
	if isinstance(value, str) and value.strip():
		return value.strip()
	return None


#============================================
def _optional_year(data: dict, identity: str, attempted: str) -> int | None:
	"""Return a valid optional TMDB release year."""
	release_date = data.get("release_date")
	if release_date in (None, ""):
		return None
	return _release_year(release_date, identity, attempted, False)


#============================================
def _optional_names(records: object, key: str) -> list[str]:
	"""Extract nonempty names from optional TMDB object records."""
	if not isinstance(records, list):
		return []
	names = []
	for record in records:
		if isinstance(record, dict):
			name = _optional_text(record, key)
			if name is not None:
				names.append(name)
	return names


#============================================
def _original_language_name(
	data: dict,
	token: str,
) -> str | None:
	"""Resolve TMDB's original-language code to one display language name."""
	code = _optional_text(data, "original_language")
	if code is None:
		return None
	spoken_languages = data.get("spoken_languages")
	if isinstance(spoken_languages, list):
		for language in spoken_languages:
			if not isinstance(language, dict):
				continue
			if language.get("iso_639_1") == code:
				name = _optional_text(language, "english_name")
				if name is not None:
					return name
	url = f"{TMDB_API_ROOT}/configuration/languages"
	headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
	try:
		response = slide_maker.http_client.fetch_url(url, headers)
	except slide_maker.http_client.HttpSourceError:
		return None
	if response.status_code != 200:
		return None
	try:
		language_records = json.loads(response.text)
	except json.JSONDecodeError:
		return None
	if isinstance(language_records, list):
		for language in language_records:
			if isinstance(language, dict) and language.get("iso_639_1") == code:
				name = _optional_text(language, "english_name")
				return name
	return None


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
	token = slide_maker.config.load()
	data, attempted = _fetch_json(
		f"{TMDB_API_ROOT}/movie/{tmdb_id}",
		token,
		params,
		identity,
	)

	returned_id = _required_value(data, "id", identity, attempted)
	title = _required_value(data, "title", identity, attempted)
	_require(returned_id == tmdb_id, identity, attempted, "returned id did not match")
	_require(isinstance(title, str) and bool(title.strip()), identity, attempted, "title was missing")
	year = _optional_year(data, identity, attempted)
	plot = _optional_text(data, "overview")
	genres = _optional_names(data.get("genres"), "name")
	runtime_value = data.get("runtime")
	runtime_minutes = runtime_value if type(runtime_value) is int and runtime_value > 0 else None
	credits = data.get("credits")
	crew = credits.get("crew") if isinstance(credits, dict) else None
	directors = []
	if isinstance(crew, list):
		directors = _optional_names(
			[person for person in crew if isinstance(person, dict) and person.get("job") == "Director"],
			"name",
		)
	external_ids = data.get("external_ids")
	imdb_id = _optional_text(external_ids, "imdb_id") if isinstance(external_ids, dict) else None
	if imdb_id is not None and IMDB_ID_PATTERN.fullmatch(imdb_id) is None:
		imdb_id = None
	remote_poster_path = _optional_text(data, "poster_path")
	poster_path = _fetch_poster(tmdb_id, remote_poster_path, poster_directory, token, identity)
	original_language = _original_language_name(data, token)

	movie = TmdbMovie(
		title=title.strip(),
		year=year,
		plot=plot if plot is not None else "",
		genres=genres,
		runtime_minutes=runtime_minutes,
		directors=directors,
		tmdb_id=returned_id,
		imdb_id=imdb_id,
		poster_path=poster_path,
		original_language=original_language,
	)
	return movie

"""Orchestrate one validated movie from interactive input to an ODP slide."""

# Standard Library
import re
import pathlib
import tempfile
import dataclasses
import unicodedata
import collections.abc

# local repo modules
import slide_maker.config
import slide_maker.moviedata
import slide_maker.rt_scraper
import slide_maker.movie_input
import slide_maker.tmdb_client
import slide_maker.imdb_ratings
import slide_maker.slide_builder
import slide_maker.slide_convert
import slide_maker.movie_identity
import slide_maker.movie_resolver
import slide_maker.metacritic_scraper


@dataclasses.dataclass(frozen=True, slots=True)
class ProviderBundle:
	"""Injectable provider and resolver functions used by one pipeline run."""

	resolve_tmdb_id: collections.abc.Callable[
		[
			slide_maker.movie_input.MovieInput,
			collections.abc.Callable[[str], str],
			collections.abc.Callable[[str], None],
		],
		int,
	]
	fetch_tmdb_movie: collections.abc.Callable[
		[int, str | pathlib.Path],
		slide_maker.tmdb_client.TmdbMovie,
	]
	fetch_imdb_rating: collections.abc.Callable[
		[str],
		slide_maker.imdb_ratings.ImdbRating,
	]
	fetch_rt_rating: collections.abc.Callable[
		[str, str, str, int, list[str]],
		slide_maker.rt_scraper.RtRating,
	]
	fetch_metacritic_rating: collections.abc.Callable[
		[str, str, str, int, list[str]],
		slide_maker.metacritic_scraper.MetacriticRating,
	]


LIVE_PROVIDERS = ProviderBundle(
	resolve_tmdb_id=slide_maker.movie_resolver.resolve_tmdb_id,
	fetch_tmdb_movie=slide_maker.tmdb_client.fetch_movie,
	fetch_imdb_rating=slide_maker.imdb_ratings.fetch_imdb_ratings,
	fetch_rt_rating=slide_maker.rt_scraper.fetch_rt_rating,
	fetch_metacritic_rating=slide_maker.metacritic_scraper.fetch_metacritic_rating,
)


class MoviePipelineError(RuntimeError):
	"""Report an incomplete or inconsistent source before presentation creation."""


#============================================
def _source_error(
	source: str,
	movie: slide_maker.tmdb_client.TmdbMovie,
	attempted: str,
	problem: str,
) -> MoviePipelineError:
	"""Build a source, identity, and attempted-location pipeline error."""
	identity = f"{movie.title!r} ({movie.year}), IMDb id {movie.imdb_id}"
	message = f"{source} source error for {identity} at {attempted}: {problem}"
	error = MoviePipelineError(message)
	return error


#============================================
def _require_source(
	condition: bool,
	source: str,
	movie: slide_maker.tmdb_client.TmdbMovie,
	attempted: str,
	problem: str,
) -> None:
	"""Raise a contextual pipeline error when a provider result is invalid."""
	if not condition:
		raise _source_error(source, movie, attempted, problem)


#============================================
def _validate_tmdb_movie(
	movie: slide_maker.tmdb_client.TmdbMovie,
	attempted: str,
) -> None:
	"""Validate all TMDB-owned fields before querying dependent providers."""
	identity = f"TMDB id {movie.tmdb_id}"
	if not movie.title.strip():
		raise MoviePipelineError(f"TMDB source error for {identity} at {attempted}: title was missing")
	if movie.year <= 0:
		raise MoviePipelineError(f"TMDB source error for {identity} at {attempted}: year was invalid")
	if not movie.plot.strip():
		raise MoviePipelineError(f"TMDB source error for {identity} at {attempted}: plot was missing")
	if not movie.genres or any(not genre.strip() for genre in movie.genres):
		raise MoviePipelineError(f"TMDB source error for {identity} at {attempted}: genres were missing")
	if movie.runtime_minutes <= 0:
		raise MoviePipelineError(f"TMDB source error for {identity} at {attempted}: runtime was invalid")
	if not movie.directors or any(not director.strip() for director in movie.directors):
		message = f"TMDB source error for {identity} at {attempted}: directors were missing"
		raise MoviePipelineError(message)
	if movie.tmdb_id <= 0 or re.fullmatch(r"tt[0-9]{7,10}", movie.imdb_id) is None:
		raise MoviePipelineError(f"TMDB source error for {identity} at {attempted}: ids were invalid")
	if not pathlib.Path(movie.poster_path).is_file():
		raise MoviePipelineError(f"TMDB source error for {identity} at {attempted}: poster was missing")


#============================================
def _validate_imdb_rating(
	result: slide_maker.imdb_ratings.ImdbRating,
	movie: slide_maker.tmdb_client.TmdbMovie,
) -> None:
	"""Validate IMDb identity, rating, and vote values against TMDB."""
	attempted = f"https://www.imdb.com/title/{movie.imdb_id}/"
	_require_source(result.imdb_id == movie.imdb_id, "IMDb", movie, attempted, "id did not match TMDB")
	_require_source(
		bool(result.title.strip()),
		"IMDb",
		movie,
		attempted,
		"title was missing",
	)
	_require_source(
		result.year > 0,
		"IMDb",
		movie,
		attempted,
		"year was invalid",
	)
	_require_source(0.0 <= result.imdb_rating <= 10.0, "IMDb", movie, attempted, "rating was invalid")
	_require_source(result.imdb_votes > 0, "IMDb", movie, attempted, "vote count was missing")


#============================================
def _slug_base(title: str, separator: str) -> str:
	"""Build one provider-style ASCII title slug."""
	normalized = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
	slug = re.sub(r"[^a-z0-9]+", separator, normalized.casefold()).strip(separator)
	return slug


#============================================
def source_slug_candidates(title: str, year: int, separator: str) -> tuple[str, ...]:
	"""Return bounded title and title-year candidates for one provider.

	Args:
		title: Movie title to transliterate and normalize.
		year: Release year appended to the second candidate.
		separator: Provider-specific separator between normalized words.

	Returns:
		The normalized title slug followed by its title-and-year form.

	Raises:
		ValueError: The title cannot produce a nonempty ASCII slug.
	"""
	base_slug = _slug_base(title, separator)
	if not base_slug:
		raise ValueError(f"Movie title cannot produce a source slug: {title!r}")
	year_slug = f"{base_slug}{separator}{year}"
	candidates = (base_slug, year_slug)
	return candidates


#============================================
def _source_slug_candidates_for_titles(
	titles: list[str],
	year: int,
	separator: str,
) -> tuple[str, ...]:
	"""Return unique provider slugs for multiple trusted movie titles."""
	candidates = []
	for title in titles:
		for candidate in source_slug_candidates(title, year, separator):
			if candidate not in candidates:
				candidates.append(candidate)
	result = tuple(candidates)
	return result


#============================================
def _rt_slug_candidates(title: str, year: int) -> tuple[str, ...]:
	"""Return bounded RT candidates including its legacy joined-hyphen style."""
	standard_candidates = source_slug_candidates(title, year, "_")
	joined_slug = _slug_base(title.replace("-", ""), "_")
	candidates = list(standard_candidates)
	joined_candidates = (joined_slug, f"{joined_slug}_{year}")
	for candidate in joined_candidates:
		if candidate not in candidates:
			candidates.append(candidate)
	result = tuple(candidates)
	return result


#============================================
def product_slug(title: str, year: int) -> str:
	"""Return the stable title-and-year product filename stem.

	Args:
		title: Movie title to transliterate and normalize.
		year: Release year appended to the filename stem.

	Returns:
		A lowercase underscore-separated ASCII filename stem.

	Raises:
		ValueError: The title cannot produce a nonempty ASCII slug.
	"""
	base_slug = _slug_base(title, "_")
	if not base_slug:
		raise ValueError(f"Movie title cannot produce a product slug: {title!r}")
	slug = f"{base_slug}_{year}"
	return slug


#============================================
def _fetch_rt(
	movie: slide_maker.tmdb_client.TmdbMovie,
	providers: ProviderBundle,
) -> slide_maker.rt_scraper.RtRating:
	"""Resolve and validate one bounded Rotten Tomatoes candidate sequence."""
	attempted_urls = []
	last_error: slide_maker.rt_scraper.RtSourceError | None = None
	for slug in _rt_slug_candidates(movie.title, movie.year):
		attempted_url = f"{slide_maker.rt_scraper.RT_MOVIE_ROOT}/{slug}"
		attempted_urls.append(attempted_url)
		try:
			result = providers.fetch_rt_rating(
				movie.imdb_id,
				slug,
				movie.title,
				movie.year,
				movie.directors,
			)
		except slide_maker.rt_scraper.RtSourceError as error:
			last_error = error
			continue
		_require_source(
			result.imdb_id == movie.imdb_id,
			"Rotten Tomatoes",
			movie,
			attempted_url,
			"id did not match TMDB",
		)
		matches = slide_maker.movie_identity.count_identity_matches(
			result.title,
			result.year,
			result.directors,
			movie.title,
			movie.year,
			movie.directors,
		)
		_require_source(
			matches >= 2,
			"Rotten Tomatoes",
			movie,
			attempted_url,
			"candidate failed two identity attributes",
		)
		_require_source(
			0 <= result.rt_tomatometer <= 100,
			"Rotten Tomatoes",
			movie,
			attempted_url,
			"Tomatometer was invalid",
		)
		_require_source(
			result.rt_audience_score is None
			or 0 <= result.rt_audience_score <= 100,
			"Rotten Tomatoes",
			movie,
			attempted_url,
			"Popcornmeter was invalid",
		)
		_require_source(
			result.rt_state in ("fresh", "rotten"),
			"Rotten Tomatoes",
			movie,
			attempted_url,
			"freshness state was invalid",
		)
		_require_source(
			bool(result.rt_consensus.strip()),
			"Rotten Tomatoes",
			movie,
			attempted_url,
			"critics consensus was missing",
		)
		return result
	attempted = ", ".join(attempted_urls)
	problem = f"bounded candidates failed; last source diagnostic: {last_error}"
	raise _source_error("Rotten Tomatoes", movie, attempted, problem)


#============================================
def _fetch_metacritic(
	movie: slide_maker.tmdb_client.TmdbMovie,
	imdb_title: str,
	providers: ProviderBundle,
) -> slide_maker.metacritic_scraper.MetacriticRating:
	"""Resolve Metacritic from its IMDb-aligned title and the TMDB title."""
	attempted_urls = []
	last_error: slide_maker.metacritic_scraper.MetacriticSourceError | None = None
	titles = [imdb_title, movie.title]
	for slug in _source_slug_candidates_for_titles(titles, movie.year, "-"):
		attempted_url = f"{slide_maker.metacritic_scraper.METACRITIC_MOVIE_ROOT}/{slug}/"
		attempted_urls.append(attempted_url)
		try:
			result = providers.fetch_metacritic_rating(
				movie.imdb_id,
				slug,
				movie.title,
				movie.year,
				movie.directors,
			)
		except slide_maker.metacritic_scraper.MetacriticSourceError as error:
			last_error = error
			continue
		_require_source(
			result.imdb_id == movie.imdb_id,
			"Metacritic",
			movie,
			attempted_url,
			"id did not match TMDB",
		)
		matches = slide_maker.movie_identity.count_identity_matches(
			result.title,
			result.year,
			result.directors,
			movie.title,
			movie.year,
			movie.directors,
		)
		_require_source(
			matches >= 2,
			"Metacritic",
			movie,
			attempted_url,
			"candidate failed two identity attributes",
		)
		_require_source(
			0 <= result.metascore <= 100,
			"Metacritic",
			movie,
			attempted_url,
			"Metascore was missing or invalid",
		)
		_require_source(
			result.metascore_band in ("low", "middle", "high"),
			"Metacritic",
			movie,
			attempted_url,
			"Metascore band was invalid",
		)
		return result
	attempted = ", ".join(attempted_urls)
	problem = f"bounded candidates failed; last source diagnostic: {last_error}"
	raise _source_error("Metacritic", movie, attempted, problem)


#============================================
def _assemble_movie_data(
	tmdb_movie: slide_maker.tmdb_client.TmdbMovie,
	imdb_rating: slide_maker.imdb_ratings.ImdbRating,
	rt_rating: slide_maker.rt_scraper.RtRating,
	metacritic_rating: slide_maker.metacritic_scraper.MetacriticRating,
) -> slide_maker.moviedata.MovieData:
	"""Assemble and validate the provider-to-builder contract."""
	movie_data = slide_maker.moviedata.MovieData(
		title=tmdb_movie.title,
		year=tmdb_movie.year,
		plot=tmdb_movie.plot,
		genres=tmdb_movie.genres,
		runtime_minutes=tmdb_movie.runtime_minutes,
		directors=tmdb_movie.directors,
		tmdb_id=tmdb_movie.tmdb_id,
		imdb_id=tmdb_movie.imdb_id,
		imdb_rating=imdb_rating.imdb_rating,
		imdb_votes=imdb_rating.imdb_votes,
		rt_tomatometer=rt_rating.rt_tomatometer,
		rt_audience_score=rt_rating.rt_audience_score,
		rt_state=rt_rating.rt_state,
		rt_consensus=rt_rating.rt_consensus,
		metascore=metacritic_rating.metascore,
		metascore_band=metacritic_rating.metascore_band,
		poster_path=tmdb_movie.poster_path,
	)
	slide_maker.moviedata.validate_movie_data(movie_data)
	return movie_data


#============================================
def resolve_movie_data(
	raw_input: str,
	poster_directory: str | pathlib.Path,
	providers: ProviderBundle = LIVE_PROVIDERS,
	read_choice: collections.abc.Callable[[str], str] = input,
	write_line: collections.abc.Callable[[str], None] = print,
) -> slide_maker.moviedata.MovieData:
	"""Resolve all providers and return validated data with a caller-owned poster.

	Args:
		raw_input: Movie title, provider id, or supported provider URL.
		poster_directory: Directory that will receive the downloaded poster.
		providers: Injectable resolver and provider functions for the full pipeline.
		read_choice: Callback used only when title resolution needs a menu choice.
		write_line: Callback that receives prompts and progress messages.

	Returns:
		A complete validated movie-data contract with a local poster path.

	Raises:
		ValueError: The input or a provider argument is malformed.
		MoviePipelineError: A provider result conflicts with the resolved identity.
		RuntimeError: A resolver or provider cannot return its required data.

	Note:
		The function may prompt through ``read_choice``, reports through
		``write_line``, performs provider requests, and writes the poster into
		``poster_directory``.
	"""
	movie_input = slide_maker.movie_input.classify_movie_input(raw_input)
	write_line("Resolving movie identity with TMDB...")
	tmdb_id = providers.resolve_tmdb_id(movie_input, read_choice, write_line)
	tmdb_movie = providers.fetch_tmdb_movie(tmdb_id, poster_directory)
	_validate_tmdb_movie(tmdb_movie, f"TMDB id {tmdb_id}")
	write_line(f"Resolved {tmdb_movie.title} ({tmdb_movie.year}); fetching ratings...")
	imdb_rating = providers.fetch_imdb_rating(tmdb_movie.imdb_id)
	_validate_imdb_rating(imdb_rating, tmdb_movie)
	rt_rating = _fetch_rt(tmdb_movie, providers)
	metacritic_rating = _fetch_metacritic(tmdb_movie, imdb_rating.title, providers)
	movie_data = _assemble_movie_data(
		tmdb_movie,
		imdb_rating,
		rt_rating,
		metacritic_rating,
	)
	return movie_data


#============================================
def generate_movie_slide(
	raw_input: str,
	output_directory: str | pathlib.Path = ".",
	providers: ProviderBundle = LIVE_PROVIDERS,
	read_choice: collections.abc.Callable[[str], str] = input,
	write_line: collections.abc.Callable[[str], None] = print,
) -> pathlib.Path:
	"""Resolve, validate, build, convert, and return one movie ODP path.

	Args:
		raw_input: Movie title, provider id, or supported provider URL.
		output_directory: Directory that will receive the presentation artifacts.
		providers: Injectable resolver and provider functions for the full pipeline.
		read_choice: Callback used only when title resolution needs a menu choice.
		write_line: Callback that receives prompts, progress, and completion messages.

	Returns:
		The validated ODP product path.

	Raises:
		ValueError: The input or a provider argument is malformed.
		MoviePipelineError: A provider result conflicts with the resolved identity.
		RuntimeError: Resolution, provider retrieval, build, or conversion fails.

	Note:
		The function may prompt through ``read_choice``, performs provider requests,
		creates ``output_directory``, and writes a scratch PPTX and final ODP. A
		failed conversion preserves the scratch PPTX; success removes it.
	"""
	repo_root = slide_maker.config.get_repo_root()
	template_path = repo_root / "template" / "movie_slide_template.pptx"
	with tempfile.TemporaryDirectory() as temporary_directory:
		movie_data = resolve_movie_data(
			raw_input,
			temporary_directory,
			providers,
			read_choice,
			write_line,
		)
		write_line("All provider data validated; building the presentation...")
		output_dir = pathlib.Path(output_directory)
		output_dir.mkdir(parents=True, exist_ok=True)
		slug = product_slug(movie_data.title, movie_data.year)
		scratch_path = output_dir / f"{slug}.pptx"
		output_path = output_dir / f"{slug}.odp"
		slide_maker.slide_builder.build_movie_presentation(
			movie_data,
			template_path,
			scratch_path,
		)
		product_path = slide_maker.slide_convert.convert_presentation(
			scratch_path,
			output_path,
		)
	write_line(f"Created validated movie slide: {product_path}")
	return product_path

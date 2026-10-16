"""Orchestrate one validated movie from interactive input to an ODP slide."""

# Standard Library
import re
import hashlib
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
	resolve_tmdb_movie: collections.abc.Callable[
		[
			slide_maker.movie_input.MovieInput,
			collections.abc.Callable[[str], str],
			collections.abc.Callable[[str], None],
		],
		slide_maker.movie_resolver.ResolvedTmdbMovie,
	] | None = None


LIVE_PROVIDERS = ProviderBundle(
	resolve_tmdb_id=slide_maker.movie_resolver.resolve_tmdb_id,
	fetch_tmdb_movie=slide_maker.tmdb_client.fetch_movie,
	fetch_imdb_rating=slide_maker.imdb_ratings.fetch_imdb_ratings,
	fetch_rt_rating=slide_maker.rt_scraper.fetch_rt_rating,
	fetch_metacritic_rating=slide_maker.metacritic_scraper.fetch_metacritic_rating,
	resolve_tmdb_movie=slide_maker.movie_resolver.resolve_tmdb_movie,
)


class MoviePipelineError(RuntimeError):
	"""Report an unrecoverable movie identity or presentation problem."""


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
def _slug_base(title: str, separator: str) -> str:
	"""Build one provider-style ASCII title slug."""
	normalized = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
	slug = re.sub(r"[^a-z0-9]+", separator, normalized.casefold()).strip(separator)
	return slug


#============================================
def source_slug_candidates(title: str, year: int | None, separator: str) -> tuple[str, ...]:
	"""Return bounded title and title-year candidates for one provider.

	Args:
		title: Movie title to transliterate and normalize.
		year: Release year appended to the second candidate.
		separator: Provider-specific separator between normalized words.

	Returns:
		The normalized title slug followed by its title-and-year form.

	"""
	base_slug = _slug_base(title, separator)
	if not base_slug:
		return ()
	candidates = (base_slug,)
	if year is not None:
		year_slug = f"{base_slug}{separator}{year}"
		candidates += (year_slug,)
	return candidates


#============================================
def _source_slug_candidates_for_titles(
	titles: list[str],
	year: int | None,
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
def _rt_slug_candidates(title: str, year: int | None) -> tuple[str, ...]:
	"""Return bounded RT candidates including its legacy joined-hyphen style."""
	standard_candidates = source_slug_candidates(title, year, "_")
	if not standard_candidates:
		return ()
	joined_slug = _slug_base(title.replace("-", ""), "_")
	candidates = list(standard_candidates)
	if not joined_slug:
		joined_slug = standard_candidates[0]
	joined_candidates = (joined_slug,)
	if year is not None:
		joined_candidates += (f"{joined_slug}_{year}",)
	for candidate in joined_candidates:
		if candidate not in candidates:
			candidates.append(candidate)
	result = tuple(candidates)
	return result


#============================================
def product_slug(title: str, year: int | None) -> str:
	"""Return the stable title-and-year product filename stem.

	Args:
		title: Movie title to transliterate and normalize.
		year: Release year appended to the filename stem.

	Returns:
		A lowercase underscore-separated ASCII filename stem.

	"""
	base_slug = _slug_base(title, "_")
	if not base_slug:
		digest = hashlib.sha256(title.strip().encode("utf-8")).hexdigest()[:12]
		base_slug = f"movie_{digest}"
	slug = base_slug
	if year is not None:
		slug += f"_{year}"
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
		return result
	attempted = ", ".join(attempted_urls)
	problem = f"bounded candidates failed; last source diagnostic: {last_error}"
	raise _source_error("Metacritic", movie, attempted, problem)


#============================================
def _assemble_movie_data(
	tmdb_movie: slide_maker.tmdb_client.TmdbMovie,
	imdb_rating: slide_maker.imdb_ratings.ImdbRating | None,
	rt_rating: slide_maker.rt_scraper.RtRating | None,
	metacritic_rating: slide_maker.metacritic_scraper.MetacriticRating | None,
	title: str | None = None,
	year: int | None = None,
) -> slide_maker.moviedata.MovieData:
	"""Assemble the independent provider values into one adaptable contract."""
	# ASVS 2.2.1: validate supplied values independently at the provider boundary.
	resolved_title = title if title is not None else tmdb_movie.title
	resolved_year = year if year is not None else tmdb_movie.year
	if type(resolved_year) is not int or resolved_year <= 0:
		resolved_year = None
	rt_score = rt_rating.rt_tomatometer if rt_rating is not None else None
	if type(rt_score) is not int or not 0 <= rt_score <= 100:
		rt_score = None
	rt_state = rt_rating.rt_state if rt_score is not None and rt_rating is not None else None
	if rt_score is not None:
		expected_rt_state = slide_maker.emoji_marks.rt_state_for_score(rt_score)
		if rt_state is not None and rt_state != expected_rt_state:
			rt_score = None
			rt_state = None
	rt_audience = rt_rating.rt_audience_score if rt_rating is not None else None
	if type(rt_audience) is not int or not 0 <= rt_audience <= 100:
		rt_audience = None
	metascore = metacritic_rating.metascore if metacritic_rating is not None else None
	if type(metascore) is not int or not 0 <= metascore <= 100:
		metascore = None
	metascore_band = metacritic_rating.metascore_band if metascore is not None and metacritic_rating is not None else None
	if metascore is not None:
		expected_band = slide_maker.emoji_marks.metascore_band_for_score(metascore)
		if metascore_band is not None and metascore_band != expected_band:
			metascore = None
			metascore_band = None
	genres = [genre for genre in tmdb_movie.genres if isinstance(genre, str) and genre.strip()]
	directors = [director for director in tmdb_movie.directors if isinstance(director, str) and director.strip()]
	runtime = tmdb_movie.runtime_minutes
	if type(runtime) is not int or runtime <= 0:
		runtime = None
	poster_path = tmdb_movie.poster_path
	if poster_path is not None and not pathlib.Path(poster_path).is_file():
		poster_path = None
	tmdb_id = tmdb_movie.tmdb_id
	if type(tmdb_id) is not int or tmdb_id <= 0:
		tmdb_id = None
	imdb_id = tmdb_movie.imdb_id
	if not isinstance(imdb_id, str) or re.fullmatch(r"tt[0-9]{7,10}", imdb_id) is None:
		imdb_id = None
	plot = tmdb_movie.plot if isinstance(tmdb_movie.plot, str) else ""
	imdb_score = imdb_rating.imdb_rating if imdb_rating is not None else None
	if type(imdb_score) not in (int, float) or not 0.0 <= imdb_score <= 10.0:
		imdb_score = None
	imdb_votes = imdb_rating.imdb_votes if imdb_rating is not None else None
	if type(imdb_votes) is not int or imdb_votes < 0:
		imdb_votes = None
	consensus = rt_rating.rt_consensus if rt_rating is not None else ""
	if not isinstance(consensus, str):
		consensus = ""
	original_language = tmdb_movie.original_language
	if not isinstance(original_language, str) or not original_language.strip():
		original_language = None
	movie_data = slide_maker.moviedata.MovieData(
		title=resolved_title,
		year=resolved_year,
		plot=plot,
		genres=genres,
		runtime_minutes=runtime,
		directors=directors,
		tmdb_id=tmdb_id,
		imdb_id=imdb_id,
		imdb_rating=imdb_score,
		imdb_votes=imdb_votes,
		rt_tomatometer=rt_score,
		rt_audience_score=rt_audience,
		rt_state=rt_state,
		rt_consensus=consensus,
		metascore=metascore,
		metascore_band=metascore_band,
		poster_path=poster_path,
		original_language=original_language,
	)
	slide_maker.moviedata.validate_movie_data(movie_data)
	return movie_data


#============================================
def _report_source_problem(
	write_line: collections.abc.Callable[[str], None],
	source: str,
	problem: BaseException | str,
) -> None:
	"""Report a concise source omission without exposing provider internals."""
	message = str(problem).splitlines()[0]
	write_line(f"{source} metadata omitted: {message}")


#============================================
def _requested_identity(
	movie_input: slide_maker.movie_input.MovieInput,
	read_choice: collections.abc.Callable[[str], str],
) -> tuple[str, int | None]:
	"""Return a slide title without inventing a title for identifier-only input."""
	if movie_input.kind == slide_maker.movie_input.InputKind.TITLE:
		return movie_input.value, movie_input.year
	title = read_choice("TMDB details are unavailable. Enter the movie title: ").strip()
	if not title:
		raise MoviePipelineError("Identifier-only input needs a movie title when TMDB details fail")
	return title, None


#============================================
def _matches_requested_identity(
	movie: slide_maker.tmdb_client.TmdbMovie,
	requested_title: str,
	requested_year: int | None,
) -> bool:
	"""Return whether TMDB details agree with a title request when comparable."""
	if slide_maker.movie_identity.normalize_identity_text(movie.title) != (
		slide_maker.movie_identity.normalize_identity_text(requested_title)
	):
		return False
	if requested_year is not None and movie.year is not None and movie.year != requested_year:
		return False
	return True


#============================================
def _sparse_movie(title: str, year: int | None) -> slide_maker.moviedata.MovieData:
	"""Build a title-only contract after the source identity cannot be enriched."""
	movie_data = slide_maker.moviedata.MovieData(title=title, year=year)
	slide_maker.moviedata.validate_movie_data(movie_data)
	return movie_data


#============================================
def _fallback_identity(
	movie_input: slide_maker.movie_input.MovieInput,
	selected_identity: slide_maker.movie_resolver.ResolvedTmdbMovie | None,
	read_choice: collections.abc.Callable[[str], str],
) -> tuple[str, int | None]:
	"""Return the trusted selection or recover a title for an identifier input."""
	if selected_identity is not None and selected_identity.title is not None:
		return selected_identity.title, selected_identity.year
	return _requested_identity(movie_input, read_choice)


#============================================
def _valid_imdb_rating(
	result: slide_maker.imdb_ratings.ImdbRating,
	movie: slide_maker.tmdb_client.TmdbMovie,
) -> bool:
	"""Accept IMDb values only when its identifier positively agrees with TMDB."""
	return movie.imdb_id is not None and result.imdb_id == movie.imdb_id


#============================================
def _provider_identity_matches(
	result: object,
	movie: slide_maker.tmdb_client.TmdbMovie,
	source: str,
	write_line: collections.abc.Callable[[str], None],
) -> bool:
	"""Accept a scraped record only after two identity attributes agree."""
	if not movie.title:
		_report_source_problem(write_line, source, "rating record did not match")
		return False
	result_title = getattr(result, "title")
	result_year = getattr(result, "year")
	result_directors = getattr(result, "directors")
	if (
		not isinstance(result_title, str)
		or not isinstance(result_directors, list)
		or any(not isinstance(director, str) for director in result_directors)
	):
		_report_source_problem(write_line, source, "rating record did not match")
		return False
	matches = slide_maker.movie_identity.count_identity_matches(
		result_title,
		result_year,
		result_directors,
		movie.title,
		movie.year,
		movie.directors,
	)
	if matches >= 2:
		return True
	_report_source_problem(write_line, source, "rating record did not match")
	return False


#============================================
def resolve_movie_data(
	raw_input: str,
	poster_directory: str | pathlib.Path,
	providers: ProviderBundle = LIVE_PROVIDERS,
	read_choice: collections.abc.Callable[[str], str] = input,
	write_line: collections.abc.Callable[[str], None] = print,
) -> slide_maker.moviedata.MovieData:
	"""Resolve available providers and return adaptable data with a caller-owned poster.

	Args:
		raw_input: Movie title, provider id, or supported provider URL.
		poster_directory: Directory that will receive the downloaded poster.
		providers: Injectable resolver and provider functions for the full pipeline.
		read_choice: Callback used only when title resolution needs a menu choice.
		write_line: Callback that receives prompts and progress messages.

	Returns:
		A validated movie-data contract containing every usable source value.

	Raises:
		ValueError: The input or a provider argument is malformed.
		MoviePipelineError: Identifier-only input cannot recover a display title.
		RuntimeError: A resolver or provider has an unexpected programming failure.

	Note:
		The function may prompt through ``read_choice`` when identifier-only
		input cannot recover a title. It reports omitted source data through
		``write_line`` and writes an available poster into ``poster_directory``.
	"""
	movie_input = slide_maker.movie_input.classify_movie_input(raw_input)
	requested_title = movie_input.value if movie_input.kind == slide_maker.movie_input.InputKind.TITLE else None
	requested_year = movie_input.year if requested_title is not None else None
	write_line("Resolving movie identity with TMDB...")
	selected_identity = None
	try:
		if providers.resolve_tmdb_movie is None:
			tmdb_id = providers.resolve_tmdb_id(movie_input, read_choice, write_line)
			selected_identity = None
		else:
			selected_identity = providers.resolve_tmdb_movie(movie_input, read_choice, write_line)
			tmdb_id = selected_identity.tmdb_id
		tmdb_movie = providers.fetch_tmdb_movie(tmdb_id, poster_directory)
	except (
		slide_maker.movie_resolver.MovieResolutionError,
		slide_maker.tmdb_client.TmdbSourceError,
	) as error:
		_report_source_problem(write_line, "TMDB", error)
		requested_title, requested_year = _fallback_identity(
			movie_input,
			selected_identity,
			read_choice,
		)
		return _sparse_movie(requested_title, requested_year)
	if tmdb_movie.tmdb_id != tmdb_id:
		_report_source_problem(write_line, "TMDB", "details returned a different TMDB id")
		requested_title, requested_year = _fallback_identity(
			movie_input,
			selected_identity,
			read_choice,
		)
		return _sparse_movie(requested_title, requested_year)

	if movie_input.kind == slide_maker.movie_input.InputKind.TITLE:
		if requested_title is None:
			raise MoviePipelineError("Title input was missing its requested title")
		if selected_identity is not None and selected_identity.title is not None:
			# The resolved TMDB id anchors the selected identity.  Its display label
			# may be a title alias and its release year may be absent from details.
			requested_title = selected_identity.title
			requested_year = selected_identity.year
		elif not _matches_requested_identity(tmdb_movie, requested_title, requested_year):
			_report_source_problem(write_line, "TMDB", "returned a different movie")
			return _sparse_movie(requested_title, requested_year)
	else:
		requested_title = tmdb_movie.title.strip()
		requested_year = tmdb_movie.year
	if not requested_title:
		raise MoviePipelineError("TMDB details did not provide a usable movie title")
	if tmdb_movie.poster_path is None:
		poster_problem = getattr(tmdb_movie, "poster_diagnostic", None)
		if poster_problem is None:
			poster_problem = "no usable poster was available"
		_report_source_problem(write_line, "TMDB poster", poster_problem)

	# TMDB owns the base metadata.  Missing optional fields remain absent rather
	# than preventing independent ratings from reaching a student-facing slide.
	write_line(f"Resolved {requested_title}; fetching available ratings...")
	imdb_rating = None
	if tmdb_movie.imdb_id is not None:
		try:
			candidate = providers.fetch_imdb_rating(tmdb_movie.imdb_id)
		except slide_maker.imdb_ratings.ImdbSourceError as error:
			_report_source_problem(write_line, "IMDb", error)
		else:
			if _valid_imdb_rating(candidate, tmdb_movie):
				imdb_rating = candidate
			else:
				_report_source_problem(write_line, "IMDb", "rating record did not match the movie")

	rt_rating = None
	if tmdb_movie.title:
		try:
			candidate = _fetch_rt(tmdb_movie, providers)
		except (slide_maker.rt_scraper.RtSourceError, MoviePipelineError) as error:
			_report_source_problem(write_line, "Rotten Tomatoes", error)
		else:
			if _provider_identity_matches(candidate, tmdb_movie, "Rotten Tomatoes", write_line):
				rt_rating = candidate

	metacritic_rating = None
	if tmdb_movie.title:
		imdb_title = tmdb_movie.title
		if imdb_rating is not None and isinstance(imdb_rating.title, str) and imdb_rating.title.strip():
			imdb_title = imdb_rating.title
		try:
			candidate = _fetch_metacritic(tmdb_movie, imdb_title, providers)
		except (slide_maker.metacritic_scraper.MetacriticSourceError, MoviePipelineError) as error:
			_report_source_problem(write_line, "Metacritic", error)
		else:
			if _provider_identity_matches(candidate, tmdb_movie, "Metacritic", write_line):
				metacritic_rating = candidate

	movie_data = _assemble_movie_data(
		tmdb_movie,
		imdb_rating,
		rt_rating,
		metacritic_rating,
		requested_title,
		requested_year,
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
		write_line("Available movie data assembled; building the presentation...")
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
	write_line(f"Created movie slide: {product_path}")
	return product_path

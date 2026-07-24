"""Resolve classified movie input to one TMDB movie identity."""

# Standard Library
import collections.abc

# local repo modules
import slide_maker.movie_input
import slide_maker.tmdb_client


OVERVIEW_WORD_LIMIT = 12


class MovieResolutionError(RuntimeError):
	"""Report that interactive movie resolution could not select a movie."""


#============================================
def _require_positive_tmdb_id(tmdb_id: int, attempted_input: str) -> int:
	"""Require one resolved identity to be a positive TMDB movie id."""
	if type(tmdb_id) is not int or tmdb_id <= 0:
		raise MovieResolutionError(
			f"{attempted_input} did not resolve to a positive TMDB movie id: {tmdb_id!r}"
		)
	return tmdb_id


#============================================
def _candidate_label(
	index: int,
	candidate: slide_maker.tmdb_client.TmdbSearchResult,
) -> str:
	"""Build one human-readable numbered TMDB candidate label."""
	year = str(candidate.year) if candidate.year is not None else "year unknown"
	overview_words = candidate.overview.split()
	overview = " ".join(overview_words[:OVERVIEW_WORD_LIMIT])
	if len(overview_words) > OVERVIEW_WORD_LIMIT:
		overview += "..."
	if not overview:
		overview = "No summary available."
	label = (
		f"{index}. {candidate.title} ({year}) [TMDB {candidate.tmdb_id}] "
		f"- {overview}"
	)
	return label


#============================================
def select_movie_candidate(
	candidates: list[slide_maker.tmdb_client.TmdbSearchResult],
	read_choice: collections.abc.Callable[[str], str] = input,
	write_line: collections.abc.Callable[[str], None] = print,
) -> slide_maker.tmdb_client.TmdbSearchResult:
	"""Select one movie from TMDB search results.

	A single candidate is accepted without prompting. Multiple candidates are
	presented as a numbered menu until the user enters an available number.

	Args:
		candidates: TMDB search results in provider order.
		read_choice: Prompt function used to read one menu selection.
		write_line: Output function used to display the menu and guidance.

	Returns:
		The selected TMDB search result.

	Raises:
		MovieResolutionError: No movie candidates were available.
	"""
	if not candidates:
		raise MovieResolutionError("TMDB search returned no movie candidates")
	if len(candidates) == 1:
		candidate = candidates[0]
		return candidate

	write_line("Multiple TMDB movies matched:")
	for index, candidate in enumerate(candidates, start=1):
		write_line(_candidate_label(index, candidate))

	while True:
		raw_choice = read_choice(f"Choose a movie [1-{len(candidates)}]: ").strip()
		if raw_choice.isdecimal():
			selected_index = int(raw_choice) - 1
			if 0 <= selected_index < len(candidates):
				candidate = candidates[selected_index]
				return candidate
		write_line(f"Enter a number from 1 to {len(candidates)}.")


#============================================
def resolve_tmdb_id(
	movie_input: slide_maker.movie_input.MovieInput,
	read_choice: collections.abc.Callable[[str], str] = input,
	write_line: collections.abc.Callable[[str], None] = print,
) -> int:
	"""Resolve classified input to the TMDB id used by the movie pipeline.

	Args:
		movie_input: Classified title, IMDb identity, or TMDB identity.
		read_choice: Prompt function used for ambiguous title results.
		write_line: Output function used for ambiguous title results.

	Returns:
		A positive TMDB movie id.

	Raises:
		MovieResolutionError: The input does not resolve to a positive TMDB id.
	"""
	if movie_input.kind == slide_maker.movie_input.InputKind.IMDB:
		tmdb_id = slide_maker.tmdb_client.find_tmdb_id_by_imdb_id(movie_input.value)
		attempted_input = f"IMDb input {movie_input.value!r}"
		validated_id = _require_positive_tmdb_id(tmdb_id, attempted_input)
		return validated_id
	if movie_input.kind == slide_maker.movie_input.InputKind.TMDB:
		if not movie_input.value.isdecimal():
			raise MovieResolutionError(
				f"Direct TMDB input {movie_input.value!r} is not a positive movie id"
			)
		tmdb_id = int(movie_input.value)
		attempted_input = f"Direct TMDB input {movie_input.value!r}"
		validated_id = _require_positive_tmdb_id(tmdb_id, attempted_input)
		return validated_id

	candidates = slide_maker.tmdb_client.search_movies(movie_input.value, movie_input.year)
	if not candidates:
		attempted_title = f"title {movie_input.value!r}"
		if movie_input.year is not None:
			attempted_title += f" ({movie_input.year})"
		raise MovieResolutionError(f"TMDB search returned no movies for {attempted_title}")
	selected = select_movie_candidate(candidates, read_choice, write_line)
	tmdb_id = selected.tmdb_id
	attempted_input = f"TMDB search for title {movie_input.value!r}"
	validated_id = _require_positive_tmdb_id(tmdb_id, attempted_input)
	return validated_id

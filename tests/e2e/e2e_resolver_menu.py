"""Exercise every resolver route without network or terminal input."""

# Standard Library
import sys
import pathlib
import functools


TESTS_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TESTS_DIR))

# local repo modules
import file_utils

REPO_ROOT = pathlib.Path(file_utils.get_repo_root())

# local repo modules
import slide_maker.movie_input
import slide_maker.tmdb_client
import slide_maker.movie_resolver


#============================================
def require(condition: bool, message: str) -> None:
	"""Raise a clear E2E failure when a menu requirement is absent."""
	if condition:
		return
	raise RuntimeError(message)


#============================================
def capture_resolution_error(movie_input: slide_maker.movie_input.MovieInput) -> str:
	"""Return the explicit resolver error raised for one invalid input."""
	try:
		slide_maker.movie_resolver.resolve_tmdb_id(movie_input)
	except slide_maker.movie_resolver.MovieResolutionError as error:
		return str(error)
	raise RuntimeError(f"Expected MovieResolutionError for {movie_input!r}")


#============================================
def require_input(
	raw_input: str,
	expected_value: str,
	expected_year: int | None,
) -> None:
	"""Require one raw title input to retain its intended title and year."""
	movie_input = slide_maker.movie_input.classify_movie_input(raw_input)
	require(
		movie_input.kind is slide_maker.movie_input.InputKind.TITLE,
		f"{raw_input!r} was not a title",
	)
	require(movie_input.value == expected_value, f"{raw_input!r} produced the wrong title")
	require(movie_input.year == expected_year, f"{raw_input!r} produced the wrong year")


#============================================
def validate_input_classification() -> None:
	"""Validate title-year syntax, numeric titles, and empty-input rejection."""
	require_input("Her 2013", "Her", 2013)
	require_input("Her (2013)", "Her", 2013)
	require_input("Godzilla Minus One/2023", "Godzilla Minus One", 2023)
	require_input("Godzilla Minus One / 2023", "Godzilla Minus One", 2023)
	for numeric_title in ("1917", "1984", "2001", "42"):
		require_input(numeric_title, numeric_title, None)
	require_input("2001: A Space Odyssey", "2001: A Space Odyssey", None)
	empty_rejected = False
	try:
		slide_maker.movie_input.classify_movie_input("  ")
	except ValueError:
		empty_rejected = True
	require(empty_rejected, "Empty movie input was not rejected")


#============================================
def find_tmdb_id(
	provider_calls: list[tuple[str, str, int | None]],
	imdb_id: str,
) -> int:
	"""Return a deterministic cross-map identity and record the provider call."""
	provider_calls.append(("imdb", imdb_id, None))
	return 7001


#============================================
def search_movies(
	provider_calls: list[tuple[str, str, int | None]],
	title: str,
	year: int | None = None,
) -> list[slide_maker.tmdb_client.TmdbSearchResult]:
	"""Return deterministic zero, one, or multiple title-search results."""
	provider_calls.append(("title", title, year))
	if title == "Missing Movie":
		return []
	if title == "Only Movie":
		results = [slide_maker.tmdb_client.TmdbSearchResult(1001, "Only Movie", 2001)]
		return results
	if title == "The Movie":
		results = [
			slide_maker.tmdb_client.TmdbSearchResult(2001, "The Movie", 1999),
			slide_maker.tmdb_client.TmdbSearchResult(2002, "The Movie", 2024),
		]
		return results
	raise RuntimeError(f"Unexpected title search: {title!r} ({year!r})")


#============================================
def install_provider_stubs(provider_calls: list[tuple[str, str, int | None]]) -> None:
	"""Replace live TMDB calls with deterministic module-level stubs."""
	slide_maker.tmdb_client.find_tmdb_id_by_imdb_id = functools.partial(
		find_tmdb_id,
		provider_calls,
	)
	slide_maker.tmdb_client.search_movies = functools.partial(
		search_movies,
		provider_calls,
	)


#============================================
def read_scripted_choice(
	scripted_choices: list[str],
	written_lines: list[str],
	prompt: str,
) -> str:
	"""Return the next deterministic menu choice while capturing its prompt."""
	written_lines.append(prompt)
	choice = scripted_choices.pop(0)
	return choice


#============================================
def validate_direct_routes() -> None:
	"""Validate IMDb cross-map, direct TMDB, and invalid TMDB routes."""
	imdb_input = slide_maker.movie_input.MovieInput(
		slide_maker.movie_input.InputKind.IMDB,
		"tt0316654",
		None,
	)
	imdb_id = slide_maker.movie_resolver.resolve_tmdb_id(imdb_input)
	require(imdb_id == 7001, "IMDb input did not route through the TMDB cross-map")

	direct_tmdb_input = slide_maker.movie_input.MovieInput(
		slide_maker.movie_input.InputKind.TMDB,
		"8001",
		None,
	)
	direct_tmdb_id = slide_maker.movie_resolver.resolve_tmdb_id(direct_tmdb_input)
	require(direct_tmdb_id == 8001, "Direct TMDB input did not preserve its identity")

	invalid_tmdb_input = slide_maker.movie_input.MovieInput(
		slide_maker.movie_input.InputKind.TMDB,
		"0",
		None,
	)
	direct_error = capture_resolution_error(invalid_tmdb_input)
	require("positive TMDB movie id" in direct_error, "Direct TMDB error was not explicit")


#============================================
def validate_title_routes(
	written_lines: list[str],
) -> None:
	"""Validate zero, one, and multiple-result title routes and menu retries."""
	missing_input = slide_maker.movie_input.MovieInput(
		slide_maker.movie_input.InputKind.TITLE,
		"Missing Movie",
		2012,
	)
	missing_error = capture_resolution_error(missing_input)
	require("Missing Movie" in missing_error, "Zero-result error omitted the attempted title")
	require("2012" in missing_error, "Zero-result error omitted the attempted year")

	one_input = slide_maker.movie_input.MovieInput(
		slide_maker.movie_input.InputKind.TITLE,
		"Only Movie",
		2001,
	)
	one_id = slide_maker.movie_resolver.resolve_tmdb_id(one_input)
	require(one_id == 1001, "Single-result title did not resolve automatically")

	scripted_choices = ["invalid", "3", "2"]
	multiple_input = slide_maker.movie_input.MovieInput(
		slide_maker.movie_input.InputKind.TITLE,
		"The Movie",
		None,
	)
	multiple_id = slide_maker.movie_resolver.resolve_tmdb_id(
		multiple_input,
		functools.partial(read_scripted_choice, scripted_choices, written_lines),
		written_lines.append,
	)
	require(multiple_id == 2002, "Resolver menu selected the wrong TMDB identity")
	require(
		any(line.startswith("1. ") for line in written_lines)
		and any(line.startswith("2. ") for line in written_lines),
		"Resolver did not present numbered movie choices",
	)
	retry_count = sum(line.startswith("Enter a number") for line in written_lines)
	require(retry_count == 2, "Resolver did not retry both invalid menu choices")


#============================================
def validate_provider_calls(provider_calls: list[tuple[str, str, int | None]]) -> None:
	"""Require the resolver to make only the expected provider calls in order."""
	require(
		provider_calls == [
			("imdb", "tt0316654", None),
			("title", "Missing Movie", 2012),
			("title", "Only Movie", 2001),
			("title", "The Movie", None),
		],
		"Resolver provider routing changed unexpectedly",
	)


#============================================
def main() -> None:
	"""Drive direct identities and zero, one, and multiple title matches."""
	provider_calls: list[tuple[str, str, int | None]] = []
	written_lines: list[str] = []
	validate_input_classification()
	install_provider_stubs(provider_calls)
	validate_direct_routes()
	validate_title_routes(written_lines)
	validate_provider_calls(provider_calls)
	print("Resolver-menu E2E passed: all direct and title routes are deterministic")


if __name__ == "__main__":
	main()

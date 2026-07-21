"""Verify the live IMDb rating path against one current movie."""

# Standard Library
import sys
import pathlib


TESTS_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TESTS_DIR))

# local repo modules
import file_utils

REPO_ROOT = pathlib.Path(file_utils.get_repo_root())

# local repo modules
import slide_maker.imdb_ratings


CURRENT_MOVIE_IMDB_ID = "tt31193180"


#============================================
def require(condition: bool, message: str) -> None:
	"""Raise a clear E2E failure when a semantic requirement is absent."""
	if condition:
		return
	raise RuntimeError(message)


#============================================
def main() -> None:
	"""Fetch a current movie and validate identity-bearing IMDb values."""
	result = slide_maker.imdb_ratings.fetch_imdb_ratings(CURRENT_MOVIE_IMDB_ID)
	require(result.imdb_id == CURRENT_MOVIE_IMDB_ID, "IMDb identity anchor changed")
	require(result.title.strip(), "IMDb title is missing")
	require(result.year == 2025, "IMDb returned the wrong release year for Sinners")
	require(0.0 <= result.imdb_rating <= 10.0, "IMDb rating is outside 0-10")
	require(result.imdb_votes > 0, "IMDb vote count is missing")
	print(
		f"IMDb E2E passed: {result.imdb_id}; "
		f"{result.title} ({result.year}); "
		f"rating={result.imdb_rating:.1f}; votes={result.imdb_votes}"
	)


if __name__ == "__main__":
	main()

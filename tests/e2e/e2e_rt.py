"""Verify the live Rotten Tomatoes path against one current movie."""

# Standard Library
import sys
import pathlib


TESTS_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TESTS_DIR))

# local repo modules
import file_utils

REPO_ROOT = pathlib.Path(file_utils.get_repo_root())

# local repo modules
import slide_maker.rt_scraper


CURRENT_MOVIE_IMDB_ID = "tt31193180"


#============================================
def require(condition: bool, message: str) -> None:
	"""Raise a clear E2E failure when a semantic requirement is absent."""
	if condition:
		return
	raise RuntimeError(message)


#============================================
def main() -> None:
	"""Fetch a current movie and validate identity-bearing RT values."""
	result = slide_maker.rt_scraper.fetch_rt_rating(
		CURRENT_MOVIE_IMDB_ID,
		"sinners_2025",
		"Sinners",
		2025,
		["Ryan Coogler"],
	)
	require(result.imdb_id == CURRENT_MOVIE_IMDB_ID, "RT IMDb identity anchor changed")
	require(result.title == "Sinners", "RT title resolved a different movie")
	require(result.year == 2025, "RT release year resolved a different movie")
	require("Ryan Coogler" in result.directors, "RT director resolved a different movie")
	require(0 <= result.rt_tomatometer <= 100, "RT Tomatometer is outside 0-100")
	require(result.rt_state in ("fresh", "rotten"), "RT score state is invalid")
	require(result.rt_consensus.strip(), "RT critics consensus is missing")
	print(
		f"Rotten Tomatoes E2E passed: {result.imdb_id}; {result.title} ({result.year}); "
		f"Tomatometer={result.rt_tomatometer}; state={result.rt_state}"
	)


if __name__ == "__main__":
	main()

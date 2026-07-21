"""Verify the live Metacritic path against one current movie."""

# Standard Library
import sys
import pathlib


TESTS_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TESTS_DIR))

# local repo modules
import file_utils

REPO_ROOT = pathlib.Path(file_utils.get_repo_root())

# local repo modules
import slide_maker.metacritic_scraper


CURRENT_MOVIE_IMDB_ID = "tt31193180"


#============================================
def require(condition: bool, message: str) -> None:
	"""Raise a clear E2E failure when a semantic requirement is absent."""
	if condition:
		return
	raise RuntimeError(message)


#============================================
def main() -> None:
	"""Fetch a current movie and validate identity-bearing Metacritic values."""
	result = slide_maker.metacritic_scraper.fetch_metacritic_rating(
		CURRENT_MOVIE_IMDB_ID,
		"sinners",
		"Sinners",
		2025,
		["Ryan Coogler"],
	)
	require(result.imdb_id == CURRENT_MOVIE_IMDB_ID, "Metacritic IMDb identity anchor changed")
	identity_matches = (
		result.title == "Sinners",
		result.year == 2025,
		"Ryan Coogler" in result.directors,
	)
	require(sum(identity_matches) >= 2, "Metacritic resolved a different movie")
	require(0 <= result.metascore <= 100, "Metascore is outside 0-100")
	require(
		result.metascore_band in ("low", "middle", "high"),
		"Metascore display band is invalid",
	)
	require(
		result.canonical_url.startswith("https://www.metacritic.com/movie/"),
		"Metacritic canonical movie URL is invalid",
	)
	print(
		f"Metacritic E2E passed: {result.imdb_id}; "
		f"{result.title} ({result.year}); "
		f"Metascore={result.metascore}; band={result.metascore_band}"
	)


if __name__ == "__main__":
	main()

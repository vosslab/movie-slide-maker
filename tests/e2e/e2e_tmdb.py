"""Exercise live TMDB search, cross-map, details, credits, and poster retrieval."""

# Standard Library
import os
import pathlib
import tempfile
import subprocess

# Resolve the repository root before importing the production package.
repo_result = subprocess.run(
	["git", "rev-parse", "--show-toplevel"],
	check=True,
	capture_output=True,
	text=True,
)
REPO_ROOT = pathlib.Path(repo_result.stdout.strip())

# local repo modules
import slide_maker.moviedata
import slide_maker.tmdb_client


IMDB_ID = "tt31193180"
MOVIE_TITLE = "Sinners"
MOVIE_YEAR = 2025


#============================================
def main() -> None:
	"""Verify live TMDB meaning with IMDb identity as the stable anchor."""
	search_results = slide_maker.tmdb_client.search_movies(MOVIE_TITLE, MOVIE_YEAR)
	tmdb_id = slide_maker.tmdb_client.find_tmdb_id_by_imdb_id(IMDB_ID)
	matching_results = [result for result in search_results if result.tmdb_id == tmdb_id]
	assert matching_results, "TMDB title search did not include the IMDb-anchored movie"
	assert matching_results[0].year == MOVIE_YEAR, "TMDB search resolved the wrong release year"

	with tempfile.TemporaryDirectory() as temp_dir:
		movie = slide_maker.tmdb_client.fetch_movie(tmdb_id, temp_dir)
		assert movie.imdb_id == IMDB_ID, "TMDB details did not preserve the IMDb identity anchor"
		assert movie.title.strip() and movie.plot.strip(), "TMDB display text was missing"
		assert 1800 < movie.year < 3000, "TMDB release year was implausible"
		assert 0 < movie.runtime_minutes < 1000, "TMDB runtime was implausible"
		assert movie.genres and all(movie.genres), "TMDB genres were missing"
		assert movie.directors and all(movie.directors), "TMDB directors were missing"
		assert os.path.isfile(movie.poster_path), "TMDB poster was not downloaded"
		assert os.path.getsize(movie.poster_path) > 0, "TMDB poster was empty"

		# Map the provider result into the shared contract with inline values owned by later providers.
		movie_data = slide_maker.moviedata.MovieData(
			title=movie.title,
			year=movie.year,
			plot=movie.plot,
			genres=movie.genres,
			runtime_minutes=movie.runtime_minutes,
			directors=movie.directors,
			tmdb_id=movie.tmdb_id,
			imdb_id=movie.imdb_id,
			imdb_rating=5.0,
			imdb_votes=1,
			rt_tomatometer=60,
			rt_audience_score=60,
			rt_state="fresh",
			rt_consensus="Provider-specific value supplied during orchestration.",
			metascore=50,
			metascore_band="middle",
			poster_path=movie.poster_path,
		)
		slide_maker.moviedata.validate_movie_data(movie_data)

	print(f"TMDB E2E OK: {movie.title} ({movie.year}), {movie.imdb_id}")


if __name__ == "__main__":
	main()

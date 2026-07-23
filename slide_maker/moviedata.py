"""Shared movie data contract for providers and slide builders."""

# Standard Library
import os
import dataclasses

# local repo modules
import slide_maker.emoji_marks


@dataclasses.dataclass
class MovieData:
	"""Movie information assembled from the supported providers."""

	title: str
	year: int
	plot: str
	genres: list[str]
	runtime_minutes: int
	directors: list[str]
	tmdb_id: int
	imdb_id: str
	imdb_rating: float
	imdb_votes: int
	rt_tomatometer: int
	rt_audience_score: int | None
	rt_state: str
	rt_consensus: str
	metascore: int
	metascore_band: str
	poster_path: str


#============================================
def validate_movie_data(movie_data: MovieData) -> None:
	"""Validate all values required before building a movie slide.

	Args:
		movie_data: Fully assembled provider data for one movie.

	Raises:
		ValueError: A required value is empty, invalid, or inconsistent.
		FileNotFoundError: The poster path does not identify an existing file.
	"""
	if not movie_data.title.strip():
		raise ValueError("Movie title is required")
	if movie_data.year <= 0:
		raise ValueError("Movie year must be positive")
	if not movie_data.plot.strip():
		raise ValueError("Movie plot is required")
	if not movie_data.genres or any(not genre.strip() for genre in movie_data.genres):
		raise ValueError("At least one nonempty movie genre is required")
	if movie_data.runtime_minutes <= 0:
		raise ValueError("Movie runtime_minutes must be positive")
	if not movie_data.directors or any(not director.strip() for director in movie_data.directors):
		raise ValueError("At least one nonempty movie director is required")
	if movie_data.tmdb_id <= 0:
		raise ValueError("TMDB id must be positive")
	if not movie_data.imdb_id.strip():
		raise ValueError("IMDb id is required")
	if not 0.0 <= movie_data.imdb_rating <= 10.0:
		raise ValueError("IMDb rating must be between 0 and 10")
	if movie_data.imdb_votes <= 0:
		raise ValueError("IMDb votes must be positive")
	if not 0 <= movie_data.rt_tomatometer <= 100:
		raise ValueError("RT Tomatometer must be between 0 and 100")
	if (
		movie_data.rt_audience_score is not None
		and not 0 <= movie_data.rt_audience_score <= 100
	):
		raise ValueError("RT audience score must be between 0 and 100 when available")
	expected_rt_state = slide_maker.emoji_marks.rt_state_for_score(movie_data.rt_tomatometer)
	if movie_data.rt_state != expected_rt_state:
		raise ValueError(f"RT state must be {expected_rt_state!r} for this Tomatometer")
	if not movie_data.rt_consensus.strip():
		raise ValueError("RT critics consensus is required")
	if not 0 <= movie_data.metascore <= 100:
		raise ValueError("Metascore must be between 0 and 100")
	expected_metascore_band = slide_maker.emoji_marks.metascore_band_for_score(movie_data.metascore)
	if movie_data.metascore_band != expected_metascore_band:
		raise ValueError(
			f"Metascore band must be {expected_metascore_band!r} for this Metascore"
		)
	if not movie_data.poster_path.strip():
		raise ValueError("Poster path is required")
	if not os.path.isfile(movie_data.poster_path):
		raise FileNotFoundError(f"Poster file does not exist: {movie_data.poster_path}")

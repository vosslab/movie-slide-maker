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
	year: int | None = None
	plot: str = ""
	genres: list[str] = dataclasses.field(default_factory=list)
	runtime_minutes: int | None = None
	directors: list[str] = dataclasses.field(default_factory=list)
	tmdb_id: int | None = None
	imdb_id: str | None = None
	imdb_rating: float | None = None
	imdb_votes: int | None = None
	rt_tomatometer: int | None = None
	rt_audience_score: int | None = None
	rt_state: str | None = None
	rt_consensus: str = ""
	metascore: int | None = None
	metascore_band: str | None = None
	poster_path: str | None = None
	original_language: str | None = None


#============================================
def validate_movie_data(movie_data: MovieData) -> None:
	"""Validate supplied values before building an adaptable movie slide.

	Args:
		movie_data: Fully assembled provider data for one movie.

	Raises:
		ValueError: A supplied value is invalid or inconsistent.
		FileNotFoundError: A supplied poster path does not identify an existing file.
	"""
	if not movie_data.title.strip():
		raise ValueError("Movie title is required")
	if movie_data.year is not None and movie_data.year <= 0:
		raise ValueError("Movie year must be positive")
	if any(not genre.strip() for genre in movie_data.genres):
		raise ValueError("Movie genres must be nonempty when supplied")
	if movie_data.runtime_minutes is not None and movie_data.runtime_minutes <= 0:
		raise ValueError("Movie runtime_minutes must be positive")
	if any(not director.strip() for director in movie_data.directors):
		raise ValueError("Movie directors must be nonempty when supplied")
	if movie_data.tmdb_id is not None and movie_data.tmdb_id <= 0:
		raise ValueError("TMDB id must be positive")
	if movie_data.imdb_id is not None and not movie_data.imdb_id.strip():
		raise ValueError("IMDb id must be nonempty when supplied")
	if movie_data.imdb_rating is not None and not 0.0 <= movie_data.imdb_rating <= 10.0:
		raise ValueError("IMDb rating must be between 0 and 10")
	if movie_data.imdb_votes is not None and movie_data.imdb_votes < 0:
		raise ValueError("IMDb votes must be positive")
	if movie_data.rt_tomatometer is not None and not 0 <= movie_data.rt_tomatometer <= 100:
		raise ValueError("RT Tomatometer must be between 0 and 100")
	if (
		movie_data.rt_audience_score is not None
		and not 0 <= movie_data.rt_audience_score <= 100
	):
		raise ValueError("RT audience score must be between 0 and 100 when available")
	expected_rt_state = None
	if movie_data.rt_tomatometer is not None:
		expected_rt_state = slide_maker.emoji_marks.rt_state_for_score(movie_data.rt_tomatometer)
	if movie_data.rt_state is not None and movie_data.rt_state != expected_rt_state:
		raise ValueError(f"RT state must be {expected_rt_state!r} for this Tomatometer")
	if movie_data.metascore is not None and not 0 <= movie_data.metascore <= 100:
		raise ValueError("Metascore must be between 0 and 100")
	expected_metascore_band = None
	if movie_data.metascore is not None:
		expected_metascore_band = slide_maker.emoji_marks.metascore_band_for_score(movie_data.metascore)
	if movie_data.metascore_band is not None and movie_data.metascore_band != expected_metascore_band:
		raise ValueError(
			f"Metascore band must be {expected_metascore_band!r} for this Metascore"
		)
	if movie_data.poster_path is not None and not movie_data.poster_path.strip():
		raise ValueError("Poster path must be nonempty when supplied")
	if movie_data.poster_path is not None and not os.path.isfile(movie_data.poster_path):
		raise FileNotFoundError(f"Poster file does not exist: {movie_data.poster_path}")

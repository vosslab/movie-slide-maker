"""Exercise injected and live single-movie orchestration through real conversion."""

# Standard Library
import sys
import pathlib
import zipfile
import tempfile

# PIP3 modules
import PIL.Image #pillow


TESTS_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TESTS_DIR))

# local repo modules
import file_utils

REPO_ROOT = pathlib.Path(file_utils.get_repo_root())

# local repo modules
import slide_maker.rt_scraper
import slide_maker.tmdb_client
import slide_maker.imdb_ratings
import slide_maker.movie_pipeline
import slide_maker.metacritic_scraper


#============================================
def require(condition: bool, message: str) -> None:
	"""Raise a clear E2E failure when one orchestration condition is false."""
	if condition:
		return
	raise RuntimeError(message)


#============================================
def ignore_prompt(prompt: str) -> str:
	"""Reject unexpected resolver prompts in deterministic injected transitions."""
	raise RuntimeError(f"Injected resolver unexpectedly requested input: {prompt}")


#============================================
def select_first_candidate(prompt: str) -> str:
	"""Select the expected first live Her candidate without terminal input."""
	require(prompt.startswith("Choose a movie [1-"), "Live resolver emitted an unexpected prompt")
	return "1"


#============================================
def ignore_output(message: str) -> None:
	"""Consume injected pipeline progress without adding acceptance noise."""
	if not isinstance(message, str):
		raise RuntimeError("Pipeline progress output was not text")


#============================================
def injected_resolve(
	movie_input: object,
	read_choice: object,
	write_line: object,
) -> int:
	"""Return the deterministic Her TMDB identity."""
	if movie_input is None or read_choice is None or write_line is None:
		raise RuntimeError("Injected resolver inputs were incomplete")
	return 152601


#============================================
def injected_tmdb(
	tmdb_id: int,
	poster_directory: str | pathlib.Path,
) -> slide_maker.tmdb_client.TmdbMovie:
	"""Return complete TMDB-owned fields with a runtime poster."""
	require(tmdb_id == 152601, "Injected resolver returned the wrong TMDB id")
	poster_path = pathlib.Path(poster_directory) / "her_poster.png"
	poster_image = PIL.Image.new("RGB", (600, 900), color=(35, 72, 115))
	poster_image.save(poster_path)
	movie = slide_maker.tmdb_client.TmdbMovie(
		title="Her",
		year=2013,
		plot="A lonely writer develops a relationship with an operating system.",
		genres=["Drama", "Romance", "Science Fiction"],
		runtime_minutes=126,
		directors=["Spike Jonze"],
		tmdb_id=152601,
		imdb_id="tt1798709",
		poster_path=str(poster_path),
	)
	return movie


#============================================
def injected_imdb(imdb_id: str) -> slide_maker.imdb_ratings.ImdbRating:
	"""Return complete injected IMDb fields."""
	require(imdb_id == "tt1798709", "Injected IMDb call used the wrong identity")
	result = slide_maker.imdb_ratings.ImdbRating(imdb_id, "Her", 2013, 8.0, 792315)
	return result


#============================================
def validate_imdb_provider_labels() -> None:
	"""Accept differing IMDb labels when the exact provider id matches TMDB."""
	movie = slide_maker.tmdb_client.TmdbMovie(
		title="Godzilla Minus One",
		year=2023,
		plot="Japan confronts a giant monster after World War II.",
		genres=["Science Fiction"],
		runtime_minutes=124,
		directors=["Takashi Yamazaki"],
		tmdb_id=940721,
		imdb_id="tt23289160",
		poster_path="unused",
	)
	result = slide_maker.imdb_ratings.ImdbRating(
		imdb_id="tt23289160",
		title="Gojira Mainasu Wan",
		year=2024,
		imdb_rating=7.6,
		imdb_votes=228245,
	)
	slide_maker.movie_pipeline._validate_imdb_rating(result, movie)


#============================================
def injected_rt(
	imdb_id: str,
	rt_slug: str,
	expected_title: str,
	expected_year: int,
	expected_directors: list[str],
) -> slide_maker.rt_scraper.RtRating:
	"""Return complete injected Rotten Tomatoes fields."""
	require(rt_slug == "her", "Injected RT call used an unexpected slug")
	result = slide_maker.rt_scraper.RtRating(
		imdb_id=imdb_id,
		title=expected_title,
		year=expected_year,
		directors=expected_directors,
		rt_tomatometer=95,
		rt_audience_score=82,
		rt_state="fresh",
		rt_consensus="Sweet, soulful, and smart, Her imparts wisdom about relationships.",
		canonical_url="https://www.rottentomatoes.com/m/her",
	)
	return result


#============================================
def injected_metacritic(
	imdb_id: str,
	metacritic_slug: str,
	expected_title: str,
	expected_year: int,
	expected_directors: list[str],
) -> slide_maker.metacritic_scraper.MetacriticRating:
	"""Return complete injected Metacritic fields."""
	require(metacritic_slug == "her", "Injected Metacritic call used an unexpected slug")
	result = slide_maker.metacritic_scraper.MetacriticRating(
		imdb_id=imdb_id,
		title=expected_title,
		year=expected_year,
		directors=expected_directors,
		metascore=91,
		metascore_band="high",
		canonical_url="https://www.metacritic.com/movie/her/",
	)
	return result


#============================================
def incomplete_rt(
	imdb_id: str,
	rt_slug: str,
	expected_title: str,
	expected_year: int,
	expected_directors: list[str],
) -> slide_maker.rt_scraper.RtRating:
	"""Return the mandatory-field-absent injected transition."""
	result = injected_rt(
		imdb_id,
		rt_slug,
		expected_title,
		expected_year,
		expected_directors,
	)
	incomplete = slide_maker.rt_scraper.RtRating(
		imdb_id=result.imdb_id,
		title=result.title,
		year=result.year,
		directors=result.directors,
		rt_tomatometer=result.rt_tomatometer,
		rt_audience_score=result.rt_audience_score,
		rt_state=result.rt_state,
		rt_consensus="",
		canonical_url=result.canonical_url,
	)
	return incomplete


#============================================
def injected_bundle(
	rt_provider: object,
) -> slide_maker.movie_pipeline.ProviderBundle:
	"""Build one injected provider bundle for an orchestration transition."""
	if not callable(rt_provider):
		raise RuntimeError("Injected RT provider was not callable")
	bundle = slide_maker.movie_pipeline.ProviderBundle(
		resolve_tmdb_id=injected_resolve,
		fetch_tmdb_movie=injected_tmdb,
		fetch_imdb_rating=injected_imdb,
		fetch_rt_rating=rt_provider,
		fetch_metacritic_rating=injected_metacritic,
	)
	return bundle


#============================================
def validate_product(product_path: pathlib.Path, expected_title: str) -> None:
	"""Validate one product package and its displayed movie identity."""
	require(product_path.is_file(), f"Pipeline product is absent: {product_path}")
	require(product_path.stat().st_size > 0, f"Pipeline product is empty: {product_path}")
	require(zipfile.is_zipfile(product_path), f"Pipeline product is not an ODP: {product_path}")
	with zipfile.ZipFile(product_path) as archive:
		content = archive.read("content.xml").decode("utf-8")
	require(expected_title in content, f"Pipeline product is missing {expected_title!r}")
	for label in ("IMDB rating", "Critics: RT", "Audience:", "Review Summary:"):
		require(label in content, f"Pipeline product is missing label: {label}")


#============================================
def run_injected_success() -> None:
	"""Run complete injected providers through real build and LibreOffice conversion."""
	with tempfile.TemporaryDirectory() as temporary_directory:
		work_dir = pathlib.Path(temporary_directory)
		product_path = slide_maker.movie_pipeline.generate_movie_slide(
			"Her (2013)",
			work_dir,
			injected_bundle(injected_rt),
			ignore_prompt,
			ignore_output,
		)
		validate_product(product_path, "Her (2013)")
		require(not work_dir.joinpath("her_2013.pptx").exists(), "Accepted scratch PPTX remained")


#============================================
def run_injected_abort() -> None:
	"""Require a mandatory source failure before either presentation file exists."""
	with tempfile.TemporaryDirectory() as temporary_directory:
		work_dir = pathlib.Path(temporary_directory)
		try:
			slide_maker.movie_pipeline.generate_movie_slide(
				"Her (2013)",
				work_dir,
				injected_bundle(incomplete_rt),
				ignore_prompt,
				ignore_output,
			)
		except slide_maker.movie_pipeline.MoviePipelineError as error:
			diagnostic = str(error)
		else:
			raise RuntimeError("Mandatory-field-absent transition did not stop the pipeline")
		require("Rotten Tomatoes" in diagnostic, "Abort diagnostic omitted the source")
		require("'Her' (2013)" in diagnostic, "Abort diagnostic omitted the movie identity")
		require(
			"https://www.rottentomatoes.com/m/her" in diagnostic,
			"Abort diagnostic omitted the attempted URL",
		)
		require(not list(work_dir.glob("*.pptx")), "Provider abort left a PPTX")
		require(not list(work_dir.glob("*.odp")), "Provider abort left an ODP")


#============================================
def run_live_her() -> pathlib.Path:
	"""Generate and validate the live Her product in the repository root."""
	product_path = slide_maker.movie_pipeline.generate_movie_slide(
		"Her (2013)",
		REPO_ROOT,
		read_choice=select_first_candidate,
		write_line=print,
	)
	require(product_path == REPO_ROOT / "her_2013.odp", "Live product slug changed")
	validate_product(product_path, "Her (2013)")
	return product_path


#============================================
def main() -> None:
	"""Run injected success, injected abort, then the live Her product path."""
	validate_imdb_provider_labels()
	run_injected_success()
	run_injected_abort()
	product_path = run_live_her()
	print(f"Movie-pipeline orchestration E2E passed: {product_path}")


if __name__ == "__main__":
	main()

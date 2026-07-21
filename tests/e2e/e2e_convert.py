"""Convert and semantically inspect a real Her presentation."""

# Standard Library
import os
import sys
import pathlib
import tempfile

# PIP3 modules
import PIL.Image #pillow


TESTS_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TESTS_DIR))

# local repo modules
import file_utils

REPO_ROOT = pathlib.Path(file_utils.get_repo_root())

# local repo modules
import slide_maker.moviedata
import slide_maker.slide_builder
import slide_maker.slide_convert


#============================================
def require(condition: bool, message: str) -> None:
	"""Raise a clear E2E failure when a conversion condition is false."""
	if condition:
		return
	raise RuntimeError(message)


#============================================
def main() -> None:
	"""Build, convert, validate, and clean one temporary Her presentation."""
	template_path = REPO_ROOT / "template" / "movie_slide_template.pptx"
	with tempfile.TemporaryDirectory() as temporary_directory:
		work_dir = pathlib.Path(temporary_directory)
		poster_path = work_dir / "her_poster.png"
		scratch_path = work_dir / "her_2013.pptx"
		poster_image = PIL.Image.new("RGB", (600, 900), color=(35, 72, 115))
		poster_image.save(poster_path)
		movie_data = slide_maker.moviedata.MovieData(
			title="Her",
			year=2013,
			plot="A lonely writer develops an unexpected relationship with an operating system.",
			genres=["Drama", "Romance", "Science Fiction"],
			runtime_minutes=126,
			directors=["Spike Jonze"],
			tmdb_id=152601,
			imdb_id="tt1798709",
			imdb_rating=8.0,
			imdb_votes=792315,
			rt_tomatometer=95,
			rt_state="fresh",
			rt_consensus="Sweet, soulful, and smart, Her uses its scenario to impart wisdom.",
			metascore=91,
			metascore_band="high",
			poster_path=str(poster_path),
		)
		slide_maker.slide_builder.build_movie_presentation(
			movie_data,
			template_path,
			scratch_path,
		)
		original_directory = pathlib.Path.cwd()
		os.chdir(work_dir)
		output_path = slide_maker.slide_convert.convert_presentation(
			scratch_path,
			pathlib.Path("her_2013.odp"),
		)
		os.chdir(original_directory)
		product_path = work_dir / output_path
		require(product_path.is_file(), "Converter did not write ./her_2013.odp")
		require(not scratch_path.exists(), "Converter retained the accepted scratch PPTX")
		require(product_path.stat().st_size > 0, "Converter wrote an empty ODP")
		print(f"Presentation-conversion E2E passed: {product_path}")


if __name__ == "__main__":
	main()

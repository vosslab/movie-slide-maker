"""Generate the live Her movie deck through the public pipeline."""

# Standard Library
import sys
import pathlib
import zipfile


TESTS_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TESTS_DIR))

# local repo modules
import file_utils

REPO_ROOT = pathlib.Path(file_utils.get_repo_root())

# local repo modules
import slide_maker.movie_pipeline


#============================================
def require(condition: bool, message: str) -> None:
	"""Raise a clear E2E failure when the live product is invalid."""
	if condition:
		return
	raise RuntimeError(message)


#============================================
def select_first_candidate(prompt: str) -> str:
	"""Select the expected first live Her candidate without terminal input."""
	require(prompt.startswith("Choose a movie [1-"), "Live resolver emitted an unexpected prompt")
	return "1"


#============================================
def validate_product(product_path: pathlib.Path) -> None:
	"""Validate one published live movie product."""
	require(product_path.is_file(), f"Pipeline product is absent: {product_path}")
	require(product_path.stat().st_size > 0, f"Pipeline product is empty: {product_path}")
	require(zipfile.is_zipfile(product_path), f"Pipeline product is not an ODP: {product_path}")
	with zipfile.ZipFile(product_path) as archive:
		content = archive.read("content.xml").decode("utf-8")
	require("Her (2013)" in content, "Pipeline product is missing the selected movie")


#============================================
def main() -> None:
	"""Run the public live pipeline without interactive terminal input."""
	product_path = slide_maker.movie_pipeline.generate_movie_slide(
		"Her (2013)",
		REPO_ROOT,
		read_choice=select_first_candidate,
		write_line=print,
	)
	validate_product(product_path)
	print(f"Movie-pipeline orchestration E2E passed: {product_path}")


if __name__ == "__main__":
	main()

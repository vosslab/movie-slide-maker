#!/usr/bin/env python3
"""Capture the current review deck and Jurassic Park guidance screenshots."""

# Standard Library
import pathlib
import shutil
import tempfile
import subprocess
import dataclasses

# PIP3 modules
import PIL.Image
import pptx

# Resolve the repository root before importing the production package.
repo_result = subprocess.run(
	["git", "rev-parse", "--show-toplevel"],
	check=True,
	capture_output=True,
	text=True,
)
REPO_ROOT = pathlib.Path(repo_result.stdout.strip())

# local repo modules
import slide_maker.libreoffice_runner
import slide_maker.movie_pipeline
import slide_maker.review_deck
import slide_maker.slide_builder
import slide_maker.slide_convert


SCREENSHOT_DIRECTORY = REPO_ROOT / "docs" / "screenshots"
JURASSIC_SOURCE_PATH = (
	REPO_ROOT / "output_smoke" / "guidance_live" / "jurassic_park_1993.odp"
)
REVIEW_OUTPUT_NAMES = {
	"Her": "movie_slide_her.webp",
	"Cooties": "movie_slide_cooties.webp",
	"Parasite": "movie_slide_parasite.webp",
	"A Ghost Waits": "movie_slide_a_ghost_waits.webp",
}
SUMMARY_REQUESTS = tuple(
	request
	for request in slide_maker.review_deck.DEFAULT_REQUESTS
	if request.title in REVIEW_OUTPUT_NAMES
)
JURASSIC_OUTPUT_NAMES = (
	"movie_slide_jurassic_park.webp",
	"guidance_csm_overview.webp",
	"guidance_csm_categories.webp",
	"guidance_imdb.webp",
)


#============================================
def require(condition: bool, message: str) -> None:
	"""Raise a clear capture error when an expected artifact is absent."""
	if condition:
		return
	raise RuntimeError(message)


#============================================
def render_pdf_pages(pdf_path: pathlib.Path, work_directory: pathlib.Path) -> tuple[pathlib.Path, ...]:
	"""Render every PDF page as a deterministic numbered PNG under ``_temp``."""
	prefix = work_directory / pdf_path.stem
	command = ["pdftoppm", "-png", "-r", "150", str(pdf_path), str(prefix)]
	result = subprocess.run(command, capture_output=True, text=True, check=False)
	require(result.returncode == 0, result.stderr.strip() or "pdftoppm failed")
	pages = tuple(
		sorted(
			work_directory.glob(f"{pdf_path.stem}-*.png"),
			key=lambda path: int(path.stem.rsplit("-", maxsplit=1)[1]),
		)
	)
	require(bool(pages), f"PDF render produced no pages: {pdf_path}")
	return pages


#============================================
def encode_webp(
	source_path: pathlib.Path,
	output_name: str,
	work_directory: pathlib.Path,
) -> tuple[int, int, int]:
	"""Bound one PNG, encode it at quality 90, and publish the inspected WebP."""
	processed_path = work_directory / f"{output_name}.png"
	with PIL.Image.open(source_path) as image:
		width, height = image.size
		if max(width, height) > 1920:
			image.thumbnail((1920, 1920))
			image.save(processed_path)
		else:
			shutil.copy2(source_path, processed_path)
	temporary_webp = work_directory / output_name
	command = ["cwebp", "-q", "90", str(processed_path), "-o", str(temporary_webp)]
	result = subprocess.run(command, capture_output=True, text=True, check=False)
	require(result.returncode == 0, result.stderr.strip() or "cwebp failed")
	with PIL.Image.open(temporary_webp) as image:
		width, height = image.size
		require(max(width, height) <= 1920, f"Screenshot exceeds 1920 px: {output_name}")
		format_name = image.format
	require(format_name == "WEBP", f"Screenshot is not WebP: {output_name}")
	file_size = temporary_webp.stat().st_size
	require(file_size <= 1_000_000, f"Screenshot exceeds 1 MB: {output_name}")
	SCREENSHOT_DIRECTORY.mkdir(parents=True, exist_ok=True)
	shutil.copy2(temporary_webp, SCREENSHOT_DIRECTORY / output_name)
	return width, height, file_size


#============================================
def build_summary_only_deck(
	work_directory: pathlib.Path,
) -> tuple[tuple[str, pathlib.Path], ...]:
	"""Build live summary slides without the optional multi-page guidance section."""
	poster_directory = work_directory / "summary_posters"
	poster_directory.mkdir()
	providers = dataclasses.replace(
		slide_maker.movie_pipeline.LIVE_PROVIDERS,
		fetch_csm_guidance=None,
		fetch_imdb_guidance=None,
	)
	accepted_movies, failures = slide_maker.review_deck.resolve_requests(
		SUMMARY_REQUESTS,
		poster_directory,
		providers,
		print,
	)
	require(not failures, f"Summary capture source failures: {failures!r}")
	accepted_titles = {movie_data.title for unused_request, movie_data in accepted_movies}
	missing_titles = sorted(set(REVIEW_OUTPUT_NAMES) - accepted_titles)
	require(not missing_titles, f"Summary capture omitted movies: {', '.join(missing_titles)}")
	template_path = REPO_ROOT / "template" / "movie_slide_template.pptx"
	presentation = pptx.Presentation(template_path)
	for unused_request, movie_data in accepted_movies:
		slide_maker.slide_builder.append_movie_slide(presentation, movie_data)
	scratch_path = work_directory / "review_summaries.pptx"
	presentation.save(scratch_path)
	output_path = work_directory / "review_summaries.odp"
	slide_maker.slide_convert.convert_presentation(
		scratch_path,
		output_path,
		expected_movie_slides=len(accepted_movies),
	)
	page_paths = slide_maker.review_deck.render_deck_pages(
		output_path,
		work_directory / "review_summary_pages",
		len(accepted_movies),
	)
	pairs = tuple(
		(movie_data.title, page_path)
		for (unused_request, movie_data), page_path in zip(
			accepted_movies,
			page_paths,
			strict=True,
		)
	)
	return pairs


#============================================
def capture_review_deck(work_directory: pathlib.Path) -> dict[str, tuple[int, int, int]]:
	"""Build the live summary views while keeping optional guidance separate."""
	summary_pages = dict(build_summary_only_deck(work_directory))
	records = {}
	for title, output_name in REVIEW_OUTPUT_NAMES.items():
		source_path = summary_pages[title]
		records[output_name] = encode_webp(source_path, output_name, work_directory)
	return records


#============================================
def capture_jurassic_guidance(work_directory: pathlib.Path) -> dict[str, tuple[int, int, int]]:
	"""Export the current Jurassic Park ODP headlessly and retain four useful views."""
	if JURASSIC_SOURCE_PATH.is_file():
		source_path = JURASSIC_SOURCE_PATH
	else:
		# A fresh checkout has no ignored smoke artifact, so recreate it through
		# the same public pipeline that produces ordinary movie decks.
		source_path = slide_maker.movie_pipeline.generate_movie_slide(
			"tt0107290",
			work_directory / "jurassic_source",
		)
	pdf_directory = work_directory / "jurassic_pdf"
	conversion = slide_maker.libreoffice_runner.convert_document(
		source_path,
		"pdf",
		pdf_directory,
		work_directory / "jurassic_lo_profile",
	)
	diagnostic = conversion.stderr.strip() or conversion.stdout.strip()
	require(conversion.returncode == 0, f"Jurassic Park PDF export failed: {diagnostic}")
	pdf_path = pdf_directory / "jurassic_park_1993.pdf"
	require(pdf_path.is_file(), f"Jurassic Park PDF is absent: {pdf_path}")
	pages = render_pdf_pages(pdf_path, work_directory)
	require(len(pages) >= 4, f"Jurassic Park export has {len(pages)} pages; expected at least four")
	records = {}
	for output_name, source_path in zip(JURASSIC_OUTPUT_NAMES, pages[:4], strict=True):
		records[output_name] = encode_webp(source_path, output_name, work_directory)
	return records


#============================================
def print_records(records: dict[str, tuple[int, int, int]]) -> None:
	"""Print the exact published image dimensions and byte sizes for the receipt."""
	for output_name, (width, height, file_size) in sorted(records.items()):
		print(f"{output_name}: {width}x{height}, {file_size} bytes")


#============================================
def main() -> None:
	"""Regenerate all README visual evidence without editing the README itself."""
	temporary_parent = REPO_ROOT / "_temp"
	temporary_parent.mkdir(exist_ok=True)
	with tempfile.TemporaryDirectory(prefix="readme_capture_", dir=temporary_parent) as directory_name:
		work_directory = pathlib.Path(directory_name)
		review_records = capture_review_deck(work_directory)
		jurassic_records = capture_jurassic_guidance(work_directory)
	records = review_records | jurassic_records
	print_records(records)


if __name__ == "__main__":
	main()

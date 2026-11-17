"""Build, convert, and render editable parental-guidance movie sections."""

# Standard Library
import sys
import pathlib
import tempfile
import subprocess
import zipfile

# PIP3 modules
import pptx
import PIL.Image #pillow


TESTS_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TESTS_DIR))

# local repo modules
import file_utils

REPO_ROOT = pathlib.Path(file_utils.get_repo_root())

# local repo modules
import slide_maker.moviedata
import slide_maker.parental_guidance
import slide_maker.libreoffice_runner
import slide_maker.slide_builder
import slide_maker.slide_convert


OUTPUT_DIRECTORY = REPO_ROOT / "output_smoke" / "guidance"
OUTPUT_PATH = OUTPUT_DIRECTORY / "guidance.odp"


#============================================
def require(condition: bool, message: str) -> None:
	"""Raise a clear E2E failure when guidance output is not student-ready."""
	if condition:
		return
	raise RuntimeError(message)


#============================================
def csm_guidance() -> slide_maker.parental_guidance.SourceGuidance:
	"""Return inline Common Sense guidance with warning and positive categories."""
	categories = (
		slide_maker.parental_guidance.GuidanceCategory("Violence & Scariness", 4),
		slide_maker.parental_guidance.GuidanceCategory("Language", 2),
		slide_maker.parental_guidance.GuidanceCategory("Sex, Romance & Nudity", 1),
		slide_maker.parental_guidance.GuidanceCategory("Drinking, Drugs & Smoking", 1),
		slide_maker.parental_guidance.GuidanceCategory("Positive Messages", 3),
		slide_maker.parental_guidance.GuidanceCategory("Positive Role Models", 2),
		slide_maker.parental_guidance.GuidanceCategory("Diverse Representations", None),
	)
	guide = slide_maker.parental_guidance.SourceGuidance(
		provider="Common Sense Media",
		url="https://www.commonsensemedia.org/movie-reviews/cooties",
		age="age 17+",
		certificate="R",
		overview=(
			"This synthetic course example has violence, strong language, and adult material. "
			"Students should decide whether the content is appropriate before viewing."
		),
		categories=categories,
	)
	return guide


#============================================
def imdb_guidance() -> slide_maker.parental_guidance.SourceGuidance:
	"""Return inline non-spoiler IMDb-style category records."""
	categories = (
		slide_maker.parental_guidance.GuidanceCategory(
			"Sex & Nudity", severity="Mild", example="Brief adult flirtation appears.",
		),
		slide_maker.parental_guidance.GuidanceCategory(
			"Violence & Gore", severity="Severe", example="Zombie attacks include bloody injuries.",
		),
		slide_maker.parental_guidance.GuidanceCategory(
			"Profanity", severity="Severe", example="Frequent strong profanity is used.",
		),
		slide_maker.parental_guidance.GuidanceCategory(
			"Alcohol, Drugs & Smoking", severity="Mild", example="Drug use is referenced.",
		),
		slide_maker.parental_guidance.GuidanceCategory(
			"Frightening & Intense Scenes", severity="Moderate", example="Threatening scenes may upset viewers.",
		),
	)
	guide = slide_maker.parental_guidance.SourceGuidance(
		provider="IMDb Parents' Guide",
		url="https://www.imdb.com/title/tt2490326/parentalguide/",
		categories=categories,
	)
	return guide


#============================================
def movie_cases(poster_path: pathlib.Path) -> tuple[slide_maker.moviedata.MovieData, ...]:
	"""Return one full and one unavailable guidance section for variable page counts."""
	complete_guidance = slide_maker.parental_guidance.ParentalGuidance(
		csm=csm_guidance(),
		imdb=imdb_guidance(),
	)
	complete = slide_maker.moviedata.MovieData(
		title="Cooties",
		year=2014,
		plot="Teachers face a fast-moving outbreak at an elementary school.",
		tmdb_id=237139,
		imdb_id="tt2490326",
		poster_path=str(poster_path),
		guidance=complete_guidance,
	)
	unavailable = slide_maker.moviedata.MovieData(
		title="Guidance Gap",
		year=2026,
		tmdb_id=42,
		poster_path=str(poster_path),
		guidance=slide_maker.parental_guidance.ParentalGuidance(
			diagnostics=("Common Sense Media: unavailable", "IMDb: unavailable"),
		),
	)
	return complete, unavailable


#============================================
def visible_texts(odp_path: pathlib.Path) -> list[str]:
	"""Return normalized text from every visible ODP page in display order."""
	with zipfile.ZipFile(odp_path) as archive:
		content_root = slide_maker.slide_convert.parse_xml(archive, "content.xml")
		pages = slide_maker.slide_convert.visible_pages(content_root)
		texts = [slide_maker.slide_convert.odf_text(page) for page in pages]
	return texts


#============================================
def render_pages(odp_path: pathlib.Path) -> tuple[pathlib.Path, ...]:
	"""Render every guidance ODP page to a retained PNG for visual inspection."""
	with tempfile.TemporaryDirectory() as temporary_directory:
		work_dir = pathlib.Path(temporary_directory)
		result = slide_maker.libreoffice_runner.convert_document(
			odp_path,
			"pdf",
			work_dir,
			work_dir / "libreoffice_profile",
		)
		diagnostic = result.stderr.strip() or result.stdout.strip() or "no command diagnostic"
		require(result.returncode == 0, f"Guidance PDF render failed: {diagnostic}")
		pdf_path = work_dir / f"{odp_path.stem}.pdf"
		require(pdf_path.is_file(), "Guidance PDF was not created")
		page_count = int(subprocess.run(
			["pdfinfo", str(pdf_path)], capture_output=True, text=True, check=True,
		).stdout.split("Pages:")[1].splitlines()[0].strip())
		paths = []
		for number in range(1, page_count + 1):
			path = OUTPUT_DIRECTORY / f"guidance_{number:02d}.png"
			result = subprocess.run(
				[
					"pdftoppm", "-png", "-singlefile", "-f", str(number), "-l", str(number),
					"-r", "150", str(pdf_path), str(path.with_suffix("")),
				],
				capture_output=True,
				text=True,
				check=False,
			)
			require(result.returncode == 0 and path.is_file(), f"Guidance page {number} did not render")
			paths.append(path)
	result = tuple(paths)
	return result


#============================================
def main() -> None:
	"""Build two sections, then confirm semantic conversion and retained renders."""
	template_path = REPO_ROOT / "template" / "movie_slide_template.pptx"
	OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
	with tempfile.TemporaryDirectory() as temporary_directory:
		work_dir = pathlib.Path(temporary_directory)
		poster_path = work_dir / "poster.png"
		PIL.Image.new("RGB", (600, 900), color=(35, 72, 115)).save(poster_path)
		cases = movie_cases(poster_path)
		scratch_path = work_dir / "guidance.pptx"
		presentation = pptx.Presentation(template_path)
		for movie_data in cases:
			slide_maker.slide_builder.append_movie_section(presentation, movie_data)
		presentation.save(scratch_path)
		slide_maker.slide_convert.convert_presentation(scratch_path, OUTPUT_PATH, len(cases))
	require(OUTPUT_PATH.is_file(), "Guidance ODP is absent")
	texts = visible_texts(OUTPUT_PATH)
	combined = "\n".join(texts)
	for fragment in (
		"TMDB: https://www.themoviedb.org/movie/237139",
		"Common Sense Media: Cooties",
		"Content guidance",
		"Positive content",
		"IMDb Parents' Guide: Cooties",
		"Selected non-spoiler example",
		"Current parental-guidance sources were unavailable.",
	):
		require(fragment in combined, f"Guidance conversion omitted {fragment!r}")
	page_paths = render_pages(OUTPUT_PATH)
	require(len(page_paths) == len(texts), "Guidance render page count differs from ODP page count")
	print(f"Guidance E2E passed: {OUTPUT_PATH}")
	print(f"Guidance renders retained: {OUTPUT_DIRECTORY}")


if __name__ == "__main__":
	main()

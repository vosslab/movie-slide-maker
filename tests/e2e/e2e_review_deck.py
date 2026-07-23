"""Run and semantically accept the live default movie review deck."""

# Standard Library
import sys
import pathlib
import zipfile
import xml.etree.ElementTree

# PIP3 modules
import PIL.Image #pillow
import PIL.ImageStat #pillow


TESTS_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TESTS_DIR))

# local repo modules
import file_utils

REPO_ROOT = pathlib.Path(file_utils.get_repo_root())

# local repo modules
import slide_maker.review_deck
import slide_maker.slide_builder
import slide_maker.slide_convert


EXPECTED_REQUEST_IDENTITIES = (
	"Her (2013)",
	"Cooties (2014)",
	"It (2017)",
	"Sinners (2025)",
	"A Ghost Waits (2020)",
)
EXPECTED_OUTPUT_PATH = REPO_ROOT / "output_smoke" / "review_deck.odp"
EXPECTED_PAGE_DIRECTORY = REPO_ROOT / "output_smoke" / "review_deck_pages"


#============================================
def require(condition: bool, message: str) -> None:
	"""Raise a clear E2E failure when one batch acceptance condition is false."""
	if condition:
		return
	raise RuntimeError(message)


#============================================
def capture_progress(message: str) -> None:
	"""Print live batch progress without supplying any terminal input callback."""
	require(isinstance(message, str), "Review-deck progress output was not text")
	print(message)


#============================================
def validate_default_requests() -> dict[str, slide_maker.review_deck.ReviewMovieRequest]:
	"""Require the built-in batch identities and their exact deterministic order."""
	requests = slide_maker.review_deck.DEFAULT_REQUESTS
	identities = tuple(request.identity for request in requests)
	require(identities == EXPECTED_REQUEST_IDENTITIES, "Default review movie order changed")
	request_map = {request.identity: request for request in requests}
	require(len(request_map) == len(requests), "Default review movie identities are duplicated")
	return request_map


#============================================
def validate_result_accounting(
	result: slide_maker.review_deck.ReviewDeckResult,
	request_map: dict[str, slide_maker.review_deck.ReviewMovieRequest],
) -> None:
	"""Match every requested movie to exactly one accepted page or source failure."""
	accepted_identities = tuple(record.requested_identity for record in result.accepted)
	failure_identities = tuple(record.requested_identity for record in result.failures)
	accounted_identities = accepted_identities + failure_identities
	require(
		len(accounted_identities) == len(set(accounted_identities)),
		"A review movie was accounted more than once",
	)
	require(
		set(accounted_identities) == set(request_map),
		"Review result did not account for every default movie",
	)
	expected_accepted = tuple(
		identity for identity in EXPECTED_REQUEST_IDENTITIES
		if identity in accepted_identities
	)
	expected_failures = tuple(
		identity for identity in EXPECTED_REQUEST_IDENTITIES
		if identity in failure_identities
	)
	require(accepted_identities == expected_accepted, "Accepted review movies changed request order")
	require(failure_identities == expected_failures, "Rejected review movies changed request order")
	require(bool(result.accepted), "Live review batch produced no accepted movies")
	page_numbers = tuple(record.page_number for record in result.accepted)
	expected_page_numbers = tuple(range(1, len(result.accepted) + 1))
	require(page_numbers == expected_page_numbers, "Accepted review page numbers are not contiguous")
	require(len(result.page_paths) == len(result.accepted), "Accepted and rendered page counts differ")


#============================================
def validate_failures(
	result: slide_maker.review_deck.ReviewDeckResult,
	request_map: dict[str, slide_maker.review_deck.ReviewMovieRequest],
) -> None:
	"""Require every rejection to retain source, original identity, and context."""
	for failure in result.failures:
		request = request_map[failure.requested_identity]
		diagnostic = failure.diagnostic
		require(bool(failure.source.strip()), f"Failure source is absent for {request.identity}")
		require(bool(diagnostic.strip()), f"Failure diagnostic is absent for {request.identity}")
		require(
			failure.source.casefold() in diagnostic.casefold(),
			f"Failure diagnostic omitted source for {request.identity}",
		)
		require(
			request.title.casefold() in diagnostic.casefold(),
			f"Failure diagnostic omitted title for {request.identity}",
		)
		require(
			str(request.year) in diagnostic,
			f"Failure diagnostic omitted year for {request.identity}",
		)


#============================================
def validate_page_semantics(
	archive: zipfile.ZipFile,
	page: xml.etree.ElementTree.Element,
	record: slide_maker.review_deck.ReviewDeckAccepted,
) -> None:
	"""Validate identity, mandatory labels, and poster payload for one ODP page."""
	frames = slide_maker.slide_convert.named_frames(page)
	title_role = slide_maker.slide_builder.TEMPLATE_TITLE_NAME
	outline_role = slide_maker.slide_builder.TEMPLATE_OUTLINE_NAME
	title_text = slide_maker.slide_convert.normalized_frame_text(frames[title_role])
	outline_text = slide_maker.slide_convert.normalized_frame_text(frames[outline_role])
	expected_title = f"{record.title} ({record.year})"
	require(title_text == expected_title, f"Review page changed movie identity: {title_text}")
	for field in slide_maker.slide_convert.REQUIRED_FIELDS:
		require(outline_text.count(field) == 1, f"{expected_title} does not contain one {field!r} label")
	slide_maker.slide_convert.validate_poster(archive, page)


#============================================
def validate_deck(
	result: slide_maker.review_deck.ReviewDeckResult,
) -> None:
	"""Validate accepted-page count, order, semantic meaning, and poster packages."""
	output_path = pathlib.Path(result.output_path).resolve()
	require(output_path == EXPECTED_OUTPUT_PATH.resolve(), "Review deck output path changed")
	require(output_path.is_file(), "Review deck ODP is absent")
	require(output_path.stat().st_size > 0, "Review deck ODP is empty")
	require(zipfile.is_zipfile(output_path), "Review deck output is not an ODP package")
	with zipfile.ZipFile(output_path) as archive:
		content_root = slide_maker.slide_convert.parse_xml(archive, "content.xml")
		styles_root = slide_maker.slide_convert.parse_xml(archive, "styles.xml")
		pages = slide_maker.slide_convert.movie_pages(content_root, len(result.accepted))
		require(len(pages) == len(result.page_paths), "ODP, accepted, and PNG page counts differ")
		page_titles = []
		for page, record in zip(pages, result.accepted, strict=True):
			slide_maker.slide_convert.validate_page_size(page, styles_root)
			validate_page_semantics(archive, page, record)
			page_titles.append(f"{record.title} ({record.year})")
	for title in page_titles:
		require(page_titles.count(title) == 1, f"Accepted movie occurs more than once: {title}")


#============================================
def validate_page_renders(
	result: slide_maker.review_deck.ReviewDeckResult,
) -> None:
	"""Require one ordered, nonempty, landscape, nonblank PNG per accepted page."""
	for record, page_path_value in zip(result.accepted, result.page_paths, strict=True):
		page_path = pathlib.Path(page_path_value)
		expected_name = f"slide_{record.page_number:02d}.png"
		require(
			page_path.resolve().parent == EXPECTED_PAGE_DIRECTORY.resolve(),
			"Review page render directory changed",
		)
		require(page_path.name == expected_name, f"Review page render name changed: {page_path.name}")
		require(page_path.is_file(), f"Review page render is absent: {page_path}")
		require(page_path.stat().st_size > 0, f"Review page render is empty: {page_path}")
		with PIL.Image.open(page_path) as page_image:
			page_image.load()
			require(page_image.format == "PNG", f"Review page render is not PNG: {page_path}")
			require(page_image.width > page_image.height, f"Review page is not landscape: {page_path}")
			statistics = PIL.ImageStat.Stat(page_image.convert("RGB"))
			require(max(statistics.var) > 1.0, f"Review page pixels are effectively blank: {page_path}")


#============================================
def main() -> None:
	"""Run the live no-input default batch and accept all returned evidence."""
	request_map = validate_default_requests()
	result = slide_maker.review_deck.build_review_deck(write_line=capture_progress)
	validate_result_accounting(result, request_map)
	validate_failures(result, request_map)
	validate_deck(result)
	validate_page_renders(result)
	print(
		f"Review-deck E2E passed: {len(result.accepted)} accepted, "
		f"{len(result.failures)} rejected, {result.output_path}"
	)


if __name__ == "__main__":
	main()

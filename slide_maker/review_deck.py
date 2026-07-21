"""Build and self-check the deterministic multi-movie review deck."""

# Standard Library
import os
import re
import pathlib
import zipfile
import tempfile
import subprocess
import dataclasses
import collections.abc

# PIP3 modules
import pptx

# local repo modules
import slide_maker.config
import slide_maker.moviedata
import slide_maker.rt_scraper
import slide_maker.tmdb_client
import slide_maker.imdb_ratings
import slide_maker.slide_builder
import slide_maker.slide_convert
import slide_maker.movie_pipeline
import slide_maker.movie_resolver
import slide_maker.metacritic_scraper


@dataclasses.dataclass(frozen=True, slots=True)
class ReviewMovieRequest:
	"""Identify one movie requested for the deterministic review batch."""

	title: str
	year: int

	@property
	def identity(self) -> str:
		"""Return the original title-and-year request used in diagnostics."""
		identity = f"{self.title} ({self.year})"
		return identity


@dataclasses.dataclass(frozen=True, slots=True)
class ReviewDeckAccepted:
	"""Record one accepted movie and its one-based output page number."""

	requested_identity: str
	title: str
	year: int
	page_number: int


@dataclasses.dataclass(frozen=True, slots=True)
class ReviewDeckFailure:
	"""Record one rejected request with its source-specific diagnostic."""

	source: str
	requested_identity: str
	diagnostic: str


@dataclasses.dataclass(frozen=True, slots=True)
class ReviewDeckResult:
	"""Return the review-deck product and structured per-request accounting."""

	output_path: pathlib.Path
	accepted: tuple[ReviewDeckAccepted, ...]
	failures: tuple[ReviewDeckFailure, ...]
	page_paths: tuple[pathlib.Path, ...]


DEFAULT_REQUESTS = (
	ReviewMovieRequest("Her", 2013),
	ReviewMovieRequest("Cooties", 2014),
	ReviewMovieRequest("It", 2017),
	ReviewMovieRequest("Sinners", 2025),
	ReviewMovieRequest("A Ghost Waits", 2020),
)
DEFAULT_OUTPUT_PATH = pathlib.Path("output_smoke/review_deck.odp")
PAGE_FILENAME_PATTERN = re.compile(r"slide_[0-9]{2}\.png")


class ReviewDeckError(RuntimeError):
	"""Report a review-deck build, render, or accounting failure."""


class DeterministicResolverIO:
	"""Select the exact requested title and year without reading stdin."""

	def __init__(
		self,
		request: ReviewMovieRequest,
		write_line: collections.abc.Callable[[str], None],
	) -> None:
		"""Store one request and the resolver menu lines written for it."""
		self.request = request
		self.write_line_target = write_line
		self.messages: list[str] = []

	def write_line(self, message: str) -> None:
		"""Capture resolver output while forwarding it to the batch reporter."""
		self.messages.append(message)
		self.write_line_target(message)

	def read_choice(self, prompt: str) -> str:
		"""Return the menu number whose identity exactly matches the request."""
		self.write_line_target(prompt.rstrip())
		label_pattern = re.compile(
			rf"^([0-9]+)\. {re.escape(self.request.title)} "
			rf"\({self.request.year}\) \[TMDB [0-9]+\]$",
			re.IGNORECASE,
		)
		for message in self.messages:
			match = label_pattern.fullmatch(message)
			if match is not None:
				choice = match.group(1)
				return choice
		raise slide_maker.movie_resolver.MovieResolutionError(
			f"TMDB resolver menu omitted requested identity {self.request.identity}"
		)


#============================================
def require(condition: bool, message: str) -> None:
	"""Raise a review-deck error when one acceptance condition is false."""
	if condition:
		return
	raise ReviewDeckError(message)


#============================================
def failure_source(error: BaseException) -> str:
	"""Return the provider or pipeline boundary named by an expected failure."""
	if isinstance(error, slide_maker.movie_resolver.MovieResolutionError):
		source = "TMDB resolver"
	elif isinstance(error, slide_maker.tmdb_client.TmdbSourceError):
		source = "TMDB"
	elif isinstance(error, slide_maker.imdb_ratings.ImdbSourceError):
		source = "IMDb"
	elif isinstance(error, slide_maker.rt_scraper.RtSourceError):
		source = "Rotten Tomatoes"
	elif isinstance(error, slide_maker.metacritic_scraper.MetacriticSourceError):
		source = "Metacritic"
	elif isinstance(error, slide_maker.movie_pipeline.MoviePipelineError):
		message = str(error)
		match = re.match(r"^(.+?) source error\b", message)
		source = match.group(1) if match is not None else "movie pipeline"
	else:
		source = "movie contract"
	return source


#============================================
def resolve_request(
	request: ReviewMovieRequest,
	poster_directory: pathlib.Path,
	providers: slide_maker.movie_pipeline.ProviderBundle,
	write_line: collections.abc.Callable[[str], None],
) -> slide_maker.moviedata.MovieData:
	"""Resolve one exact request without exposing a terminal-input dependency."""
	resolver_io = DeterministicResolverIO(request, write_line)
	movie_data = slide_maker.movie_pipeline.resolve_movie_data(
		request.identity,
		poster_directory,
		providers,
		resolver_io.read_choice,
		resolver_io.write_line,
	)
	if (
		movie_data.title.casefold() != request.title.casefold()
		or movie_data.year != request.year
	):
		raise slide_maker.movie_resolver.MovieResolutionError(
			f"Requested {request.identity} resolved as "
			f"{movie_data.title} ({movie_data.year})"
		)
	return movie_data


#============================================
def resolve_requests(
	requests: tuple[ReviewMovieRequest, ...],
	poster_directory: pathlib.Path,
	providers: slide_maker.movie_pipeline.ProviderBundle,
	write_line: collections.abc.Callable[[str], None],
) -> tuple[
	list[tuple[ReviewMovieRequest, slide_maker.moviedata.MovieData]],
	list[ReviewDeckFailure],
]:
	"""Resolve the batch while retaining expected source failures by identity."""
	accepted = []
	failures = []
	expected_errors = (
		slide_maker.movie_pipeline.MoviePipelineError,
		slide_maker.movie_resolver.MovieResolutionError,
		slide_maker.tmdb_client.TmdbSourceError,
		slide_maker.imdb_ratings.ImdbSourceError,
		slide_maker.rt_scraper.RtSourceError,
		slide_maker.metacritic_scraper.MetacriticSourceError,
	)
	for request in requests:
		write_line(f"Review deck: resolving {request.identity}")
		try:
			movie_data = resolve_request(request, poster_directory, providers, write_line)
		except expected_errors as error:
			source = failure_source(error)
			diagnostic = f"{source} failure for {request.identity}: {error}"
			failure = ReviewDeckFailure(source, request.identity, diagnostic)
			failures.append(failure)
			write_line(diagnostic)
			continue
		accepted.append((request, movie_data))
	return accepted, failures


#============================================
def build_scratch_deck(
	accepted_movies: list[tuple[ReviewMovieRequest, slide_maker.moviedata.MovieData]],
	template_path: pathlib.Path,
	scratch_path: pathlib.Path,
) -> pathlib.Path:
	"""Append all accepted movies to one template-backed presentation."""
	require(template_path.is_file(), f"Movie slide template is absent: {template_path}")
	presentation = pptx.Presentation(template_path)
	for request, movie_data in accepted_movies:
		# Request identity has already been paired to the provider result.
		require(
			movie_data.title.casefold() == request.title.casefold()
			and movie_data.year == request.year,
			f"Accepted movie identity changed before build: {request.identity}",
		)
		slide_maker.slide_builder.append_movie_slide(presentation, movie_data)
	scratch_path.parent.mkdir(parents=True, exist_ok=True)
	presentation.save(scratch_path)
	return scratch_path


#============================================
def validate_deck_identities(
	output_path: pathlib.Path,
	accepted_movies: list[tuple[ReviewMovieRequest, slide_maker.moviedata.MovieData]],
) -> None:
	"""Check converted page identities, order, and mandatory displayed fields."""
	with zipfile.ZipFile(output_path) as archive:
		content_root = slide_maker.slide_convert.parse_xml(archive, "content.xml")
		pages = slide_maker.slide_convert.movie_pages(content_root, len(accepted_movies))
		converted_identities = []
		for page in pages:
			frames = slide_maker.slide_convert.named_frames(page)
			slide_maker.slide_convert.validate_displayed_fields(page)
			title_frame = frames[slide_maker.slide_builder.TEMPLATE_TITLE_NAME]
			identity = slide_maker.slide_convert.normalized_frame_text(title_frame)
			converted_identities.append(identity)
	expected_identities = [
		f"{movie_data.title} ({movie_data.year})"
		for request, movie_data in accepted_movies
	]
	require(
		converted_identities == expected_identities,
		f"Converted review-deck identity/order mismatch: {converted_identities!r}",
	)
	require(
		len(set(converted_identities)) == len(converted_identities),
		"Converted review deck contains a duplicate accepted movie identity",
	)


#============================================
def run_command(command: list[str], failure_message: str) -> subprocess.CompletedProcess[str]:
	"""Run one render command and retain a concise failure diagnostic."""
	result = subprocess.run(command, capture_output=True, text=True, check=False)
	diagnostic = result.stderr.strip() or result.stdout.strip() or "no command diagnostic"
	require(result.returncode == 0, f"{failure_message}: {diagnostic}")
	return result


#============================================
def pdf_page_count(pdf_path: pathlib.Path) -> int:
	"""Read the exact rendered PDF page count from Poppler metadata."""
	result = run_command(["pdfinfo", str(pdf_path)], "Rendered PDF inspection failed")
	match = re.search(r"^Pages:\s+([0-9]+)\s*$", result.stdout, re.MULTILINE)
	require(match is not None, "Rendered PDF metadata omitted the page count")
	page_count = int(match.group(1))
	return page_count


#============================================
def replace_page_renders(
	temporary_pages: pathlib.Path,
	page_directory: pathlib.Path,
	page_count: int,
) -> tuple[pathlib.Path, ...]:
	"""Replace only this product's numbered render evidence with accepted pages."""
	page_directory.mkdir(parents=True, exist_ok=True)
	page_paths = []
	for page_number in range(1, page_count + 1):
		filename = f"slide_{page_number:02d}.png"
		temporary_path = temporary_pages / filename
		require(temporary_path.is_file(), f"Rendered page is absent: {temporary_path}")
		require(temporary_path.stat().st_size > 0, f"Rendered page is empty: {temporary_path}")
		page_path = page_directory / filename
		temporary_path.replace(page_path)
		page_paths.append(page_path)
	return tuple(page_paths)


#============================================
def invalidate_published_artifacts(
	product_path: pathlib.Path,
	page_directory: pathlib.Path,
) -> None:
	"""Remove the explicit prior artifact set before starting a new batch."""
	if product_path.is_file():
		product_path.unlink()
	if not page_directory.is_dir():
		return
	for existing_path in page_directory.iterdir():
		if existing_path.is_file() and PAGE_FILENAME_PATTERN.fullmatch(existing_path.name):
			existing_path.unlink()


#============================================
def publish_artifacts(
	staged_product_path: pathlib.Path,
	staged_page_paths: tuple[pathlib.Path, ...],
	product_path: pathlib.Path,
	page_directory: pathlib.Path,
) -> tuple[pathlib.Path, ...]:
	"""Publish a complete staged page set, then expose the validated ODP marker."""
	product_path.parent.mkdir(parents=True, exist_ok=True)
	page_directory.mkdir(parents=True, exist_ok=True)
	page_paths = []
	for staged_page_path in staged_page_paths:
		page_path = page_directory / staged_page_path.name
		os.replace(staged_page_path, page_path)
		page_paths.append(page_path)
	os.replace(staged_product_path, product_path)
	return tuple(page_paths)


#============================================
def render_deck_pages(
	output_path: pathlib.Path,
	page_directory: pathlib.Path,
	expected_page_count: int,
) -> tuple[pathlib.Path, ...]:
	"""Render and retain exactly one nonempty PNG for each accepted movie page."""
	with tempfile.TemporaryDirectory() as temporary_directory:
		render_directory = pathlib.Path(temporary_directory)
		profile_uri = render_directory.joinpath("libreoffice_profile").resolve().as_uri()
		run_command(
			[
				"soffice",
				f"-env:UserInstallation={profile_uri}",
				"--headless",
				"--convert-to",
				"pdf",
				"--outdir",
				str(render_directory),
				str(output_path.resolve()),
			],
			"LibreOffice review-deck PDF render failed",
		)
		pdf_path = render_directory / f"{output_path.stem}.pdf"
		require(pdf_path.is_file(), f"LibreOffice did not render review deck: {pdf_path}")
		require(pdf_path.stat().st_size > 0, f"LibreOffice rendered an empty PDF: {pdf_path}")
		page_count = pdf_page_count(pdf_path)
		require(
			page_count == expected_page_count,
			f"Rendered review deck has {page_count} pages; expected {expected_page_count}",
		)
		temporary_pages = render_directory / "pages"
		temporary_pages.mkdir()
		for page_number in range(1, page_count + 1):
			page_path = temporary_pages / f"slide_{page_number:02d}.png"
			run_command(
				[
					"pdftoppm",
					"-png",
					"-singlefile",
					"-f",
					str(page_number),
					"-l",
					str(page_number),
					"-r",
					"150",
					str(pdf_path),
					str(page_path.with_suffix("")),
				],
				f"Review-deck page {page_number} pixel render failed",
			)
		page_paths = replace_page_renders(temporary_pages, page_directory, page_count)
	return page_paths


#============================================
def build_review_deck(
	requests: tuple[ReviewMovieRequest, ...] = DEFAULT_REQUESTS,
	output_path: str | pathlib.Path = DEFAULT_OUTPUT_PATH,
	providers: slide_maker.movie_pipeline.ProviderBundle = slide_maker.movie_pipeline.LIVE_PROVIDERS,
	write_line: collections.abc.Callable[[str], None] = print,
) -> ReviewDeckResult:
	"""Resolve, build, convert, render, and account for one deterministic batch.

	Args:
		requests: Exact title-and-year requests to process in order.
		output_path: Final ODP product path; its sibling render directory is derived.
		providers: Injectable resolver and provider functions used for every request.
		write_line: Callback that receives progress and source-failure diagnostics.

	Returns:
		The published product path, accepted-page accounting, failures, and PNG paths.

	Raises:
		ReviewDeckError: No request succeeds or build, render, or accounting fails.
		slide_maker.slide_convert.SlideConversionError: Conversion or ODP validation fails.

	Note:
		The function never reads terminal input. It invalidates prior published
		artifacts, performs provider requests through ``providers``, and publishes
		the ODP and page renders only after the staged product passes validation.
	"""
	product_path = pathlib.Path(output_path)
	repo_root = slide_maker.config.get_repo_root()
	template_path = repo_root / "template" / "movie_slide_template.pptx"
	page_directory = product_path.parent / "review_deck_pages"
	product_path.parent.mkdir(parents=True, exist_ok=True)
	invalidate_published_artifacts(product_path, page_directory)
	require(bool(requests), "Review deck requires at least one movie request")
	with tempfile.TemporaryDirectory() as temporary_directory:
		work_directory = pathlib.Path(temporary_directory)
		poster_directory = work_directory / "posters"
		poster_directory.mkdir()
		accepted_movies, failures = resolve_requests(
			requests,
			poster_directory,
			providers,
			write_line,
		)
		require(bool(accepted_movies), "Review deck has no fully validated movies")
		scratch_path = work_directory / "review_deck.pptx"
		build_scratch_deck(accepted_movies, template_path, scratch_path)
		staged_product_path = work_directory / "review_deck.odp"
		slide_maker.slide_convert.convert_presentation(
			scratch_path,
			staged_product_path,
			expected_movie_slides=len(accepted_movies),
		)
		validate_deck_identities(staged_product_path, accepted_movies)
		staged_page_directory = work_directory / "review_deck_pages"
		staged_page_paths = render_deck_pages(
			staged_product_path,
			staged_page_directory,
			len(accepted_movies),
		)
		page_paths = publish_artifacts(
			staged_product_path,
			staged_page_paths,
			product_path,
			page_directory,
		)
	accepted = tuple(
		ReviewDeckAccepted(request.identity, movie_data.title, movie_data.year, page_number)
		for page_number, (request, movie_data) in enumerate(accepted_movies, start=1)
	)
	result = ReviewDeckResult(product_path, accepted, tuple(failures), page_paths)
	return result


#============================================
def main() -> None:
	"""Build the no-input default review deck and print structured accounting."""
	result = build_review_deck()
	for accepted in result.accepted:
		print(
			f"Accepted page {accepted.page_number}: {accepted.requested_identity} "
			f"as {accepted.title} ({accepted.year})"
		)
	for failure in result.failures:
		print(f"Rejected: {failure.diagnostic}")
	print(f"Created validated review deck: {result.output_path}")
	print(f"Retained {len(result.page_paths)} page renders")


if __name__ == "__main__":
	main()

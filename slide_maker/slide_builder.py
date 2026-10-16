"""Build movie slides from the extracted presentation template."""

# Standard Library
import copy
import pathlib

# PIP3 modules
import pptx
import PIL.Image #pillow
import pptx.util
import pptx.oxml
import pptx.oxml.ns
import pptx.enum.text

# local repo modules
import slide_maker.moviedata
import slide_maker.emoji_marks
import slide_maker.rating_layout


TEMPLATE_TITLE_NAME = "movie_title"
TEMPLATE_OUTLINE_NAME = "movie_outline"
TEMPLATE_POSTER_NAME = "movie_poster"
FONT_NAME = "Atkinson Hyperlegible Next"
TITLE_FONT_SIZE = pptx.util.Pt(40.4)
PRIMARY_FONT_SIZE = pptx.util.Pt(22.0)
SECONDARY_FONT_SIZE = pptx.util.Pt(19.2)
PAGE_WIDTH = pptx.util.Cm(28.0)
PAGE_HEIGHT = pptx.util.Cm(17.5)
IMDB_SCORE_HIGHLIGHT = "F5C518"
RATING_SEPARATOR = " | "


class SlideBuildError(RuntimeError):
	"""Report a missing or ambiguous template role required for a movie slide."""


#============================================
def require(condition: bool, message: str) -> None:
	"""Raise a builder error when a required template condition is false."""
	if condition:
		return
	raise SlideBuildError(message)


#============================================
def shape_by_name(slide: object, name: str) -> object:
	"""Return the one shape carrying a required semantic role name."""
	candidates = [shape for shape in slide.shapes if shape.name == name]
	require(candidates, f"Required template role is absent: {name}")
	require(len(candidates) == 1, f"Required template role is ambiguous: {name}")
	shape = candidates[0]
	return shape


#============================================
def clone_template_shapes(source_slide: object, target_slide: object) -> None:
	"""Copy template shapes to a new slide while retaining their formatting."""
	for shape in list(target_slide.shapes):
		target_slide.shapes._spTree.remove(shape._element)
	for shape in source_slide.shapes:
		cloned_element = copy.deepcopy(shape._element)
		target_slide.shapes._spTree.insert_element_before(cloned_element, "p:extLst")


#============================================
def format_compact_count(count: int) -> str:
	"""Format a nonnegative count with a compact suffix and at least two significant digits."""
	if type(count) is not int or count < 0:
		raise ValueError("Compact count must be a nonnegative integer")
	units = (
		(999_500_000, 1_000_000_000, "B"),
		(999_500, 1_000_000, "M"),
		(1_000, 1_000, "k"),
	)
	for threshold, divisor, suffix in units:
		if count < threshold:
			continue
		scaled = count / divisor
		if scaled < 10:
			number = f"{scaled:.1f}"
		else:
			number = f"{scaled:.0f}"
		return f"{number}{suffix}"
	return str(count)


#============================================
def add_styled_run(
	paragraph: object,
	text: str,
	font_size: pptx.util.Length,
	bold: bool = False,
) -> object:
	"""Add one consistently styled accessible text run."""
	run = paragraph.add_run()
	run.text = text
	run.font.name = FONT_NAME
	run.font.size = font_size
	run.font.bold = bold
	return run


#============================================
def set_run_highlight(run: object, color: str) -> None:
	"""Apply one DrawingML text highlight not exposed by python-pptx."""
	run_properties = run._r.get_or_add_rPr()
	highlight_tag = pptx.oxml.ns.qn("a:highlight")
	for child in list(run_properties):
		if child.tag == highlight_tag:
			run_properties.remove(child)
	highlight_xml = (
		f'<a:highlight {pptx.oxml.ns.nsdecls("a")}>'
		f'<a:srgbClr val="{color}"/>'
		"</a:highlight>"
	)
	highlight = pptx.oxml.parse_xml(highlight_xml)
	run_properties.append(highlight)


#============================================
def add_text_paragraph(
	text_frame: object,
	text: str,
	level: int,
	font_size: pptx.util.Length,
	first: bool,
) -> None:
	"""Add one paragraph at the requested outline level."""
	if first:
		paragraph = text_frame.paragraphs[0]
	else:
		paragraph = text_frame.add_paragraph()
	paragraph.level = level
	add_styled_run(paragraph, text, font_size)


#============================================
def rating_items(
	movie_data: slide_maker.moviedata.MovieData,
) -> list[tuple[str, str]]:
	"""Assemble independent labeled facts with an optional highlighted score."""
	items = []
	if movie_data.imdb_rating is not None:
		score = f"{movie_data.imdb_rating:.1f}"
		text = f"IMDb {score}"
		if movie_data.imdb_votes is not None:
			text += f", {format_compact_count(movie_data.imdb_votes)} votes"
		items.append((text, score))
	elif movie_data.imdb_votes is not None:
		items.append((f"IMDb: {format_compact_count(movie_data.imdb_votes)} votes", ""))
	rt_mark, audience_mark, metascore_mark = format_rating_marks(movie_data)
	if movie_data.rt_tomatometer is not None:
		items.append((f"RT critics: {rt_mark} {movie_data.rt_tomatometer}%", ""))
	if movie_data.rt_audience_score is not None:
		items.append((f"RT audience: {audience_mark} {movie_data.rt_audience_score}%", ""))
	if movie_data.metascore is not None:
		items.append((f"Metacritic: {metascore_mark} {movie_data.metascore}", ""))
	return items


#============================================
def add_rating_rows(
	text_frame: object,
	items: list[tuple[str, str]],
	rows: list[list[int]],
	level: int,
	paragraph_properties: object,
) -> None:
	"""Render chosen rows with atomic items and the IMDb highlight intact."""
	for row in rows:
		paragraph = text_frame.add_paragraph() if text_frame.text else text_frame.paragraphs[0]
		paragraph._p.remove(paragraph._p.get_or_add_pPr())
		paragraph._p.insert(0, copy.deepcopy(paragraph_properties))
		paragraph.level = level
		for position, index in enumerate(row):
			if position:
				add_styled_run(paragraph, RATING_SEPARATOR, SECONDARY_FONT_SIZE)
			text, score = items[index]
			# Nonbreaking spaces keep each label, mark, score and vote count together.
			text = text.replace(" ", "\u00a0")
			if not score:
				add_styled_run(paragraph, text, SECONDARY_FONT_SIZE)
				continue
			before, score_text, after = text.partition(score)
			add_styled_run(paragraph, before, SECONDARY_FONT_SIZE)
			run = add_styled_run(paragraph, score_text, SECONDARY_FONT_SIZE, bold=True)
			set_run_highlight(run, IMDB_SCORE_HIGHLIGHT)
			add_styled_run(paragraph, after, SECONDARY_FONT_SIZE)


#============================================
def format_rating_marks(
	movie_data: slide_maker.moviedata.MovieData,
) -> tuple[str | None, str | None, str | None]:
	"""Return the requested critic, audience, and Metascore display marks."""
	rt_mark = None
	if movie_data.rt_tomatometer is not None:
		rt_mark = slide_maker.emoji_marks.rt_critic_mark_for_score(movie_data.rt_tomatometer)
	if movie_data.rt_audience_score is None:
		audience_mark = None
	else:
		audience_mark = slide_maker.emoji_marks.rt_audience_mark_for_score(
			movie_data.rt_audience_score
		)
	metascore_marks = {
		"high": slide_maker.emoji_marks.GREEN_SQUARE_MARK,
		"middle": slide_maker.emoji_marks.YELLOW_SQUARE_MARK,
		"low": slide_maker.emoji_marks.RED_SQUARE_MARK,
	}
	metascore_mark = None
	if movie_data.metascore is not None:
		band = slide_maker.emoji_marks.metascore_band_for_score(movie_data.metascore)
		metascore_mark = metascore_marks[band]
	return rt_mark, audience_mark, metascore_mark


#============================================
def movie_title(movie_data: slide_maker.moviedata.MovieData) -> str:
	"""Format the title with a release year only when known."""
	title = movie_data.title
	if movie_data.year is not None:
		title += f" ({movie_data.year})"
	return title


#============================================
def normalize_template_fonts(presentation: object) -> None:
	"""Replace legacy inherited fonts in slides, layouts, and masters."""
	for part in presentation.part.package.iter_parts():
		if not hasattr(part, "_element"):
			continue
		for element in part._element.iter():
			font = element.get("typeface")
			if font is not None and "OpenDyslexic" in font:
				element.set("typeface", FONT_NAME)


#============================================
def fill_title(slide: object, movie_data: slide_maker.moviedata.MovieData) -> None:
	"""Fill the named movie-title anchor with the product title line."""
	title_shape = shape_by_name(slide, TEMPLATE_TITLE_NAME)
	require(title_shape.has_text_frame, "Movie title role has no text frame")
	text_frame = title_shape.text_frame
	text_frame.clear()
	text_frame.word_wrap = True
	text_frame.vertical_anchor = pptx.enum.text.MSO_VERTICAL_ANCHOR.MIDDLE
	text_frame.auto_size = pptx.enum.text.MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
	title_text = movie_title(movie_data)
	paragraph = text_frame.paragraphs[0]
	paragraph.level = 0
	add_styled_run(paragraph, title_text, TITLE_FONT_SIZE, bold=True)


#============================================
def fill_outline(slide: object, movie_data: slide_maker.moviedata.MovieData) -> None:
	"""Fill the named outline anchor with product labels and bullet hierarchy."""
	outline_shape = shape_by_name(slide, TEMPLATE_OUTLINE_NAME)
	require(outline_shape.has_text_frame, "Movie outline role has no text frame")
	text_frame = outline_shape.text_frame
	rating_level = 1 if movie_data.plot else 0
	body_properties = text_frame.paragraphs[0]._p.get_or_add_pPr()
	rating_properties = text_frame.paragraphs[rating_level]._p.get_or_add_pPr()
	details = []
	if movie_data.genres:
		details.append(f"Genre: {', '.join(movie_data.genres)}")
	if movie_data.directors:
		details.append(f"Director: {', '.join(movie_data.directors)}")
	if movie_data.runtime_minutes is not None:
		details.append(f"Run time: {movie_data.runtime_minutes} min")
	if movie_data.original_language and movie_data.original_language != "English":
		details.append(f"Original language: {movie_data.original_language}")
	if movie_data.rt_consensus.strip():
		details.append(f"Review Summary: {movie_data.rt_consensus}")
	items = rating_items(movie_data)
	scale = 1.0
	rows = []
	if items:
		metrics = slide_maker.rating_layout.TextMetrics(FONT_NAME)
		body_texts = ([movie_data.plot] if movie_data.plot else []) + details
		width = outline_shape.width - text_frame.margin_left - text_frame.margin_right
		height = outline_shape.height - text_frame.margin_top - text_frame.margin_bottom
		rows, scale = slide_maker.rating_layout.choose_rows(
			[metrics.width(text, SECONDARY_FONT_SIZE.pt) for text, unused_score in items],
			metrics.width(RATING_SEPARATOR, SECONDARY_FONT_SIZE.pt),
			metrics.paragraphs(body_texts, PRIMARY_FONT_SIZE.pt),
			metrics.width(" ", PRIMARY_FONT_SIZE.pt),
			(width - int(body_properties.get("marL", "0"))) / 12700,
			(width - int(rating_properties.get("marL", "0"))) / 12700,
			height / 12700, PRIMARY_FONT_SIZE.pt, SECONDARY_FONT_SIZE.pt,
		)
	text_frame.clear()
	text_frame.word_wrap = True
	text_frame.auto_size = pptx.enum.text.MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
	if movie_data.plot:
		add_text_paragraph(text_frame, movie_data.plot, 0, PRIMARY_FONT_SIZE, True)
	add_rating_rows(text_frame, items, rows, rating_level, rating_properties)
	for detail in details:
		add_text_paragraph(
			text_frame, detail, 0, PRIMARY_FONT_SIZE, not text_frame.text,
		)
	for paragraph in text_frame.paragraphs:
		for run in paragraph.runs:
			run.font.size = pptx.util.Pt(run.font.size.pt * scale)
	if not text_frame.text:
		slide.shapes._spTree.remove(outline_shape._element)


#============================================
def place_poster(slide: object, movie_data: slide_maker.moviedata.MovieData) -> object | None:
	"""Replace the poster anchor with an aspect-preserving centered picture."""
	poster_anchor = shape_by_name(slide, TEMPLATE_POSTER_NAME)
	anchor_left = poster_anchor.left
	anchor_top = poster_anchor.top
	anchor_width = poster_anchor.width
	anchor_height = poster_anchor.height
	slide.shapes._spTree.remove(poster_anchor._element)
	if movie_data.poster_path is None:
		for shape in slide.shapes:
			if shape.name == TEMPLATE_OUTLINE_NAME:
				shape.width = anchor_left + anchor_width - shape.left
		return None

	with PIL.Image.open(movie_data.poster_path) as poster_image:
		poster_width, poster_height = poster_image.size
	require(poster_width > 0 and poster_height > 0, "Poster image has invalid dimensions")
	poster_ratio = poster_width / poster_height
	anchor_ratio = anchor_width / anchor_height
	if poster_ratio >= anchor_ratio:
		picture = slide.shapes.add_picture(
			movie_data.poster_path,
			anchor_left,
			anchor_top,
			width=anchor_width,
		)
		picture.top = anchor_top + (anchor_height - picture.height) // 2
	else:
		picture = slide.shapes.add_picture(
			movie_data.poster_path,
			anchor_left,
			anchor_top,
			height=anchor_height,
		)
		picture.left = anchor_left + (anchor_width - picture.width) // 2
	picture.name = TEMPLATE_POSTER_NAME
	picture._element.nvPicPr.cNvPr.set("descr", f"Poster for {movie_data.title}")
	return picture


#============================================
def append_movie_slide(presentation: object, movie_data: slide_maker.moviedata.MovieData) -> object:
	"""Append one visible movie slide using the presentation's template slide."""
	slide_maker.moviedata.validate_movie_data(movie_data)
	normalize_template_fonts(presentation)
	presentation.slide_width = PAGE_WIDTH
	presentation.slide_height = PAGE_HEIGHT
	require(len(presentation.slides) >= 1, "Presentation has no movie template slide")
	template_slide = presentation.slides[0]
	shape_by_name(template_slide, TEMPLATE_TITLE_NAME)
	shape_by_name(template_slide, TEMPLATE_OUTLINE_NAME)
	shape_by_name(template_slide, TEMPLATE_POSTER_NAME)

	new_slide = presentation.slides.add_slide(template_slide.slide_layout)
	clone_template_shapes(template_slide, new_slide)
	new_slide._element.attrib.pop("show", None)
	fill_title(new_slide, movie_data)
	place_poster(new_slide, movie_data)
	fill_outline(new_slide, movie_data)
	return new_slide


#============================================
def build_movie_presentation(
	movie_data: slide_maker.moviedata.MovieData,
	template_path: pathlib.Path,
	output_path: pathlib.Path,
) -> pathlib.Path:
	"""Load the extracted template, append one movie slide, and save the PPTX."""
	require(template_path.is_file(), f"Movie slide template is absent: {template_path}")
	presentation = pptx.Presentation(template_path)
	append_movie_slide(presentation, movie_data)
	output_path.parent.mkdir(parents=True, exist_ok=True)
	presentation.save(output_path)
	return output_path

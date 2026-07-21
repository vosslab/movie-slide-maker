"""Build movie slides from the extracted presentation template."""

# Standard Library
import copy
import pathlib

# PIP3 modules
import pptx
import PIL.Image #pillow
import pptx.util
import pptx.enum.text

# local repo modules
import slide_maker.moviedata
import slide_maker.emoji_marks


TEMPLATE_TITLE_NAME = "movie_title"
TEMPLATE_OUTLINE_NAME = "movie_outline"
TEMPLATE_POSTER_NAME = "movie_poster"
FONT_NAME = "OpenDyslexic"
TITLE_FONT_SIZE = pptx.util.Pt(40.4)
PRIMARY_FONT_SIZE = pptx.util.Pt(22.0)
SECONDARY_FONT_SIZE = pptx.util.Pt(19.2)


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
def add_text_paragraph(
	text_frame: object,
	text: str,
	level: int,
	font_size: pptx.util.Length,
	first: bool,
) -> None:
	"""Add one OpenDyslexic paragraph at the requested outline level."""
	if first:
		paragraph = text_frame.paragraphs[0]
	else:
		paragraph = text_frame.add_paragraph()
	paragraph.level = level
	run = paragraph.add_run()
	run.text = text
	run.font.name = FONT_NAME
	run.font.size = font_size


#============================================
def format_rating_marks(movie_data: slide_maker.moviedata.MovieData) -> tuple[str, str]:
	"""Return the display marks for the validated RT and Metascore bands."""
	if movie_data.rt_state == "fresh":
		rt_mark = slide_maker.emoji_marks.GREEN_SQUARE_MARK
	else:
		rt_mark = slide_maker.emoji_marks.RED_SQUARE_MARK
	metascore_marks = {
		"high": slide_maker.emoji_marks.GREEN_SQUARE_MARK,
		"middle": slide_maker.emoji_marks.YELLOW_SQUARE_MARK,
		"low": slide_maker.emoji_marks.RED_SQUARE_MARK,
	}
	metascore_mark = metascore_marks[movie_data.metascore_band]
	return rt_mark, metascore_mark


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
	title_text = f"{movie_data.title} ({movie_data.year})"
	add_text_paragraph(text_frame, title_text, 0, TITLE_FONT_SIZE, True)


#============================================
def fill_outline(slide: object, movie_data: slide_maker.moviedata.MovieData) -> None:
	"""Fill the named outline anchor with product labels and bullet hierarchy."""
	outline_shape = shape_by_name(slide, TEMPLATE_OUTLINE_NAME)
	require(outline_shape.has_text_frame, "Movie outline role has no text frame")
	rt_mark, metascore_mark = format_rating_marks(movie_data)
	paragraphs = (
		(movie_data.plot, 0, PRIMARY_FONT_SIZE),
		(
			f"IMDB rating {movie_data.imdb_rating:.1f}, "
			f"{movie_data.imdb_votes:,} votes",
			1,
			SECONDARY_FONT_SIZE,
		),
		(
			f"Critics: RT {rt_mark} {movie_data.rt_tomatometer}% / "
			f"MS {metascore_mark} {movie_data.metascore}",
			1,
			SECONDARY_FONT_SIZE,
		),
		(f"Genre: {', '.join(movie_data.genres)}", 0, PRIMARY_FONT_SIZE),
		(f"Director: {', '.join(movie_data.directors)}", 0, PRIMARY_FONT_SIZE),
		(f"Run time: {movie_data.runtime_minutes} min", 0, PRIMARY_FONT_SIZE),
		(f"Review Summary: {movie_data.rt_consensus}", 0, PRIMARY_FONT_SIZE),
	)
	text_frame = outline_shape.text_frame
	text_frame.clear()
	text_frame.word_wrap = True
	text_frame.auto_size = pptx.enum.text.MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
	for index, (text, level, font_size) in enumerate(paragraphs):
		add_text_paragraph(text_frame, text, level, font_size, index == 0)


#============================================
def place_poster(slide: object, movie_data: slide_maker.moviedata.MovieData) -> object:
	"""Replace the poster anchor with an aspect-preserving centered picture."""
	poster_anchor = shape_by_name(slide, TEMPLATE_POSTER_NAME)
	anchor_left = poster_anchor.left
	anchor_top = poster_anchor.top
	anchor_width = poster_anchor.width
	anchor_height = poster_anchor.height
	slide.shapes._spTree.remove(poster_anchor._element)

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
	require(len(presentation.slides) >= 1, "Presentation has no movie template slide")
	template_slide = presentation.slides[0]
	shape_by_name(template_slide, TEMPLATE_TITLE_NAME)
	shape_by_name(template_slide, TEMPLATE_OUTLINE_NAME)
	shape_by_name(template_slide, TEMPLATE_POSTER_NAME)

	new_slide = presentation.slides.add_slide(template_slide.slide_layout)
	clone_template_shapes(template_slide, new_slide)
	new_slide._element.attrib.pop("show", None)
	fill_title(new_slide, movie_data)
	fill_outline(new_slide, movie_data)
	place_poster(new_slide, movie_data)
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

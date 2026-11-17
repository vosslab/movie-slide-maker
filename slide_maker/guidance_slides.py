"""Build editable parental-guidance slides from structured provider data."""

# Standard Library
import copy

# PIP3 modules
import pptx
import pptx.util
import pptx.enum.text
import pptx.enum.shapes
import pptx.dml.color

# local repo modules
import slide_maker.moviedata
import slide_maker.parental_guidance


FONT_NAME = "Atkinson Hyperlegible Next"
PAGE_WIDTH = pptx.util.Cm(28.0)
PAGE_HEIGHT = pptx.util.Cm(17.5)
TITLE_SIZE = pptx.util.Pt(26)
BODY_SIZE = pptx.util.Pt(20)
TABLE_SIZE = pptx.util.Pt(20)
SOURCE_SIZE = pptx.util.Pt(13)
BLACK = "222222"
GRAY = "F1F1F1"
GREEN = "B9D9A8"
YELLOW = "F5C518"
RED = "F7B2B2"


#============================================
def add_textbox(
	slide: object,
	name: str,
	text: str,
	left: int,
	top: int,
	width: int,
	height: int,
	font_size: pptx.util.Length,
	bold: bool = False,
	url: str = "",
) -> object:
	"""Add one editable, named text box with consistent typography."""
	shape = slide.shapes.add_textbox(left, top, width, height)
	shape.name = name
	frame = shape.text_frame
	frame.clear()
	frame.word_wrap = True
	frame.margin_left = pptx.util.Cm(0.15)
	frame.margin_right = pptx.util.Cm(0.15)
	frame.margin_top = pptx.util.Cm(0.05)
	frame.margin_bottom = pptx.util.Cm(0.05)
	paragraph = frame.paragraphs[0]
	paragraph.space_after = pptx.util.Pt(0)
	run = paragraph.add_run()
	run.text = text
	run.font.name = FONT_NAME
	run.font.size = font_size
	run.font.bold = bold
	run.font.color.rgb = pptx.dml.color.RGBColor.from_string(BLACK)
	if url:
		run.hyperlink.address = url
	return shape


#============================================
def remove_template_roles(slide: object) -> None:
	"""Remove movie-template content while retaining its master-page background."""
	for shape in list(slide.shapes):
		slide.shapes._spTree.remove(shape._element)


#============================================
def new_guidance_slide(presentation: object, template_slide: object) -> object:
	"""Append a blank editable slide using the movie template's layout and background."""
	slide = presentation.slides.add_slide(template_slide.slide_layout)
	for shape in template_slide.shapes:
		element = copy.deepcopy(shape._element)
		slide.shapes._spTree.insert_element_before(element, "p:extLst")
	remove_template_roles(slide)
	slide._element.attrib.pop("show", None)
	return slide


#============================================
def shorten(text: str, limit: int) -> str:
	"""Keep a whole-word excerpt within the requested word limit."""
	words = text.split()
	if len(words) <= limit:
		return text
	result = " ".join(words[:limit]) + " ..."
	return result


#============================================
def rating_text(category: slide_maker.parental_guidance.GuidanceCategory) -> str:
	"""Return one visible Common Sense score with accessible numeric meaning."""
	if category.score is None:
		text = "Not available"
	else:
		# Numeric text stays readable in a narrow editable table cell after conversion.
		text = f"{category.score} of 5"
	return text


#============================================
def add_csm_table(
	slide: object,
	name: str,
	categories: tuple[slide_maker.parental_guidance.GuidanceCategory, ...],
	left: int,
	top: int,
	width: int,
	height: int,
) -> object:
	"""Add a compact native table for one Common Sense category group."""
	rows = max(2, len(categories) + 1)
	table_shape = slide.shapes.add_table(rows, 2, left, top, width, height)
	table_shape.name = name
	table = table_shape.table
	table.columns[0].width = int(width * 0.66)
	table.columns[1].width = width - table.columns[0].width
	for row in table.rows:
		row.height = height // rows
	headers = ("Category", "Rating")
	for column, text in enumerate(headers):
		write_cell(table.cell(0, column), text, TABLE_SIZE, True, GRAY)
	for row, category in enumerate(categories, 1):
		write_cell(table.cell(row, 0), category.name, TABLE_SIZE, True)
		write_cell(table.cell(row, 1), rating_text(category), TABLE_SIZE)
	return table_shape


#============================================
def write_cell(
	cell: object,
	text: str,
	font_size: pptx.util.Length,
	bold: bool = False,
	fill: str = "",
) -> None:
	"""Set one editable table cell with readable wrapping and optional fill."""
	cell.margin_left = pptx.util.Cm(0.12)
	cell.margin_right = pptx.util.Cm(0.12)
	cell.margin_top = pptx.util.Cm(0.08)
	cell.margin_bottom = pptx.util.Cm(0.08)
	if fill:
		cell.fill.solid()
		cell.fill.fore_color.rgb = pptx.dml.color.RGBColor.from_string(fill)
	frame = cell.text_frame
	frame.clear()
	frame.word_wrap = True
	paragraph = frame.paragraphs[0]
	paragraph.space_after = pptx.util.Pt(0)
	run = paragraph.add_run()
	run.text = text
	run.font.name = FONT_NAME
	run.font.size = font_size
	run.font.bold = bold
	run.font.color.rgb = pptx.dml.color.RGBColor.from_string(BLACK)


#============================================
def csm_categories(
	guidance: slide_maker.parental_guidance.SourceGuidance,
) -> tuple[list[slide_maker.parental_guidance.GuidanceCategory], list[slide_maker.parental_guidance.GuidanceCategory]]:
	"""Separate warning and positive Common Sense categories for side-by-side tables."""
	positive_names = {"Positive Messages", "Positive Role Models", "Diverse Representations"}
	warnings = []
	positive = []
	for category in guidance.categories:
		if category.name in positive_names:
			positive.append(category)
		else:
			warnings.append(category)
	return warnings, positive


#============================================
def diagnostic_note(diagnostics: tuple[str, ...], missing_provider: str) -> str:
	"""Return a compact visible note for one unavailable complementary source."""
	if not diagnostics:
		return f"{missing_provider} guidance unavailable."
	note = shorten(diagnostics[0], 14)
	return f"{missing_provider} guidance unavailable: {note}"


#============================================
def guidance_title(provider: str, movie_data: slide_maker.moviedata.MovieData) -> str:
	"""Return a provider title that carries the resolved movie identity."""
	title = f"{provider}: {movie_data.title}"
	if movie_data.year is not None:
		title += f" ({movie_data.year})"
	return title


#============================================
def append_csm_slides(
	presentation: object,
	template_slide: object,
	movie_data: slide_maker.moviedata.MovieData,
	guidance: slide_maker.parental_guidance.SourceGuidance,
	diagnostics: tuple[str, ...] = (),
) -> list[object]:
	"""Append the Common Sense overview and category-table pages."""
	title = guidance_title("Common Sense Media", movie_data)
	overview_slide = new_guidance_slide(presentation, template_slide)
	add_textbox(overview_slide, "guidance_title", title, pptx.util.Cm(1.0), pptx.util.Cm(0.8),
		pptx.util.Cm(26.0), pptx.util.Cm(1.2), TITLE_SIZE, True)
	meta = " | ".join(value for value in (guidance.age, guidance.certificate, guidance.rating_reason) if value)
	if meta:
		add_textbox(overview_slide, "guidance_body", meta, pptx.util.Cm(1.2), pptx.util.Cm(2.1),
			pptx.util.Cm(25.4), pptx.util.Cm(0.8), BODY_SIZE, True)
	overview = shorten(guidance.overview, 140) if guidance.overview else "Overview not available."
	add_textbox(overview_slide, "guidance_overview", overview, pptx.util.Cm(1.2), pptx.util.Cm(3.1),
		pptx.util.Cm(25.4), pptx.util.Cm(11.9), BODY_SIZE)
	source_text = "Source: Common Sense Media"
	if diagnostics:
		source_text += " | " + diagnostic_note(diagnostics, "IMDb")
	add_textbox(overview_slide, "guidance_source", source_text, pptx.util.Cm(1.2),
		pptx.util.Cm(16.0), pptx.util.Cm(25.4), pptx.util.Cm(0.6), SOURCE_SIZE, url=guidance.url)

	categories_slide = new_guidance_slide(presentation, template_slide)
	add_textbox(categories_slide, "guidance_title", title + " ratings", pptx.util.Cm(1.0), pptx.util.Cm(0.8),
		pptx.util.Cm(26.0), pptx.util.Cm(1.2), TITLE_SIZE, True)
	warnings, positive = csm_categories(guidance)
	add_textbox(categories_slide, "guidance_warning_heading", "Content guidance", pptx.util.Cm(1.1),
		pptx.util.Cm(2.05), pptx.util.Cm(12.5), pptx.util.Cm(0.55), BODY_SIZE, True)
	add_textbox(categories_slide, "guidance_positive_heading", "Positive content", pptx.util.Cm(14.4),
		pptx.util.Cm(2.05), pptx.util.Cm(12.5), pptx.util.Cm(0.55), BODY_SIZE, True)
	add_csm_table(categories_slide, "guidance_warnings", warnings, pptx.util.Cm(1.1), pptx.util.Cm(3.0),
		pptx.util.Cm(12.5), pptx.util.Cm(12.3))
	add_csm_table(categories_slide, "guidance_positive", positive, pptx.util.Cm(14.4), pptx.util.Cm(3.0),
		pptx.util.Cm(12.5), pptx.util.Cm(12.3))
	add_textbox(categories_slide, "guidance_source", source_text, pptx.util.Cm(1.2),
		pptx.util.Cm(16.0), pptx.util.Cm(25.4), pptx.util.Cm(0.6), SOURCE_SIZE, url=guidance.url)
	return [overview_slide, categories_slide]


#============================================
def severity_fill(severity: str) -> str:
	"""Return the readable severity color used by the prior course slides."""
	colors = {"None": GRAY, "Mild": GREEN, "Moderate": YELLOW, "Severe": RED}
	color = colors.get(severity, GRAY)
	return color


#============================================
def append_imdb_slides(
	presentation: object,
	template_slide: object,
	movie_data: slide_maker.moviedata.MovieData,
	guidance: slide_maker.parental_guidance.SourceGuidance,
	diagnostics: tuple[str, ...] = (),
) -> list[object]:
	"""Append readable IMDb tables, continuing after two detailed rows."""
	slides = []
	category_groups = [guidance.categories[index:index + 2] for index in range(0, len(guidance.categories), 2)]
	if not category_groups:
		category_groups = [()]
	for index, categories in enumerate(category_groups, 1):
		slide = new_guidance_slide(presentation, template_slide)
		title = guidance_title("IMDb Parents' Guide", movie_data)
		if len(category_groups) > 1:
			title += f" ({index}/{len(category_groups)})"
		add_textbox(slide, "guidance_title", title, pptx.util.Cm(1.0), pptx.util.Cm(0.8),
			pptx.util.Cm(26.0), pptx.util.Cm(1.2), TITLE_SIZE, True)
		rows = max(2, len(categories) + 1)
		table_shape = slide.shapes.add_table(rows, 3, pptx.util.Cm(1.0), pptx.util.Cm(2.3),
			pptx.util.Cm(26.0), pptx.util.Cm(13.0))
		table_shape.name = "guidance_table"
		table = table_shape.table
		table.columns[0].width = pptx.util.Cm(7.2)
		table.columns[1].width = pptx.util.Cm(4.0)
		table.columns[2].width = pptx.util.Cm(14.8)
		for table_row in table.rows:
			table_row.height = pptx.util.Cm(13.0) // rows
		for column, text in enumerate(("Category", "Severity", "Selected non-spoiler example")):
			write_cell(table.cell(0, column), text, TABLE_SIZE, True, GRAY)
		for row, category in enumerate(categories, 1):
			write_cell(table.cell(row, 0), category.name, TABLE_SIZE, True)
			severity = category.severity or "Not available"
			write_cell(table.cell(row, 1), severity, TABLE_SIZE, True, severity_fill(category.severity))
			example = shorten(category.example, 35) if category.example else "No non-spoiler example available."
			write_cell(table.cell(row, 2), example, TABLE_SIZE)
		source_text = "Source: IMDb Parents' Guide; selected examples are not complete."
		if diagnostics:
			source_text += " " + diagnostic_note(diagnostics, "Common Sense Media")
		add_textbox(slide, "guidance_source", source_text, pptx.util.Cm(1.2), pptx.util.Cm(16.0),
			pptx.util.Cm(25.4), pptx.util.Cm(0.6), SOURCE_SIZE, url=guidance.url)
		slides.append(slide)
	return slides


#============================================
def append_unavailable_slide(
	presentation: object,
	template_slide: object,
	movie_data: slide_maker.moviedata.MovieData,
	diagnostics: tuple[str, ...],
) -> object:
	"""Make unavailable guidance explicit without implying an absence of content warnings."""
	slide = new_guidance_slide(presentation, template_slide)
	add_textbox(slide, "guidance_title", f"Parental guidance: {movie_data.title}", pptx.util.Cm(1.0),
		pptx.util.Cm(0.8), pptx.util.Cm(26.0), pptx.util.Cm(1.2), TITLE_SIZE, True)
	message = "Current parental-guidance sources were unavailable. Check the provider pages before viewing."
	if diagnostics:
		message += "\n\n" + "\n".join(diagnostics)
	add_textbox(slide, "guidance_body", message, pptx.util.Cm(1.2), pptx.util.Cm(3.2),
		pptx.util.Cm(25.4), pptx.util.Cm(9.0), BODY_SIZE)
	if movie_data.imdb_id:
		url = f"https://www.imdb.com/title/{movie_data.imdb_id}/parentalguide/"
		add_textbox(slide, "guidance_source", "IMDb Parents' Guide", pptx.util.Cm(1.2),
			pptx.util.Cm(16.0), pptx.util.Cm(12.0), pptx.util.Cm(0.6), SOURCE_SIZE, url=url)
	return slide


#============================================
def append_guidance_slides(
	presentation: object,
	template_slide: object,
	movie_data: slide_maker.moviedata.MovieData,
) -> list[object]:
	"""Append each available guidance source, or one explicit unavailable page."""
	guidance = movie_data.guidance
	if guidance is None:
		return []
	slides = []
	if guidance.csm is not None:
		diagnostics = guidance.diagnostics if guidance.imdb is None else ()
		if guidance.imdb is None and not diagnostics:
			diagnostics = ("No provider response details.",)
		slides.extend(append_csm_slides(presentation, template_slide, movie_data, guidance.csm, diagnostics))
	if guidance.imdb is not None:
		diagnostics = guidance.diagnostics if guidance.csm is None else ()
		if guidance.csm is None and not diagnostics:
			diagnostics = ("No provider response details.",)
		slides.extend(append_imdb_slides(presentation, template_slide, movie_data, guidance.imdb, diagnostics))
	if not slides:
		slides.append(append_unavailable_slide(presentation, template_slide, movie_data, guidance.diagnostics))
	return slides

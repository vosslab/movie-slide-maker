"""Measure slide content and pack complete ratings into the available space."""

# Standard Library
import re

# PIP3 modules
import PIL.ImageFont #pillow
import pptx.text.fonts


#============================================
class TextMetrics:
	"""Measure the installed movie font in points, reserving room for emoji."""

	def __init__(self, family: str) -> None:
		# ASVS 5.3.2: resolve the application font from installed fonts, never movie data.
		font_path = pptx.text.fonts.FontFiles.find(family, False, False)
		self.font = PIL.ImageFont.truetype(font_path, 1000)

	def width(self, text: str, size: float) -> float:
		"""Measure text with a conservative em allowance for color-font symbols."""
		parts = re.split(r"([\U0001f000-\U0001faff])", text)
		width = 0.0
		for part in parts:
			if part and ord(part[0]) >= 0x1F000:
				width += size * 1.15
			else:
				width += self.font.getlength(part) * size / 1000
		return width

	def paragraphs(self, texts: list[str], size: float) -> list[list[float]]:
		"""Premeasure words so candidate layouts need no repeated font loading."""
		paragraphs = []
		for text in texts:
			for line in text.splitlines():
				paragraphs.append([self.width(word, size) for word in line.split()])
		return paragraphs


#============================================
def pack_rows(widths: list[float], separator: float, width: float) -> list[list[int]]:
	"""Wrap only between complete items, preserving their reading order."""
	rows = []
	row = []
	used = 0.0
	for index, item_width in enumerate(widths):
		addition = item_width + (separator if row else 0.0)
		if row and used + addition > width:
			rows.append(row)
			row = []
			used = 0.0
		if row:
			used += separator
		row.append(index)
		used += item_width
	if row:
		rows.append(row)
	return rows


#============================================
def body_line_count(paragraphs: list[list[float]], space: float, width: float) -> int:
	"""Count wrapped body lines at one candidate effective width."""
	lines = 0
	for words in paragraphs:
		lines += 1
		used = 0.0
		for word in words:
			addition = word + (space if used else 0.0)
			if used and used + addition > width:
				lines += 1
				used = 0.0
			# Long unbroken words still consume their full measured width.
			while word > width:
				lines += 1
				word -= width
			used += word + (space if used else 0.0)
	return lines


#============================================
def choose_rows(
	widths: list[float],
	separator: float,
	paragraphs: list[list[float]],
	space: float,
	body_width: float,
	rating_width: float,
	height: float,
	body_size: float,
	rating_size: float,
) -> tuple[list[list[int]], float]:
	"""Choose compact rows at the largest estimated whole-outline text scale.

	All dimensions are points at the normal font sizes. Body text, including plot,
	review and metadata, competes with ratings for the same height. Width reserves
	a small margin for differences between Pillow and the presentation renderer.
	"""
	if min(body_width, rating_width, height) <= 0:
		raise ValueError("The slide outline must have positive available dimensions")
	lower = 0.0
	upper = 1.0
	best_rows = [[index] for index in range(len(widths))]
	# Test full size first, then bisect the fit boundary rather than choosing by movie name.
	for attempt in range(13):
		scale = 1.0 if attempt == 0 else (lower + upper) / 2
		available_width = rating_width * 0.95 / scale
		rows = pack_rows(widths, separator, available_width)
		lines = body_line_count(paragraphs, space, body_width * 0.95 / scale)
		body_height = lines * body_size * 1.1 + len(paragraphs) * 5.75
		rating_height = len(rows) * (rating_size * 1.1 + 2.89)
		fits = (body_height + rating_height) * scale <= height
		fits = fits and all(width <= available_width for width in widths)
		if fits:
			lower = scale
			best_rows = rows
			if scale == 1.0:
				break
		else:
			upper = scale
	return best_rows, lower

"""Presentation marks and shared movie-score classifications."""

GREEN_SQUARE_MARK = "\U0001f7e9"
YELLOW_SQUARE_MARK = "\U0001f7e8"
RED_SQUARE_MARK = "\U0001f7e5"


#============================================
def rt_state_for_score(tomatometer: int) -> str:
	"""Return the Rotten Tomatoes state for a Tomatometer score.

	Args:
		tomatometer: Rotten Tomatoes critics score.

	Returns:
		``"fresh"`` for scores of at least 60, otherwise ``"rotten"``.
	"""
	if tomatometer >= 60:
		state = "fresh"
	else:
		state = "rotten"
	return state


#============================================
def metascore_band_for_score(metascore: int) -> str:
	"""Return the display band for a Metacritic Metascore.

	Args:
		metascore: Metacritic score.

	Returns:
		``"low"`` below 40, ``"middle"`` from 40 through 60, or ``"high"``
		for scores of at least 61.
	"""
	if metascore < 40:
		band = "low"
	elif metascore <= 60:
		band = "middle"
	else:
		band = "high"
	return band

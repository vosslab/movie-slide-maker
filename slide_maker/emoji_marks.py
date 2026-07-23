"""Presentation marks and shared movie-score classifications."""

GREEN_SQUARE_MARK = "\U0001f7e9"
YELLOW_SQUARE_MARK = "\U0001f7e8"
RED_SQUARE_MARK = "\U0001f7e5"
ROTTEN_MARK = "\U0001f922"
TOMATO_MARK = "\U0001f345"
TROPHY_MARK = "\U0001f3c6"
POPCORN_MARK = "\U0001f37f"
THUMBS_DOWN_MARK = "\U0001f44e"


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
def rt_critic_mark_for_score(tomatometer: int) -> str:
	"""Return the requested Rotten Tomatoes critics display mark.

	Args:
		tomatometer: Rotten Tomatoes critics score.

	Returns:
		A rotten mark below 60, tomato from 60 through 80, or tomato and
		trophy above 80.
	"""
	if tomatometer < 60:
		mark = ROTTEN_MARK
	elif tomatometer <= 80:
		mark = TOMATO_MARK
	else:
		mark = f"{TOMATO_MARK}{TROPHY_MARK}"
	return mark


#============================================
def rt_audience_mark_for_score(audience_score: int) -> str:
	"""Return the requested Rotten Tomatoes audience display mark.

	Args:
		audience_score: Rotten Tomatoes Popcornmeter score.

	Returns:
		Popcorn at 60 or higher, or popcorn and thumbs-down below 60.
	"""
	if audience_score >= 60:
		mark = POPCORN_MARK
	else:
		mark = f"{POPCORN_MARK}{THUMBS_DOWN_MARK}"
	return mark


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

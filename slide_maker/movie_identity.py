"""Normalize and compare movie identities across provider boundaries."""

# Standard Library
import re
import unicodedata


#============================================
def normalize_identity_text(value: str) -> str:
	"""Return punctuation-insensitive ASCII text for identity comparisons.

	Args:
		value: Movie title or person name supplied by a provider.

	Returns:
		A case-folded alphanumeric identity with diacritics transliterated.
	"""
	normalized = unicodedata.normalize("NFKD", value)
	ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
	identity = re.sub(r"[^a-z0-9]+", "", ascii_text.casefold())
	return identity


#============================================
def count_identity_matches(
	actual_title: str,
	actual_year: int,
	actual_directors: list[str],
	expected_title: str,
	expected_year: int,
	expected_directors: list[str],
) -> int:
	"""Count independent title, release-year, and director agreements.

	Args:
		actual_title: Title returned by the provider being checked.
		actual_year: Release year returned by the provider being checked.
		actual_directors: Director names returned by the provider being checked.
		expected_title: Title supplied by the authoritative identity provider.
		expected_year: Release year supplied by the authoritative identity provider.
		expected_directors: Authoritative director names.

	Returns:
		The number of matching identity attributes, from zero through three.
	"""
	matches = 0
	if normalize_identity_text(actual_title) == normalize_identity_text(expected_title):
		matches += 1
	if actual_year == expected_year:
		matches += 1
	director_match = any(
		normalize_identity_text(actual) == normalize_identity_text(expected)
		for actual in actual_directors
		for expected in expected_directors
	)
	if director_match:
		matches += 1
	return matches

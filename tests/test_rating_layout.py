"""Protect whole-item wrapping and content-sensitive rating composition."""

# PIP3 modules
import pytest

# local repo modules
import slide_maker.moviedata
import slide_maker.rating_layout
import slide_maker.slide_builder


#============================================
def test_rating_wrap_preserves_each_item() -> None:
	"""Narrow rows wrap between facts without losing or rearranging them."""
	rows = slide_maker.rating_layout.pack_rows([40, 30, 60, 20], 5, 80)
	assert rows == [[0, 1], [2], [3]]
	assert slide_maker.rating_layout.pack_rows([40, 30, 60, 20], 5, 200) == [[0, 1, 2, 3]]


#============================================
def test_body_content_changes_rating_arrangement() -> None:
	"""Dense prose changes the space budget with the same ratings and geometry."""
	sparse_rows, sparse_scale = slide_maker.rating_layout.choose_rows(
		[80, 80, 80], 10, [[30] * 4], 5, 200, 200, 140, 20, 18,
	)
	dense_rows, dense_scale = slide_maker.rating_layout.choose_rows(
		[80, 80, 80], 10, [[30] * 50], 5, 200, 200, 140, 20, 18,
	)
	assert len(dense_rows) < len(sparse_rows)
	assert 0 < dense_scale < sparse_scale <= 1
	assert sparse_rows == [[0], [1], [2]]


#============================================
@pytest.mark.parametrize("widths", ([80, 70, 70], [80, 70, 70, 60]))
def test_compact_ratings_pair_critics_and_audience(widths: list[float]) -> None:
	"""Crowded slides pair the two RT facts and retain every available rating."""
	rows, scale = slide_maker.rating_layout.choose_rows(
		widths, 10, [[30] * 50], 5, 200, 200, 140, 20, 18, paired=(1, 2),
	)
	assert any(1 in row and 2 in row for row in rows)
	assert sorted(index for row in rows for index in row) == list(range(len(widths)))
	assert 0 < scale < 1


#============================================
def test_pair_only_rt_when_that_frees_enough_space() -> None:
	"""Stop compacting after the RT pair when the remaining facts can stay separate."""
	rows, scale = slide_maker.rating_layout.choose_rows(
		[80, 70, 70, 60], 10, [[30] * 4], 5, 200, 200, 100, 20, 18, paired=(1, 2),
	)
	assert rows == [[0], [1, 2], [3]]
	assert scale == 1


#============================================
def test_preferred_pair_wraps_as_a_unit() -> None:
	"""RT stays together even when the other facts must occupy separate rows."""
	assert slide_maker.rating_layout.pack_rows(
		[110, 60, 60, 100], 5, 150, paired=(1, 2),
	) == [[0], [3], [1, 2]]


#============================================
def test_rating_items_keep_zero_and_independent_votes() -> None:
	"""An absent IMDb score leaves its votes and the other zero-valued scores usable."""
	movie = slide_maker.moviedata.MovieData(
		title="Sparse", imdb_votes=1200, rt_tomatometer=0, rt_audience_score=0, metascore=0,
	)
	items = slide_maker.slide_builder.rating_items(movie)
	assert items[0] == ("IMDb: 1.2k votes", "")
	assert [text for text, unused_score in items[1:]] == [
		"RT critics: \U0001f922 0%",
		"RT audience: \U0001f37f\U0001f44e 0%",
		"Metacritic: \U0001f7e5 0",
	]

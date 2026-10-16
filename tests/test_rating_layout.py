"""Protect whole-item wrapping and content-sensitive rating composition."""

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

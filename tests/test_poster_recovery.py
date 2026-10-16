"""Protect alternate artwork recovery and the required-poster publication boundary."""

# Standard Library
import io
import json
import types
import pathlib
import unittest.mock

# PIP3 modules
import pytest
import PIL.Image #pillow

# local repo modules
import slide_maker.tmdb_client
import slide_maker.movie_pipeline


#============================================
@pytest.mark.parametrize("primary", [None, "/broken.jpg"])
def test_tmdb_recovers_alternate_poster(primary: str | None, tmp_path: pathlib.Path) -> None:
	"""Missing and broken primary artwork both recover a decodable alternate."""
	payload = io.BytesIO()
	PIL.Image.new("RGB", (20, 30)).save(payload, format="PNG")
	details = {"id": 42, "title": "Movie", "poster_path": primary}
	images = {"id": 42, "posters": [{"file_path": primary}, {"file_path": "/alternate.png"}]}
	responses = [types.SimpleNamespace(status_code=200, url="details", text=json.dumps(details))]
	if primary:
		responses.append(types.SimpleNamespace(status_code=404, content=b""))
	responses.append(types.SimpleNamespace(status_code=200, url="images", text=json.dumps(images)))
	responses.append(types.SimpleNamespace(status_code=200, content=payload.getvalue()))
	with unittest.mock.patch("slide_maker.config.load", return_value="test-token"):
		with unittest.mock.patch("slide_maker.http_client.fetch_url", side_effect=responses):
			movie = slide_maker.tmdb_client.fetch_movie(42, tmp_path)
	assert pathlib.Path(movie.poster_path).read_bytes() == payload.getvalue()


#============================================
def test_exhausted_posters_stop_generation(tmp_path: pathlib.Path) -> None:
	"""An unsuccessful poster pull fails before producing a presentation."""
	responses = [
		types.SimpleNamespace(status_code=200, url="details", text='{"id":42,"title":"Movie"}'),
		types.SimpleNamespace(
			status_code=200, url="images",
			text='{"id":42,"posters":[{"file_path":"/broken.jpg"}]}',
		),
		types.SimpleNamespace(status_code=404, content=b""),
	]
	with unittest.mock.patch("slide_maker.config.load", return_value="test-token"):
		with unittest.mock.patch("slide_maker.http_client.fetch_url", side_effect=responses):
			with pytest.raises(slide_maker.movie_pipeline.MoviePipelineError, match="poster retrieval failed"):
				slide_maker.movie_pipeline.generate_movie_slide(
					"tmdb:42", tmp_path, write_line=unittest.mock.Mock(),
				)
	assert not list(tmp_path.glob("*.odp")) and not list(tmp_path.glob("*.pptx"))

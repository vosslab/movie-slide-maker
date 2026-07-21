#!/usr/bin/env python3
"""Collect one movie input and dispatch the movie-slide pipeline."""

# local repo modules
import slide_maker.movie_pipeline


#============================================
def main() -> None:
	"""Read one interactive movie identifier and generate its ODP slide."""
	raw_input = input("Movie title/year, IMDb id or URL, or TMDB id or URL: ")
	slide_maker.movie_pipeline.generate_movie_slide(raw_input)


if __name__ == "__main__":
	main()

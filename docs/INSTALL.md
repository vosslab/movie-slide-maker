# Install

Movie Slide Maker runs from its source checkout. Installation provides a Python 3.12 runtime,
the `slide_maker` package dependencies, LibreOffice conversion, Poppler rendering tools, and the
OpenDyslexic font used by the presentation template.

## Requirements

- macOS with Bash and Homebrew.
- Python 3.12, pinned by the repository environment.
- LibreOffice Still for PPTX-to-ODP conversion.
- Poppler for PDF inspection and PNG page rendering.
- OpenDyslexic installed as a macOS system font.
- A TMDB v4 Read Access Token for live movie resolution and metadata.

The repository's `Brewfile` declares Python 3.12, LibreOffice Still, and Poppler. OpenDyslexic is
a separate font requirement and must be available to LibreOffice before slides are generated.

## Install steps

From the repository root, install the system dependencies:

```bash
brew bundle
```

Install OpenDyslexic through macOS Font Book, then start or restart LibreOffice so it can discover
the font.

Install the five direct Python dependencies:

```bash
source source_me.sh
python3 -m pip install -r pip_requirements.txt
```

Create the ignored local credential file if it does not already exist:

```bash
cp tmdb_key_sample.yml tmdb_key.yml
```

Replace the sample value with the TMDB v4 Read Access Token:

```yaml
read_token: your_tmdb_v4_read_access_token
```

Keep `tmdb_key.yml` local. The runtime reads this exact root-level file and requires a nonempty
`read_token` value.

## Verify install

Verify the Python package and both external command-line tools:

```bash
source source_me.sh
python3 -c "import slide_maker.movie_pipeline; print('Movie Slide Maker imports OK')"
soffice --version
pdfinfo -v
```

The import command must print `Movie Slide Maker imports OK`; the other commands must report their
installed versions. A complete live product check is documented in [USAGE.md](USAGE.md).

## Troubleshooting

- A missing or empty `read_token` error means `tmdb_key.yml` is absent, still contains no token, or
  does not contain the required YAML mapping.
- A LibreOffice conversion error means the installed `soffice` command could not create or validate
  the ODP. Confirm that `brew bundle` completed and LibreOffice Still launches on this Mac.
- Incorrect typography means OpenDyslexic is unavailable to LibreOffice. Confirm the font appears in
  Font Book, then restart LibreOffice before retrying.

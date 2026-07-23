#!/usr/bin/env python3
"""Probe live movie sources and write reproducible evidence captures."""

# Standard Library
import re
import json
import hashlib
import pathlib
import argparse
import datetime
import subprocess
import dataclasses
import html.parser
import urllib.parse

# PIP3 modules
import imdbinfo.services

# Resolve the repository root before importing the production package.
repo_result = subprocess.run(
	["git", "rev-parse", "--show-toplevel"],
	check=True,
	capture_output=True,
	text=True,
)
REPO_ROOT = pathlib.Path(repo_result.stdout.strip())

# local repo modules
import slide_maker.config
import slide_maker.http_client


PROBE_OUTPUT_DIR = REPO_ROOT / "output_smoke" / "movie_source_probe"
CAPTURE_DIR = PROBE_OUTPUT_DIR / "captured"
IMDBINFO_CACHE_PATH = (
	PROBE_OUTPUT_DIR / "runtime_cache" / "imdbinfo" / "waf_cookies.json"
)
REPORT_PATH = (
	REPO_ROOT / "docs" / "active_plans" / "audits" / "movie_source_probe_report.md"
)
TMDB_API_ROOT = "https://api.themoviedb.org/3"


#============================================
def parse_args() -> argparse.Namespace:
	"""Parse the maintainer command line."""
	parser = argparse.ArgumentParser(
		description=(
			"Probe live movie providers, replace ignored response captures, and update "
			"the source-probe audit report."
		),
	)
	args = parser.parse_args()
	return args


@dataclasses.dataclass(frozen=True)
class SampleMovie:
	"""One movie in the evidence sample."""

	key: str
	title: str
	year: int
	imdb_id: str
	directors: tuple[str, ...]
	rt_path: str
	metacritic_path: str
	note: str


@dataclasses.dataclass(frozen=True)
class FetchRecord:
	"""One HTTP response plus retry evidence."""

	url: str
	status_code: int
	content: bytes
	text: str
	statuses: tuple[int, ...]


@dataclasses.dataclass(frozen=True)
class ProbeResult:
	"""Outcomes for one source and movie."""

	source: str
	movie: str
	resolution: str
	parse: str
	absence: str
	correct: bool
	path: str
	keys: str
	observed: str
	blocking: str
	target: str
	captures: tuple[str, ...]


SAMPLE_MOVIES = (
	SampleMovie(
		key="her_2013",
		title="Her",
		year=2013,
		imdb_id="tt1798709",
		directors=("Spike Jonze",),
		rt_path="her",
		metacritic_path="her",
		note="reference film",
	),
	SampleMovie(
		key="cooties_2014",
		title="Cooties",
		year=2014,
		imdb_id="tt2490326",
		directors=("Jonathan Milott", "Cary Murnion"),
		rt_path="cooties",
		metacritic_path="cooties",
		note="rotten critic and audience scores",
	),
	SampleMovie(
		key="it_2017",
		title="It",
		year=2017,
		imdb_id="tt1396484",
		directors=("Andy Muschietti",),
		rt_path="it_2017",
		metacritic_path="it",
		note="ambiguous title and slug",
	),
	SampleMovie(
		key="sinners_2025",
		title="Sinners",
		year=2025,
		imdb_id="tt31193180",
		directors=("Ryan Coogler",),
		rt_path="sinners_2025",
		metacritic_path="sinners",
		note="current-release freshness",
	),
	SampleMovie(
		key="a_ghost_waits_2020",
		title="A Ghost Waits",
		year=2020,
		imdb_id="tt6048638",
		directors=("Adam Stovall",),
		rt_path="a_ghost_waits",
		metacritic_path="a-ghost-waits",
		note="low-vote film with mandatory-field absences",
	),
)


class SourcePageParser(html.parser.HTMLParser):
	"""Collect structured scripts and the RT critics consensus."""

	def __init__(self) -> None:
		"""Initialize collection state."""
		super().__init__()
		self.scripts: list[tuple[dict[str, str | None], str]] = []
		self.consensus: str | None = None
		self._script_attributes: dict[str, str | None] | None = None
		self._script_parts: list[str] = []
		self._saw_consensus_label = False
		self._in_consensus = False
		self._consensus_parts: list[str] = []

	def handle_starttag(
		self,
		tag: str,
		attrs: list[tuple[str, str | None]],
	) -> None:
		"""Start collecting a relevant element."""
		if tag == "script":
			self._script_attributes = dict(attrs)
			self._script_parts = []
		if tag == "p" and self._saw_consensus_label:
			self._in_consensus = True
			self._consensus_parts = []

	def handle_data(self, data: str) -> None:
		"""Collect script text and consensus text."""
		if self._script_attributes is not None:
			self._script_parts.append(data)
		if data.strip().casefold() == "critics consensus":
			self._saw_consensus_label = True
		if self._in_consensus:
			self._consensus_parts.append(data)

	def handle_endtag(self, tag: str) -> None:
		"""Finish collecting a relevant element."""
		if tag == "script" and self._script_attributes is not None:
			body = "".join(self._script_parts)
			self.scripts.append((self._script_attributes, body))
			self._script_attributes = None
			self._script_parts = []
		if tag == "p" and self._in_consensus:
			consensus = " ".join("".join(self._consensus_parts).split())
			self.consensus = consensus
			self._in_consensus = False
			self._saw_consensus_label = False


#============================================
def normalized_title(title: str) -> str:
	"""Normalize a title for identity comparison."""
	normalized = re.sub(r"[^a-z0-9]+", "", title.casefold())
	return normalized


#============================================
def configure_probe_cache() -> None:
	"""Keep imdbinfo state in probe output and route its request through the shared client."""
	imdbinfo.services._WAF_COOKIE_FILE = IMDBINFO_CACHE_PATH
	imdbinfo.services.request_handler = fetch_imdbinfo_reference


#============================================
def imdb_cookie_header() -> str | None:
	"""Load cached imdbinfo cookies without exposing their values."""
	if not IMDBINFO_CACHE_PATH.is_file():
		return None
	cookies = json.loads(IMDBINFO_CACHE_PATH.read_text(encoding="ascii"))
	if not isinstance(cookies, dict):
		raise ValueError("imdbinfo cookie cache must contain a mapping")
	parts = [f"{name}={value}" for name, value in cookies.items()]
	header = "; ".join(parts)
	return header


#============================================
def fetch_imdbinfo_reference(url: str) -> object:
	"""Fetch imdbinfo's reference page through the production HTTP policy."""
	headers = dict(imdbinfo.services.HEADERS)
	cookie_header = imdb_cookie_header()
	if cookie_header is not None:
		headers["Cookie"] = cookie_header
	response = slide_maker.http_client.fetch_url(url, headers)
	return response


#============================================
def fetch_url(url: str, extra_headers: dict[str, str] | None = None) -> FetchRecord:
	"""Fetch one URL through the production HTTP policy."""
	response = slide_maker.http_client.fetch_url(url, extra_headers)
	record = FetchRecord(
		url=str(response.url),
		status_code=response.status_code,
		content=response.content,
		text=response.text,
		statuses=(response.status_code,),
	)
	return record


#============================================
def save_capture(filename: str, content: bytes) -> str:
	"""Save response bytes and return the repo-relative filename."""
	CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
	path = CAPTURE_DIR / filename
	path.write_bytes(content)
	relative_path = path.relative_to(REPO_ROOT).as_posix()
	return relative_path


#============================================
def save_json_capture(filename: str, data: object) -> str:
	"""Save deterministic JSON evidence and return the repo-relative filename."""
	content = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True)
	content += "\n"
	relative_path = save_capture(filename, content.encode("ascii"))
	return relative_path


#============================================
def blocking_summary(statuses: tuple[int, ...]) -> str:
	"""Describe any blocking or rate-limit status."""
	blocked = [str(status) for status in statuses if status in (403, 429)]
	if not blocked:
		return "none"
	if statuses[-1] not in (403, 429):
		summary = f"HTTP {'/'.join(blocked)}; retry succeeded with {statuses[-1]}"
		return summary
	summary = f"HTTP {'/'.join(str(status) for status in statuses)}"
	return summary


#============================================
def tmdb_url(path: str, params: dict[str, str]) -> str:
	"""Build a TMDB API URL without credentials in its query string."""
	query = urllib.parse.urlencode(params)
	url = f"{TMDB_API_ROOT}{path}?{query}"
	return url


#============================================
def select_tmdb_result(results: list[dict], sample: SampleMovie) -> dict:
	"""Select the exact title and release-year result."""
	for result in results:
		titles = (result["title"], result["original_title"])
		title_matches = any(
			normalized_title(title) == normalized_title(sample.title)
			for title in titles
		)
		release_date = result["release_date"]
		if title_matches and release_date.startswith(str(sample.year)):
			return result
	raise ValueError("TMDB search did not return the exact title and year")


#============================================
def probe_tmdb(sample: SampleMovie, token: str) -> ProbeResult:
	"""Probe TMDB search and detail endpoints for one movie."""
	headers = {"Authorization": f"Bearer {token}"}
	search_url = tmdb_url(
		"/search/movie",
		{"query": sample.title, "year": str(sample.year), "language": "en-US"},
	)
	search = fetch_url(search_url, headers)
	search_capture = save_capture(f"tmdb_{sample.key}_search.json", search.content)
	if search.status_code != 200:
		raise ValueError(f"TMDB search returned HTTP {search.status_code}")
	search_data = json.loads(search.text)
	selected = select_tmdb_result(search_data["results"], sample)

	detail_url = tmdb_url(
		f"/movie/{selected['id']}",
		{"append_to_response": "credits,external_ids", "language": "en-US"},
	)
	detail = fetch_url(detail_url, headers)
	detail_capture = save_capture(f"tmdb_{sample.key}_details.json", detail.content)
	if detail.status_code != 200:
		raise ValueError(f"TMDB detail returned HTTP {detail.status_code}")
	detail_data = json.loads(detail.text)
	directors = [
		person["name"]
		for person in detail_data["credits"]["crew"]
		if person["job"] == "Director"
	]
	if detail_data["external_ids"]["imdb_id"] != sample.imdb_id:
		raise ValueError("TMDB external IMDB id does not match the sample")
	if normalized_title(detail_data["title"]) != normalized_title(sample.title):
		raise ValueError("TMDB detail title does not match the sample")
	if not any(director in sample.directors for director in directors):
		raise ValueError("TMDB director does not match the sample")

	blocking_parts = (
		blocking_summary(search.statuses),
		blocking_summary(detail.statuses),
	)
	blocking = "; ".join(part for part in blocking_parts if part != "none")
	if not blocking:
		blocking = "none"
	observed = (
		f"tmdb_id={detail_data['id']}; imdb_id={detail_data['external_ids']['imdb_id']}; "
		f"directors={', '.join(directors)}"
	)
	result = ProbeResult(
		source="TMDB",
		movie=f"{sample.title} ({sample.year})",
		resolution="OK",
		parse="OK",
		absence="none",
		correct=True,
		path="search/movie + movie/{id}?append_to_response=credits,external_ids",
		keys=(
			"results[].{id,title,original_title,release_date}; "
			"{id,title,release_date,overview,genres,runtime,poster_path}; "
			"credits.crew[].{job,name}; external_ids.imdb_id"
		),
		observed=observed,
		blocking=blocking,
		target=detail.url,
		captures=(search_capture, detail_capture),
	)
	return result


#============================================
def imdb_model_data(movie: object) -> dict:
	"""Convert the installed imdbinfo model to JSON-compatible data."""
	model_dump = getattr(movie, "model_dump")
	data = model_dump(mode="json")
	return data


#============================================
def json_ld_records(page: SourcePageParser) -> list[dict]:
	"""Parse dictionary-shaped JSON-LD records from a page."""
	records = []
	for attributes, body in page.scripts:
		if attributes.get("type") != "application/ld+json":
			continue
		parsed = json.loads(body)
		if isinstance(parsed, dict):
			records.append(parsed)
		if isinstance(parsed, list):
			records.extend(item for item in parsed if isinstance(item, dict))
	return records


#============================================
def imdb_json_ld(page: SourcePageParser) -> dict:
	"""Find the IMDB movie JSON-LD record."""
	for record in json_ld_records(page):
		if record.get("@type") == "Movie":
			return record
	raise ValueError("IMDB JSON-LD movie record is missing")


#============================================
def parse_imdb_fallback(record: FetchRecord, sample: SampleMovie) -> tuple[float, int]:
	"""Parse rating and vote count from direct-page JSON-LD."""
	if record.status_code != 200:
		raise ValueError(f"direct IMDB page returned HTTP {record.status_code}")
	page = SourcePageParser()
	page.feed(record.text)
	data = imdb_json_ld(page)
	if normalized_title(data["name"]) != normalized_title(sample.title):
		raise ValueError("IMDB JSON-LD title does not match the sample")
	rating = float(data["aggregateRating"]["ratingValue"])
	votes = int(data["aggregateRating"]["ratingCount"])
	return rating, votes


#============================================
def probe_imdb(sample: SampleMovie) -> ProbeResult:
	"""Probe imdbinfo first and retain the direct-page fallback evidence."""
	url = f"https://www.imdb.com/title/{sample.imdb_id}/"
	direct = fetch_url(url)
	direct_capture = save_capture(f"imdb_{sample.key}_direct.html", direct.content)
	movie = imdbinfo.services.get_movie(sample.imdb_id)
	path = "imdbinfo"
	keys = (
		"props.pageProps.mainColumnData.ratingsSummary.{aggregateRating,voteCount}"
	)
	if movie is not None and movie.rating is not None and movie.votes is not None:
		rating = float(movie.rating)
		votes = int(movie.votes)
		model_data = imdb_model_data(movie)
		model_capture = save_json_capture(
			f"imdb_{sample.key}_imdbinfo.json",
			model_data,
		)
		captures = (direct_capture, model_capture)
		resolved_title = movie.title
		resolved_year = movie.year
	else:
		rating, votes = parse_imdb_fallback(direct, sample)
		path = "curl_cffi + JSON-LD"
		keys = "name; aggregateRating.{ratingValue,ratingCount}"
		captures = (direct_capture,)
		resolved_title = sample.title
		resolved_year = sample.year

	if normalized_title(resolved_title) != normalized_title(sample.title):
		raise ValueError("IMDB title does not match the sample")
	if resolved_year != sample.year:
		raise ValueError("IMDB year does not match the sample")
	if not 0.0 <= rating <= 10.0 or votes < 1:
		raise ValueError("IMDB rating or vote count is outside a plausible range")
	blocking = blocking_summary(direct.statuses)
	if direct.status_code == 202 and path == "imdbinfo":
		blocking = "direct HTML HTTP 202 challenge; imdbinfo succeeded"
	observed = f"imdb_id={sample.imdb_id}; rating={rating:.1f}; votes={votes}"
	result = ProbeResult(
		source="IMDB",
		movie=f"{sample.title} ({sample.year})",
		resolution="OK",
		parse="OK",
		absence="none",
		correct=True,
		path=path,
		keys=keys,
		observed=observed,
		blocking=blocking,
		target=url,
		captures=captures,
	)
	return result


#============================================
def page_json(page: SourcePageParser, attribute: str, value: str) -> dict:
	"""Return a dictionary JSON script selected by one attribute."""
	for attributes, body in page.scripts:
		if attributes.get(attribute) == value:
			parsed = json.loads(body)
			if not isinstance(parsed, dict):
				raise ValueError(f"{value} JSON root is not a mapping")
			return parsed
	raise ValueError(f"page JSON script is missing: {attribute}={value}")


#============================================
def identity_count(
	name: str,
	date_text: str,
	director_names: list[str],
	sample: SampleMovie,
) -> int:
	"""Count independent title, year, and director identity matches."""
	matches = 0
	if normalized_title(name) == normalized_title(sample.title):
		matches += 1
	if date_text.startswith(str(sample.year)):
		matches += 1
	director_matches = any(
		normalized_title(actual) == normalized_title(expected)
		for actual in director_names
		for expected in sample.directors
	)
	if director_matches:
		matches += 1
	return matches


#============================================
def probe_rt(sample: SampleMovie) -> ProbeResult:
	"""Probe a Rotten Tomatoes movie page and distinguish consensus absence."""
	url = f"https://www.rottentomatoes.com/m/{sample.rt_path}"
	record = fetch_url(url)
	capture = save_capture(f"rt_{sample.key}.html", record.content)
	if record.status_code != 200:
		raise ValueError(f"RT page returned HTTP {record.status_code}")
	page = SourcePageParser()
	page.feed(record.text)
	vanity = page_json(page, "data-json", "vanity")
	scorecard = page_json(page, "id", "media-scorecard-json")
	watch_data = page_json(page, "id", "where-to-watch-json")
	title = str(vanity["title"])
	date_text = str(vanity["lifecycleWindow"]["date"])
	director = str(watch_data["director"])
	matches = identity_count(title, date_text, [director], sample)
	if matches < 2:
		raise ValueError("RT page failed the two-factor movie identity check")
	tomatometer = int(scorecard["criticsScore"]["score"])
	if not 0 <= tomatometer <= 100:
		raise ValueError("RT Tomatometer is outside 0-100")
	audience_data = scorecard.get("audienceScore")
	audience_score = None
	if isinstance(audience_data, dict) and audience_data.get("score") is not None:
		audience_score = int(audience_data["score"])
		if not 0 <= audience_score <= 100:
			raise ValueError("RT Popcornmeter is outside 0-100")
	consensus_present = page.consensus is not None and bool(page.consensus.strip())
	absence = "none" if consensus_present else "CLEAN: critics consensus missing"
	audience_text = str(audience_score) if audience_score is not None else "absent"
	observed = (
		f"tomatometer={tomatometer}; audience={audience_text}; "
		f"consensus={'present' if consensus_present else 'absent'}"
	)
	result = ProbeResult(
		source="Rotten Tomatoes",
		movie=f"{sample.title} ({sample.year})",
		resolution=f"OK ({matches}/3 identity checks)",
		parse="OK",
		absence=absence,
		correct=True,
		path="media-scorecard-json + What to Know HTML",
		keys=(
				"vanity.{title,lifecycleWindow.date}; where-to-watch-json.director; "
				"media-scorecard-json.{criticsScore.score,audienceScore.score}; "
				"Critics Consensus + p"
			),
		observed=observed,
		blocking=blocking_summary(record.statuses),
		target=record.url,
		captures=(capture,),
	)
	return result


#============================================
def ld_people_names(value: object) -> list[str]:
	"""Read person names from one JSON-LD person object or list."""
	people = value if isinstance(value, list) else [value]
	names = []
	for person in people:
		if isinstance(person, dict) and isinstance(person.get("name"), str):
			names.append(person["name"])
	return names


#============================================
def metacritic_json_ld(page: SourcePageParser) -> dict:
	"""Find the Metacritic movie JSON-LD record."""
	for record in json_ld_records(page):
		record_type = record.get("@type")
		if record_type in ("Movie", "CreativeWork") and "name" in record:
			return record
	raise ValueError("Metacritic movie JSON-LD record is missing")


#============================================
def probe_metacritic(sample: SampleMovie) -> ProbeResult:
	"""Probe Metacritic JSON-LD and distinguish a missing Metascore."""
	url = f"https://www.metacritic.com/movie/{sample.metacritic_path}/"
	record = fetch_url(url)
	capture = save_capture(f"metacritic_{sample.key}.html", record.content)
	if record.status_code != 200:
		raise ValueError(f"Metacritic page returned HTTP {record.status_code}")
	page = SourcePageParser()
	page.feed(record.text)
	data = metacritic_json_ld(page)
	title = str(data["name"])
	date_text = str(data["datePublished"])
	director_names = ld_people_names(data.get("director", []))
	matches = identity_count(title, date_text, director_names, sample)
	if matches < 2:
		raise ValueError("Metacritic page failed the two-factor movie identity check")
	aggregate_rating = data.get("aggregateRating")
	if aggregate_rating is None:
		absence = "CLEAN: Metascore missing"
		parse_status = "N/A: field absent"
		observed = "metascore=absent"
	else:
		if not isinstance(aggregate_rating, dict):
			raise ValueError("Metacritic aggregateRating is not a mapping")
		metascore = int(aggregate_rating["ratingValue"])
		if not 0 <= metascore <= 100:
			raise ValueError("Metascore is outside 0-100")
		absence = "none"
		parse_status = "OK"
		observed = f"metascore={metascore}"
	result = ProbeResult(
		source="Metacritic",
		movie=f"{sample.title} ({sample.year})",
		resolution=f"OK ({matches}/3 identity checks)",
		parse=parse_status,
		absence=absence,
		correct=True,
		path="ld+json",
		keys="name; datePublished; director[].name; aggregateRating.ratingValue",
		observed=observed,
		blocking=blocking_summary(record.statuses),
		target=record.url,
		captures=(capture,),
	)
	return result


#============================================
def failed_result(source: str, sample: SampleMovie, error: Exception) -> ProbeResult:
	"""Build a failure row without hiding the source error."""
	message = f"{type(error).__name__}: {error}"
	result = ProbeResult(
		source=source,
		movie=f"{sample.title} ({sample.year})",
		resolution="FAIL",
		parse="FAIL",
		absence="UNKNOWN",
		correct=False,
		path="none",
		keys="none",
		observed=message,
		blocking="probe error",
		target="not resolved",
		captures=(),
	)
	return result


#============================================
def guarded_probe(
	probe_name: str,
	probe_function: object,
	sample: SampleMovie,
	*probe_args: object,
) -> ProbeResult:
	"""Run one probe and convert a narrow operational failure into evidence."""
	try:
		result = probe_function(sample, *probe_args)
	except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
		result = failed_result(probe_name, sample, error)
	return result


#============================================
def markdown_cell(value: str) -> str:
	"""Escape one value for a compact Markdown table cell."""
	cell = value.replace("|", "\\|").replace("\n", " ")
	return cell


#============================================
def source_totals(results: list[ProbeResult], source: str) -> str:
	"""Summarize resolution, applicable parse, absence, and correctness totals."""
	rows = [result for result in results if result.source == source]
	resolved = sum(result.resolution.startswith("OK") for result in rows)
	applicable = [result for result in rows if not result.parse.startswith("N/A")]
	parsed = sum(result.parse == "OK" for result in applicable)
	absence_rows = [result for result in rows if result.absence.startswith("CLEAN")]
	correct = sum(result.correct for result in rows)
	summary = (
		f"resolution {resolved}/{len(rows)}; parse {parsed}/{len(applicable)} applicable; "
		f"clean absence {len(absence_rows)}; correct outcome {correct}/{len(rows)}"
	)
	return summary


#============================================
def write_manifest(results: list[ProbeResult], generated_at: str) -> str:
	"""Write hashes and sizes for every saved capture."""
	files = []
	for result in results:
		for relative_name in result.captures:
			path = REPO_ROOT / relative_name
			content = path.read_bytes()
			files.append({
				"bytes": len(content),
				"path": relative_name,
				"sha256": hashlib.sha256(content).hexdigest(),
				"source": result.source,
				"movie": result.movie,
				"target": result.target,
			})
	manifest = {
		"generated_at": generated_at,
		"credential_values_captured": False,
		"files": files,
	}
	manifest_path = save_json_capture("manifest.json", manifest)
	return manifest_path


#============================================
def write_report(
	results: list[ProbeResult],
	generated_at: str,
	manifest_path: str,
) -> None:
	"""Write the complete source-probe audit report."""
	sources = ("TMDB", "IMDB", "Rotten Tomatoes", "Metacritic")
	lines = [
		"# Movie source probe report",
		"",
		f"Generated: `{generated_at}`",
		"",
		"This live probe separates page resolution, parsing of fields that exist, and clean",
		"absence of fields that genuinely do not exist. A clean absence is a valid probe outcome;",
		"the later product still treats missing RT consensus or Metascore as a mandatory abort.",
		"Every live request uses the production `slide_maker/http_client.py` policy, and TMDB",
		"credentials come from `slide_maker/config.py`.",
		"Credential values are never written to captures or this report.",
		"Raw responses are reproducibly generated under",
		"`output_smoke/movie_source_probe/captured/`. That gitignored directory contains probe",
		"evidence, not committed test inputs. Probe-specific runtime cache data stays under",
		"`output_smoke/movie_source_probe/runtime_cache/`.",
		"",
		"## Sample",
		"",
		"| Movie | IMDB id | Stress case |",
		"| --- | --- | --- |",
	]
	for sample in SAMPLE_MOVIES:
		lines.append(
			f"| {sample.title} ({sample.year}) | `{sample.imdb_id}` | {sample.note} |"
		)
	lines.extend(["", "## Source totals", ""])
	for source in sources:
		lines.append(f"- {source}: {source_totals(results, source)}")
	lines.extend([
		"",
		"## Evidence rows",
		"",
		"| Source | Movie | Resolution | Parse | Absence | Correct | Path | Observed | Blocking | Target URL or id |",
		"| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
	])
	for result in results:
		cells = (
			result.source,
			result.movie,
			result.resolution,
			result.parse,
			result.absence,
			"YES" if result.correct else "NO",
			result.path,
			result.observed,
			result.blocking,
			result.target,
		)
		escaped = " | ".join(markdown_cell(cell) for cell in cells)
		lines.append(f"| {escaped} |")
	lines.extend([
		"",
		"## Parse contracts",
		"",
		"| Source | Winning path | Exact keys or selector |",
		"| --- | --- | --- |",
	])
	for source in sources:
		source_rows = [result for result in results if result.source == source]
		paths = sorted(set(result.path for result in source_rows))
		keys = sorted(set(result.keys for result in source_rows))
		lines.append(
			f"| {source} | {markdown_cell('; '.join(paths))} | "
			f"{markdown_cell('; '.join(keys))} |"
		)
	lines.extend([
		"",
		"## Capture index",
		"",
		f"Manifest: `{manifest_path}`",
		"",
		"The manifest and response captures are generated output and remain uncommitted.",
		"Each SHA-256 value below is computed from the corresponding raw response.",
		"",
		"| Source | Movie | Target URL or id | Capture | SHA-256 |",
		"| --- | --- | --- | --- | --- |",
	])
	for result in results:
		for relative_name in result.captures:
			capture_path = REPO_ROOT / relative_name
			digest = hashlib.sha256(capture_path.read_bytes()).hexdigest()
			lines.append(
				f"| {markdown_cell(result.source)} | {markdown_cell(result.movie)} | "
				f"{markdown_cell(result.target)} | `{relative_name}` | `{digest}` |"
			)
	lines.extend([
		"",
		"## Provider gate",
		"",
	])
	for source in sources:
		failed = [
			result.movie
			for result in results
			if result.source == source and not result.correct
		]
		if failed:
			lines.append(
				f"- {source}: BLOCKED. Alternate path required for {', '.join(failed)}."
			)
		else:
			lines.append(f"- {source}: GO. All five outcomes were classified correctly.")
	lines.append("")
	REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
	REPORT_PATH.write_text("\n".join(lines), encoding="ascii")


#============================================
def print_summary(results: list[ProbeResult], manifest_path: str) -> None:
	"""Print concise verification evidence."""
	print("Movie source probe complete")
	for source in ("TMDB", "IMDB", "Rotten Tomatoes", "Metacritic"):
		print(f"{source}: {source_totals(results, source)}")
	print(f"Report: {REPORT_PATH.relative_to(REPO_ROOT)}")
	print(f"Capture manifest: {manifest_path}")
	print(f"Capture files: {sum(len(result.captures) for result in results)}")


#============================================
def main() -> None:
	"""Run all four live-source probes for all five movies."""
	parse_args()
	CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
	configure_probe_cache()
	token = slide_maker.config.load()
	results = []
	for sample in SAMPLE_MOVIES:
		print(f"Probing {sample.title} ({sample.year})")
		results.append(guarded_probe("TMDB", probe_tmdb, sample, token))
		results.append(guarded_probe("IMDB", probe_imdb, sample))
		results.append(guarded_probe("Rotten Tomatoes", probe_rt, sample))
		results.append(guarded_probe("Metacritic", probe_metacritic, sample))
	generated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
	manifest_path = write_manifest(results, generated_at)
	write_report(results, generated_at, manifest_path)
	print_summary(results, manifest_path)


if __name__ == "__main__":
	main()

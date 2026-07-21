"""Shared browser-like HTTP request policy for movie data providers."""

# Standard Library
import time
import random

# PIP3 modules
import curl_cffi.requests


REQUEST_TIMEOUT_SECONDS = 30
RETRY_STATUS_CODES = (403, 429)


#============================================
def request_headers(extra_headers: dict[str, str] | None = None) -> dict[str, str]:
	"""Build the common browser headers with provider-specific additions.

	Args:
		extra_headers: Additional headers for one provider request.

	Returns:
		A new header mapping for the request.
	"""
	headers = {
		"Accept-Language": "en-US,en;q=0.9",
		"Referer": "https://www.google.com/",
	}
	if extra_headers is not None:
		headers.update(extra_headers)
	return headers


#============================================
def request_once(
	url: str,
	headers: dict[str, str],
	params: dict[str, str | int | float] | None,
) -> curl_cffi.requests.Response:
	"""Perform one delayed browser-like GET request.

	Args:
		url: Absolute provider URL.
		headers: Complete request headers.
		params: Optional query parameters.

	Returns:
		The provider response.
	"""
	time.sleep(random.random())
	response = curl_cffi.requests.get(
		url,
		impersonate="chrome",
		headers=headers,
		params=params,
		timeout=REQUEST_TIMEOUT_SECONDS,
	)
	return response


#============================================
def fetch_url(
	url: str,
	extra_headers: dict[str, str] | None = None,
	params: dict[str, str | int | float] | None = None,
) -> curl_cffi.requests.Response:
	"""Fetch a provider URL with one retry for a blocking response.

	Args:
		url: Absolute provider URL.
		extra_headers: Additional headers for one provider request.
		params: Optional query parameters.

	Returns:
		The initial response, or the single retry response after HTTP 403 or 429.
	"""
	headers = request_headers(extra_headers)
	response = request_once(url, headers, params)
	if response.status_code in RETRY_STATUS_CODES:
		response = request_once(url, headers, params)
	return response

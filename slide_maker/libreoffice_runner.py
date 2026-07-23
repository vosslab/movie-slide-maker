"""Run LibreOffice conversions without direct macOS application registration."""

# Standard Library
import sys
import pathlib
import subprocess


MACOS_APP_NAME = "LibreOffice"


#============================================
def _conversion_command(arguments: list[str]) -> list[str]:
	"""Return the platform-safe LibreOffice launch command."""
	if sys.platform == "darwin":
		command = [
			"open",
			"-g",
			"-n",
			"-W",
			"-a",
			MACOS_APP_NAME,
			"--args",
			*arguments,
		]
	else:
		command = ["soffice", *arguments]
	return command


#============================================
def convert_document(
	source_path: pathlib.Path,
	output_format: str,
	output_directory: pathlib.Path,
	profile_directory: pathlib.Path,
) -> subprocess.CompletedProcess[str]:
	"""Run one synchronous LibreOffice document conversion.

	On macOS, launching the application binary directly can intermittently abort
	while AppKit registers the process and can leave a crash dialog on screen.
	LaunchServices performs that registration safely, ``-g`` keeps the headless
	process in the background, and ``-W`` retains the synchronous command
	contract needed by the validation pipeline.

	Args:
		source_path: Existing presentation or document to convert.
		output_format: LibreOffice output extension such as ``"odp"`` or ``"pdf"``.
		output_directory: Directory that will receive the converted artifact.
		profile_directory: Isolated LibreOffice user-profile directory.

	Returns:
		The completed platform launch process with captured text output.

	Raises:
		ValueError: The output format is empty.
		FileNotFoundError: The source document is absent.
	"""
	if not source_path.is_file():
		raise FileNotFoundError(f"LibreOffice source document is absent: {source_path}")
	if not output_format.strip():
		raise ValueError("LibreOffice output format must be nonempty")
	output_directory.mkdir(parents=True, exist_ok=True)
	arguments = [
		f"-env:UserInstallation={profile_directory.resolve().as_uri()}",
		"--headless",
		"--convert-to",
		output_format,
		"--outdir",
		str(output_directory.resolve()),
		str(source_path.resolve()),
	]
	command = _conversion_command(arguments)
	result = subprocess.run(command, capture_output=True, text=True, check=False)
	return result

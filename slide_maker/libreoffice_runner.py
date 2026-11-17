"""Run isolated headless LibreOffice document conversions."""

# Standard Library
import pathlib
import subprocess


#============================================
def convert_document(
	source_path: pathlib.Path,
	output_format: str,
	output_directory: pathlib.Path,
	profile_directory: pathlib.Path,
) -> subprocess.CompletedProcess[str]:
	"""Run one synchronous LibreOffice document conversion.

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
		"--headless",
		"--norestore",
		"--convert-to",
		output_format,
		f"-env:UserInstallation={profile_directory.resolve().as_uri()}",
		"--outdir",
		str(output_directory.resolve()),
		str(source_path.resolve()),
	]
	command = ["soffice", *arguments]
	result = subprocess.run(command, capture_output=True, text=True, check=False)
	return result

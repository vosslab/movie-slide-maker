"""Load local configuration for the movie slide maker."""

# Standard Library
import pathlib
import subprocess

# PIP3 modules
import yaml


#============================================
def get_repo_root() -> pathlib.Path:
	"""Return the repository root that owns the local credential file."""
	result = subprocess.run(
		["git", "rev-parse", "--show-toplevel"],
		check=True,
		capture_output=True,
		text=True,
	)
	repo_root = pathlib.Path(result.stdout.strip())
	return repo_root


CONFIG_PATH = get_repo_root() / "tmdb_key.yml"


#============================================
def load(config_path: str | pathlib.Path = CONFIG_PATH) -> str:
	"""Load the TMDB v4 read token from a YAML configuration file.

	Args:
		config_path: Path to the YAML configuration file.

	Returns:
		The token used for TMDB ``Authorization: Bearer`` requests.

	Raises:
		ValueError: The file is not a mapping or lacks a non-empty read token.
	"""
	path = pathlib.Path(config_path)
	config_data = yaml.safe_load(path.read_text(encoding="ascii"))
	if not isinstance(config_data, dict):
		raise ValueError(f"{path.name} must contain a YAML mapping")
	if "read_token" not in config_data:
		raise ValueError(f"{path.name} requires a read_token for TMDB v4 access")
	read_token = config_data["read_token"]
	if not isinstance(read_token, str) or not read_token.strip():
		raise ValueError(f"{path.name} read_token must be a non-empty string")
	token = read_token.strip()
	return token

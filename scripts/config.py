"""
Config Manager

Class to manage file-based configuration settings.
"""
# MARK: Imports
import tomllib
from typing import Union, Optional, Any
from pathlib import Path

# MARK: Classes
class Config:
    """
    Class to manage file-based configuration settings.
    """
    # Initializer
    def __init__(self, configPath: Optional[Union[str, Path]] = None):
        """
        configPath: Path to the configuration file. If `None`, will attempt to load `config.toml` from the current working directory.
        """
        # Prep parameters
        self.path = (Path(configPath) if configPath else Path.cwd() / "config.toml").absolute()
        self.data = self._loadConfig()

    # Python Functions
    def __repr__(self) -> str:
        return f"Config(path={self.path.absolute()}, data={self.data})"

    def __str__(self) -> str:
        return self.__repr__()

    # Private Functions
    def _loadConfig(self) -> dict[str, Any]:
        """
        Load the configuration file.
        """
        # Check if the file exists
        if not self.path.exists():
            raise FileNotFoundError(f"Configuration file not found at: {self.path}")

        # Load the configuration file
        with open(self.path, "rb") as f:
            return tomllib.load(f)

    # Functions
    def get(self, *keys, fallback: Optional[Union[KeyError, Any]] = KeyError) -> Optional[Union[dict[str, Any], list[Any], Any]]:
        """
        Retrieve a value from the configuration using a sequence of `keys`.

        *keys: A sequence of keys to traverse the configuration dictionary.
        fallback: Optional value to return if a key along the `*keys` sequence is not found. If the `KeyError` type is provided, a `KeyError` will be raised instead.

        Returns the value found at the specified `keys`.
        """
        # Go find it
        data = self.data
        for key in keys:
            # Check if the key exists
            if (not isinstance(data, dict)) or (key not in data):
                # Check if no fallback is provided
                if fallback == KeyError:
                    raise KeyError(f"Key '{key}' not found in configuration.")

                # Return the fallback value
                return fallback

            # Go deeper
            data = data[key]

        # Return the found data
        return data

    # NOTE: Set is not implemented because Python's `tomllib` does not support writing TOML files.

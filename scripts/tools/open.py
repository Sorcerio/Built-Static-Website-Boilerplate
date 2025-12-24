"""
Open Tool

Opens the static site in the default web browser.
"""
# MARK: Imports
import webbrowser
import argparse
from typing import Optional
from pathlib import Path

from .baseTool import BaseTool
from ..config import Config

# MARK: - BuildTool
class OpenTool(BaseTool):
    """
    Opens the static site in the default web browser.
    """
    # Constants
    TOOL_NAME = "open"
    TOOL_HELP = "Opens the static site in the default web browser."

    # MARK: CLI Functions
    @staticmethod
    def setupParser(parser: argparse.ArgumentParser, config: Optional[Config]):
        """
        Sets up the given `parser` with arguments for this tool.

        parser: The parser to apply the arguments to.
        config: The config manager to use for the tool or `None` if not present.
        """
        pass

    @classmethod
    def fromArgs(cls, args: argparse.Namespace, config: Optional[Config]) -> "OpenTool":
        """
        Creates an instance of this tool from the given `args`.

        args: The parser arguments to create the tool from.
        config: The config manager to use for the tool.

        Returns an instance of this tool.
        """
        return cls()

    def _run(self, args: argparse.Namespace, config: Optional[Config]):
        """
        Runs the tool as configured by the CLI.

        args: The parser arguments to create the tool from.
        config: The config manager to use for the tool.
        """
        # Get the path
        homePath = Path(config.get("build", "outputDirectory")).absolute() / "index.html"

        # Check if it exists
        if not homePath.is_file():
            print("Error: The static site has not been built yet. Please run the `build` tool first.")
            return

        # Just open the thing
        webbrowser.open(str(homePath))

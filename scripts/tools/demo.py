"""
Demo Tool

An example of using the `BaseTool` class to create a command line tool.
"""
# MARK: Imports
import argparse
from typing import Optional

from .baseTool import BaseTool
from ..config import Config

# MARK: Classes
class DemoTool(BaseTool):
    """
    Demo tool for command line tools.
    """
    # Constants
    TOOL_NAME = "demo"
    TOOL_HELP = "Demo tool for command line tools."

    # Initializer
    def __init__(self, isA: bool):
        self.isA = isA

    # CLI Functions
    @staticmethod
    def setupParser(parser: argparse.ArgumentParser, config: Optional[Config]):
        """
        Sets up the given `parser` with arguments for this tool.

        parser: The parser to apply the arguments to.
        config: The config manager to use for the tool or `None` if not present.
        """
        # Add a demo argument
        parser.add_argument(
            "-d",
            "--demo",
            action="store_true",
            help="Run the demo."
        )

    @classmethod
    def fromArgs(cls, args: argparse.Namespace, config: Optional[Config]) -> "DemoTool":
        """
        Creates an instance of this tool from the given `args`.

        args: The parser arguments to create the tool from.
        config: The config manager to use for the tool.

        Returns an instance of this tool.
        """
        return cls(args.demo)

    def _run(self, args: argparse.Namespace, config: Optional[Config]):
        """
        Runs the tool as configured by the CLI.

        args: The parser arguments to create the tool from.
        config: The config manager to use for the tool.
        """
        print("Running demo tool!")
        print(f"Is A: {self.isA}")
        print(f"Args: {args}")
        print(f"Config: {config}")

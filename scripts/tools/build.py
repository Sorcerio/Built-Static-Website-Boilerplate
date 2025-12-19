"""
Build Tool

Builds the static site by rendering templates with content.
"""
# MARK: Imports
import shutil
import webbrowser
import datetime
import argparse
from typing import Optional
from pathlib import Path
from shutil import copytree, copy2

import jinja2
from tqdm import tqdm

from .baseTool import BaseTool
from ..config import Config

# MARK: - BuildTool
class BuildTool(BaseTool):
    """
    Builds the static site by rendering templates with content.
    """
    # Constants
    TOOL_NAME = "build"
    TOOL_HELP = "Builds the static site by rendering templates with content."

    # MARK: Initializer
    def __init__(self,
        rootUrl: str,
        sourceDir: Path,
        templateDir: Path,
        outputDir: Path,
        copyBlacklist: tuple[str, ...]
    ):
        """
        Initializes the build tool.
        """
        # Setup
        super().__init__()

        # Assign properties
        self.rootUrl = rootUrl.rstrip("/")
        self.sourceDir = sourceDir.absolute()
        self.templateDir = templateDir.absolute()
        self.outputDir = outputDir.absolute()
        self.copyBlacklist = copyBlacklist

        # Make output directory
        self.outputDir.mkdir(parents=True, exist_ok=True)

    # MARK: CLI Functions
    @staticmethod
    def setupParser(parser: argparse.ArgumentParser, config: Optional[Config]):
        """
        Sets up the given `parser` with arguments for this tool.

        parser: The parser to apply the arguments to.
        config: The config manager to use for the tool or `None` if not present.
        """
        # NOTE: Most configuration for the CLI is found in the config file.

        # Add optional arguments
        parser.add_argument(
            "-o",
            "--open",
            action="store_true",
            help="Open the index page in the default web browser after building."
        )

    @classmethod
    def fromArgs(cls, args: argparse.Namespace, config: Optional[Config]) -> "BuildTool":
        """
        Creates an instance of this tool from the given `args`.

        args: The parser arguments to create the tool from.
        config: The config manager to use for the tool.

        Returns an instance of this tool.
        """
        return cls(
            rootUrl=config.get("build", "rootUrl"),
            sourceDir=Path(config.get("build", "sourceDirectory")),
            templateDir=Path(config.get("build", "templateDirectory")),
            outputDir=Path(config.get("build", "outputDirectory")),
            copyBlacklist=tuple(config.get("build", "blacklist")),
        )

    def _run(self, args: argparse.Namespace, config: Optional[Config]):
        """
        Runs the tool as configured by the CLI.

        args: The parser arguments to create the tool from.
        config: The config manager to use for the tool.
        """
        self.clean()
        self.build()

        if args.open:
            webbrowser.open(str(self.outputDir / "index.html"))

    # MARK: Functions
    def clean(self):
        """
        Cleans the output directory by deleting its content.
        """
        # Delete the output directory if it exists
        shutil.rmtree(self.outputDir)

        # Recreate the output directory
        self.outputDir.mkdir(parents=True, exist_ok=True)

    def build(self):
        # Load the template environment
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader((
                str(self.templateDir),
                str(self.sourceDir)
            )),
            autoescape=False
        )

        # Report
        print("Templates registered.")

        # TODO: Update the `site.webmanifest` file

        # Render the content to output
        for contentFile in tqdm(tuple(self.sourceDir.glob("*.html")), desc="Rendering content", unit="file"):
            # Build the payload
            payload = {
                "rootUrl": self.rootUrl,
                "pagePath": str(contentFile.relative_to(self.sourceDir)),
                "cacheVersion": datetime.datetime.now(datetime.timezone.utc).strftime("%y%m%d%H%M%S"),
                # **self.socialLinks.dict() # TODO: Reimplement social links support
            }

            # Get the template
            template = env.get_template(
                name=contentFile.name,
                globals=payload
            )

            # Render the template with the content file
            html = template.render()

            # Write the rendered HTML to the output directory
            with open(self.outputDir / contentFile.name, "w") as f:
                f.write(html) # TODO: Minify HTML and remove comments

        # Report
        print("Content rendered.")

        # Copy other files to output
        for otherPath in tqdm(tuple(self.sourceDir.glob("*")), desc="Copying other files", unit="file"):
            # Skip exclusions
            if (otherPath.suffix.lower() == ".html") or (otherPath.name in self.copyBlacklist):
                continue

            # Copy appropriately
            if otherPath.is_dir():
                copytree(otherPath, self.outputDir / otherPath.name, dirs_exist_ok=True)
            else:
                copy2(otherPath, self.outputDir / otherPath.name)

        # Report
        print("Static files copied.")
        print(f"Built to: {self.outputDir}")

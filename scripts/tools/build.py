"""
Build Tool

Builds the static site by rendering templates with content.
"""
# MARK: Imports
import json
import shutil
import webbrowser
import datetime
import argparse
from typing import Optional, Any
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
        name: str,
        nameShort: str,
        rootUrl: str,
        sourceDir: Path,
        templateDir: Path,
        outputDir: Path,
        copyBlacklist: tuple[str, ...],
        socialLinks: dict[str, str] = {},
        overrides: dict[str, Any] = {}
    ):
        """
        name: The name of the website as a whole like `"My Blog"`.
        nameShort: A short name for the website like `"Blog"`.
        rootUrl: The root URL of the site like `"https://example.com"`.
        sourceDir: The directory containing the source content files.
        templateDir: The directory containing the template files.
        outputDir: The directory to output the built site to.
        copyBlacklist: A tuple of file or directory names to exclude from copying.
        socialLinks: A dictionary of social media links to include in the site like `{"substack": "https://mbmcloude.substack.com"}`.
        overrides: A dictionary of additional or override `key:value` pairs to include in the template rendering context. These will override any other values with the same key.
        """
        # Setup
        super().__init__()

        # Assign properties
        self.name = name
        self.nameShort = nameShort
        self.rootUrl = rootUrl.rstrip("/")
        self.sourceDir = sourceDir.absolute()
        self.templateDir = templateDir.absolute()
        self.outputDir = outputDir.absolute()
        self.copyBlacklist = copyBlacklist
        self.socialLinks = socialLinks
        self.overrides = overrides

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
            name=config.get("site", "name"),
            nameShort=config.get("site", "nameShort"),
            rootUrl=config.get("site", "rootUrl"),
            sourceDir=Path(config.get("build", "sourceDirectory")),
            templateDir=Path(config.get("build", "templateDirectory")),
            outputDir=Path(config.get("build", "outputDirectory")),
            copyBlacklist=tuple(config.get("build", "blacklist")),
            socialLinks=config.getDict((str, ), "socialMedia", fallback={}),
            overrides=config.getDict(None, "overrides", fallback={})
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

        # Render the content to output
        for contentFile in tqdm(tuple(self.sourceDir.glob("*.html")), desc="Rendering content", unit="file"):
            # Build the payload
            payload = {
                **self.socialLinks,
                "rootUrl": self.rootUrl,
                "pagePath": str(contentFile.relative_to(self.sourceDir)),
                "cacheVersion": datetime.datetime.now(datetime.timezone.utc).strftime("%y%m%d%H%M%S"),
                **self.overrides # Overrides last to take precedence
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

        # Update the site.webmanifest
        manifestPath = (self.outputDir / "images" / "favicon" / "site.webmanifest").absolute()
        if manifestPath.exists():
            # Open the manifest
            with open(manifestPath, "r") as f:
                manifest = json.load(f)

            # Update the manifest
            manifest["name"] = self.name
            manifest["short_name"] = self.nameShort

            # Write the manifest back
            with open(manifestPath, "w") as f:
                json.dump(manifest, f, indent=2)

            # Report
            print("`site.webmanifest` updated.")
        else:
            # Report
            print("No `site.webmanifest` exists. Skipping update.")

        # TODO: Generate sitemap.xml

        # Final report
        print(f"Built to: {self.outputDir}")

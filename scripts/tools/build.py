"""
Build Tool

Builds the static site by rendering templates with content.
"""
# MARK: Imports
import time
import json
import shutil
import webbrowser
import datetime
import argparse
from typing import Optional, Any
from pathlib import Path
from shutil import copy2

import jinja2
import minify_html
from tqdm import tqdm
from watchdog.events import FileSystemEvent, FileSystemEventHandler, FileModifiedEvent
from watchdog.observers import Observer

from .baseTool import BaseTool
from ..config import Config
from ..models import AttrItem

# MARK: - Static File Synchronization Watcher
class _SFSyncWatcher(FileSystemEventHandler):
    """
    Watches for changes in static files in the project's output directory and writes them back to the source directory.
    """
    # Initializer
    def __init__(self, watchDir: Path, resultDir: Path, bufferDelay: float):
        """
        watchDir: The directory that changes could occur in and should be synced back to the `resultDir`.
        resultDir: The directory that changes should be written back to when they occur in the `watchDir`.
        bufferDelay: The delay in seconds to buffer events to avoid duplicate processing and repeated events.
        """
        # Setup
        super().__init__()

        # Properties
        self.watchDir: Path = watchDir.absolute()
        self.resultDir: Path = resultDir.absolute()
        self.bufferDelay: float = bufferDelay # seconds
        self.events: dict[FileSystemEvent, float] = {} # { event: timestamp }

    # Functions
    def on_modified(self, event: FileModifiedEvent):
        # Check if the event is already buffered
        currentTime = time.time()
        if event in self.events:
            lastTime = self.events[event]
            if (currentTime - lastTime) < self.bufferDelay:
                # Still in buffer delay, ignore
                return

        # Record the event time
        self.events[event] = currentTime

        # Determine event's source path
        srcPath = Path(event.src_path).absolute()

        # Make sure there's no destination path
        # Only process files that are modified *in place*!
        # If files are moved and such in the build output, then the build needs to be rebuilt!
        if str(event.dest_path).strip() != "":
            # Report
            print(f"File was moved, renamed, or otherwise modified outside of its content. Make the change in your source directory and rebuild the site output!\nIgnoring change at: {srcPath}")
            return

        # Make sure the file is in the watchDir
        if not srcPath.is_relative_to(self.watchDir):
            # Report
            print(f"Received a `FileModifiedEvent` for a file outside the watch directory. Build system may be setup incorrectly!\nIgnoring change at: {srcPath}")
            return

        # Determine paired file path in resultDir
        pairedFilePath = self.resultDir / srcPath.relative_to(self.watchDir)

        # Make sure the paired file is in the resultDir
        if not pairedFilePath.exists():
            # Report
            print(f"Paired file does not exist in the build output directory. Verify the file exists in your source directory and rebuild the site output!\nIgnoring change at: {srcPath}")
            return

        # Do the copy back to the resultDir
        copy2(srcPath, pairedFilePath)

        # Report
        print(f"Synchronized: {pairedFilePath.relative_to(self.resultDir.parent)}")

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
        attributions: list[AttrItem] = [],
        copyBlacklist: tuple[str, ...] = tuple(),
        socialLinks: dict[str, str] = {},
        overrides: dict[str, Any] = {},
        staticSync: bool = False
    ):
        """
        name: The name of the website as a whole like `"My Blog"`.
        nameShort: A short name for the website like `"Blog"`.
        rootUrl: The root URL of the site like `"https://example.com"`.
        sourceDir: The directory containing the source content files.
        templateDir: The directory containing the template files.
        outputDir: The directory to output the built site to.
        attributions: A list of `AttrItem` objects to include in the attributions page.
        copyBlacklist: A tuple of file or directory names to exclude from copying.
        socialLinks: A dictionary of social media links to include in the site like `{"substack": "https://mbmcloude.substack.com"}`.
        overrides: A dictionary of additional or override `key:value` pairs to include in the template rendering context. These will override any other values with the same key.
        staticSync: Whether to watch for changes in the build output's static files' content and write them back to the source directory automatically. Changes made in the source directory will still require a rebuild to be reflected in the output.
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
        self.attributions = attributions
        self.copyBlacklist = copyBlacklist
        self.socialLinks = socialLinks
        self.overrides = overrides

        self._doStaticSync = staticSync
        self._staticSyncDelay: float = 1.0 # TODO: Make configurable?
        self._sfChangeHandler: Optional[_SFSyncWatcher] = None
        self._sfChangeObserver = None

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
            "-o", "--open",
            action="store_true",
            help="Open the index page in the default web browser after building."
        )
        parser.add_argument(
            "-s", "--sync",
            action="store_true",
            help=f"Watch for changes in the the build output's (`{Path(config.get('build', 'outputDirectory')).name}/`) static files' content and writes them back to the source directory (`{Path(config.get('build', 'sourceDirectory')).name}/`) automatically. Changes made in the source directory will still require a rebuild to be reflected in the output."
        )

    @classmethod
    def fromArgs(cls, args: argparse.Namespace, config: Optional[Config]) -> "BuildTool":
        """
        Creates an instance of this tool from the given `args`.

        args: The parser arguments to create the tool from.
        config: The config manager to use for the tool.

        Returns an instance of this tool.
        """
        # Pull the source directory
        sourceDir = Path(config.get("build", "sourceDirectory")).absolute()

        # Collect the attributions items
        attrItems: list[AttrItem] = []
        for data in config.getDict(None, "attributions", fallback={}).values():
            # Resolve path
            filePath = Path(data.get("file", None))

            if filePath is None:
                raise ValueError("Attributions item is missing required `file` property.")

            if (not filePath.is_file()) and (filePath.parent == Path(".")):
                filePath = (sourceDir / "attributions" / filePath).absolute()

            if not filePath.is_file():
                raise FileNotFoundError(f"Attributions item file does not exist at path: {filePath}")

            # Build it
            attrItems.append(AttrItem(
                category=data.get("category", ""),
                title=data.get("title", ""),
                link=data.get("link", ""),
                filePath=filePath
            ))

        # Send it
        return cls(
            name=config.get("site", "name"),
            nameShort=config.get("site", "nameShort"),
            rootUrl=config.get("site", "rootUrl"),
            sourceDir=sourceDir,
            templateDir=Path(config.get("build", "templateDirectory")),
            outputDir=Path(config.get("build", "outputDirectory")),
            attributions=attrItems,
            copyBlacklist=tuple(config.get("build", "blacklist")),
            socialLinks=config.getDict((str, ), "socialMedia", fallback={}),
            overrides=config.getDict(None, "overrides", fallback={}),
            staticSync=args.sync
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
        """
        Builds the static site by rendering templates with content.
        """
        # Prepare the Jinja2 environment
        env = self._prepJinjaEnv()

        # Process all files
        self._processFiles(env)

        # Report
        print("Files processed.")

        # Update the site.webmanifest
        self._updateSiteWebManifest()

        # Build the attributions page
        self._buildAttributionsPage(env)

        # Generate sitemap.xml
        self._buildSitemap(env)

        # Report
        print(f"Built to: {self.outputDir}")

        # Check if synchronization is desired
        if self._doStaticSync:
            print("")
            self._startStaticFileSyncWatcher()

    # MARK: Internal Functions
    def _prepJinjaEnv(self) -> jinja2.Environment:
        """
        Prepares and returns a Jinja2 environment for template rendering.

        Returns a Jinja2 environment.
        """
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

        return env

    def _getStandardJinjaPayload(self, contentFile: Path, relPath: Optional[Path] = None) -> dict[str, Any]:
        """
        Returns a standard payload dictionary for Jinja2 template rendering.

        contentFile: The content file being rendered.
        relPath: The relative path from the output directory to the content file. Provide `None` to attempt to auto-resolve.
        """
        # Resolve page path
        pagePath = relPath
        if pagePath is None:
            pagePath = contentFile.relative_to(self.sourceDir)
        pagePath = Path(pagePath)

        # Build it
        return {
            **self.socialLinks,
            "rootUrl": self.rootUrl,
            "pagePath": str(pagePath.as_posix()),
            "cacheVersion": datetime.datetime.now(datetime.timezone.utc).strftime("%y%m%d%H%M%S"),
            **self.overrides # Overrides last to take precedence
        }

    def _processFiles(self, env: jinja2.Environment, root: Optional[Path] = None):
        """
        Processes all files in the input directory as appropriate for their file type.

        env: The Jinja2 environment containing the templates.
        root: The root directory to start searching for HTML files within. Provide `None` to use the source directory.
        """
        # Determine the roots
        if root is None:
            rootInput = self.sourceDir
        else:
            rootInput = root.absolute()

        rootOutput = (self.outputDir / rootInput.relative_to(self.sourceDir)).absolute()

        # Create the output root, if needed
        rootOutput.mkdir(parents=True, exist_ok=True)

        # Walk the input directory
        for item in tqdm(
            tuple(rootInput.iterdir()),
            desc=str(rootInput.relative_to(self.sourceDir.parent)),
            unit="item"
        ):
            # Determine paths
            inputPath = item.absolute()
            outputPath = (rootOutput / item.name).absolute()

            # Decide the action
            if inputPath.name in self.copyBlacklist:
                # Skip blacklisted items
                continue
            elif inputPath.is_dir():
                # Recurse into directory
                self._processFiles(env, root=inputPath)
                continue
            elif inputPath.suffix.lower() == ".html":
                # Construct HTML file
                # Build the payload
                payload = self._getStandardJinjaPayload(inputPath)

                # Get the template
                template = env.get_template(
                    name=inputPath.relative_to(self.sourceDir).as_posix(),
                    globals=payload
                )

                # Render the template with the content file
                html = template.render()

                # Ensure output directory exists
                outputPath.parent.mkdir(parents=True, exist_ok=True)

                # Write the rendered HTML to the output directory
                with open(outputPath, "w", encoding="utf-8") as f:
                    f.write(minify_html.minify(
                        html,
                        keep_closing_tags=True,
                        minify_css=True,
                        minify_js=True,
                        remove_processing_instructions=True
                    ))
            elif inputPath.is_file():
                # Ensure output directory exists
                outputPath.parent.mkdir(parents=True, exist_ok=True)

                # Copy regular files
                copy2(inputPath, outputPath)

                # TODO: Add watcher, if specified
            else:
                # Report unknown item
                print(f"Unhandled file system item type at: {inputPath}")

    def _updateSiteWebManifest(self):
        """
        Updates the `site.webmanifest` file in the output directory.
        """
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
            print("Favicon 'site.webmanifest' updated.")
        else:
            # Report
            print("No favicon 'site.webmanifest' exists. Skipping update.")

    def _buildAttributionsPage(self, env: jinja2.Environment):
        """
        Builds the attributions page.

        env: The Jinja2 environment containing the templates.
        """
        # Prepare the path
        attrsPath = self.outputDir / "attributions.html"

        # Build the attributions list for payload
        payloadAttrData: dict[str, list[dict[str, str]]] = {}
        for item in self.attributions:
            # Prep the item dict
            itemDict = item.toDict()
            itemDict["filePath"] = item.filePath.relative_to(self.sourceDir).as_posix() # NOTE: Notice it's relative to sourceDir because that's where the `filePath` is pointing!

            # Get the content
            itemDict["content"] = item.filePath.read_text(encoding="utf-8")

            # Add the category if needed
            if item.category not in payloadAttrData:
                payloadAttrData[item.category] = []

            # Append the item
            payloadAttrData[item.category].append(itemDict)

        # Build the payload
        payload = self._getStandardJinjaPayload(attrsPath, relPath=attrsPath.name)
        payload["attributions"] = payloadAttrData

        # Get the template
        template = env.get_template(
            name=attrsPath.name,
            globals=payload
        )

        # Render the template with the content file
        html = template.render()

        # Write the rendered HTML to the output directory
        with open(self.outputDir / attrsPath.name, "w") as f:
            f.write(minify_html.minify(
                html,
                keep_closing_tags=True,
                minify_css=True,
                minify_js=True,
                remove_processing_instructions=True
            ))

    def _buildSitemap(self, env: jinja2.Environment):
        """
        Generates the `sitemap.xml` file in the output directory.

        env: The Jinja2 environment containing the templates.
        """
        # Prepare the path
        sitemapPath = self.outputDir / "sitemap.xml"

        # Get all the HTML files
        htmlFiles = tuple(self.outputDir.glob("**/*.html"))

        # Build the payload
        payload = self._getStandardJinjaPayload(sitemapPath, relPath=sitemapPath.name)
        payload["entries"] = [
            {
                "loc": f"{self.rootUrl}/{htmlFile.relative_to(self.outputDir).as_posix()}",
                "lastmod": datetime.datetime.fromtimestamp(htmlFile.stat().st_mtime, datetime.timezone.utc).strftime("%Y-%m-%d")
            }
            for htmlFile in htmlFiles
        ]

        # Get the template
        template = env.get_template(
            name=sitemapPath.name,
            globals=payload
        )

        # Render the template with the content file
        xml = template.render()

        # Write the rendered XML to the output directory
        with open(self.outputDir / sitemapPath.name, "w") as f:
            f.write(xml)

    def _startStaticFileSyncWatcher(self):
        """
        Starts the static file synchronization watcher to monitor changes in the output directory and write them back to the source directory.
        """
        # Report
        print("Waiting for static file changes...")
        print("Press CTRL+C to stop.\n")

        # Create the change handler
        self._sfChangeHandler = _SFSyncWatcher(
            watchDir=self.outputDir,
            resultDir=self.sourceDir,
            bufferDelay=self._staticSyncDelay
        )

        # Create the observer
        self._sfChangeObserver = Observer()
        self._sfChangeObserver.schedule(
            self._sfChangeHandler,
            str(self.outputDir),
            recursive=True,
            event_filter=[FileModifiedEvent]
        )

        # Start observing
        self._sfChangeObserver.start()

        # Enter listening loop
        try:
            while True:
                time.sleep(self._staticSyncDelay)
        except KeyboardInterrupt:
            # Exit on CTRL+C
            pass
        finally:
            # Clean up
            self._sfChangeObserver.stop()
            self._sfChangeObserver.join()

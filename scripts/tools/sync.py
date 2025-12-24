"""
Static File Synchronization Tool

Tool to watch for changes in *static* files in the project's *output* directory and writes them back to the *source* directory.
"""
# MARK: Imports
import time
import argparse
from typing import Optional
from pathlib import Path
from shutil import copy2

from watchdog.events import FileSystemEvent, FileSystemEventHandler, FileModifiedEvent
from watchdog.observers import Observer

from .baseTool import BaseTool
from ..config import Config

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

# MARK: - Sync Tool
class SyncTool(BaseTool):
    """
    Tool to watch for changes in *static* files in the project's *output* directory and writes them back to the *source* directory.
    """
    # Constants
    TOOL_NAME = "sync"
    TOOL_HELP = "Watch for changes in *static* files in the project's *output* directory and writes them back to the *source* directory."

    # Initializer
    def __init__(self, watchDir: Path, resultDir: Path, bufferDelay: float = 1.0):
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

        self._bufferDelay: float = bufferDelay # seconds
        self._changeHandler: Optional[_SFSyncWatcher] = None
        self._changeObserver = None

    # CLI Functions
    @staticmethod
    def setupParser(parser: argparse.ArgumentParser, config: Optional[Config]):
        """
        Sets up the given `parser` with arguments for this tool.

        parser: The parser to apply the arguments to.
        config: The config manager to use for the tool or `None` if not present.
        """
        # Optional arguments
        parser.add_argument(
            "-d", "--delay",
            type=float,
            default=1.0,
            help="The delay in seconds to buffer events to avoid duplicate processing and repeated events. (default: %(default)s)"
        )

    @classmethod
    def fromArgs(cls, args: argparse.Namespace, config: Optional[Config]) -> "BaseTool":
        """
        Creates an instance of this tool from the given `args`.

        args: The parser arguments to create the tool from.
        config: The config manager to use for the tool or `None` if not present.

        Returns an instance of this tool.
        """
        return cls(
            watchDir=Path(config.get("build", "outputDirectory")),
            resultDir=Path(config.get("build", "sourceDirectory")),
            bufferDelay=args.delay
        )

    def _run(self, args: argparse.Namespace, config: Optional[Config]):
        """
        Runs the tool as configured by the CLI.

        args: The parser arguments to create the tool from.
        config: The config manager to use for the tool or `None` if not present.
        """
        try:
            self.watch()
        except FileNotFoundError as e:
            print("Error: The static site has not been built yet. Please run the `build` tool first.")

    # Functions
    def watch(self):
        """
        Starts watching for changes in static files in the watch directory and writes them back to the result directory.
        """
        # Check the directories exist
        if (not self.watchDir.exists()) or (not self.watchDir.is_dir()):
            raise FileNotFoundError(f"Watch directory does not exist or is not a directory: {self.watchDir}")

        if (not self.resultDir.exists()) or (not self.resultDir.is_dir()):
            raise FileNotFoundError(f"Result directory does not exist or is not a directory: {self.resultDir}")

        # Report
        print("Waiting for static file changes...")
        print("Press CTRL+C to stop.\n")

        # Create the change handler
        self._changeHandler = _SFSyncWatcher(
            watchDir=self.watchDir,
            resultDir=self.resultDir,
            bufferDelay=self._bufferDelay
        )

        # Create the observer
        self._changeObserver = Observer()
        self._changeObserver.schedule(
            self._changeHandler,
            str(self.watchDir),
            recursive=True,
            event_filter=[FileModifiedEvent]
        )

        # Start observing
        self._changeObserver.start()

        # Enter listening loop
        try:
            while True:
                time.sleep(self._bufferDelay)
        except KeyboardInterrupt:
            # Exit on CTRL+C
            pass
        finally:
            # Clean up
            self._changeObserver.stop()
            self._changeObserver.join()

        # Report
        print("\nStopped watching for static file changes.")

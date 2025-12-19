"""
Attributions Item Model

Data model representing a Attributions item.
"""
# MARK: Imports
from dataclasses import dataclass
from pathlib import Path

# MARK: Classes
@dataclass
class AttrItem:
    """
    Data model representing an attributions item.
    """
    # Properties
    category: str
    title: str
    link: str
    filePath: Path

    # Functions
    def toDict(self) -> dict[str, str]:
        """
        Converts the AttrItem to a dictionary.

        Returns:
            A dictionary representation of the AttrItem.
        """
        return {
            "category": self.category,
            "title": self.title,
            "link": self.link,
            "filePath": str(self.filePath)
        }

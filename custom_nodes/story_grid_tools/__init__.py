from .story_grid import StoryGridAPISize, StoryGridModelSwitch, StoryGridReference, StoryGridReferenceBatch, StoryGridSliceSave
from .resolution import StoryGridResolution
from . import ui

WEB_DIRECTORY = "./web"

NODE_CLASS_MAPPINGS = {
    "StoryGridReference": StoryGridReference,
    "StoryGridReferenceBatch": StoryGridReferenceBatch,
    "StoryGridAPISize": StoryGridAPISize,
    "StoryGridResolution": StoryGridResolution,
    "StoryGridModelSwitch": StoryGridModelSwitch,
    "StoryGridSliceSave": StoryGridSliceSave,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "StoryGridReference": "Story Grid Reference",
    "StoryGridReferenceBatch": "Story Grid Reference Batch",
    "StoryGridAPISize": "Story Grid API Size",
    "StoryGridResolution": "Story Grid Model + Resolution",
    "StoryGridModelSwitch": "Story Grid Model Switch",
    "StoryGridSliceSave": "Story Grid Slice + Save",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

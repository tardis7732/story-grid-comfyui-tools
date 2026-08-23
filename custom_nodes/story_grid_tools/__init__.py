from .story_grid import StoryGridModelSwitch, StoryGridReference, StoryGridReferenceBatch, StoryGridSliceSave

NODE_CLASS_MAPPINGS = {
    "StoryGridReference": StoryGridReference,
    "StoryGridReferenceBatch": StoryGridReferenceBatch,
    "StoryGridModelSwitch": StoryGridModelSwitch,
    "StoryGridSliceSave": StoryGridSliceSave,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "StoryGridReference": "Story Grid Reference",
    "StoryGridReferenceBatch": "Story Grid Reference Batch",
    "StoryGridModelSwitch": "Story Grid Model Switch",
    "StoryGridSliceSave": "Story Grid Slice + Save",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]

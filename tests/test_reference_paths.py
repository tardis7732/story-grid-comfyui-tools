import importlib
import os
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import torch
from aiohttp import web
from PIL import Image


NODE_DIR = Path(__file__).resolve().parents[1] / "custom_nodes" / "story_grid_tools"
package = types.ModuleType("_story_grid_reference_tests")
package.__path__ = [str(NODE_DIR)]
folder_paths = types.SimpleNamespace(get_input_directory=lambda: "")
server = types.SimpleNamespace(PromptServer=types.SimpleNamespace(instance=types.SimpleNamespace(routes=web.RouteTableDef())))
with patch.dict(sys.modules, {package.__name__: package, "folder_paths": folder_paths, "server": server}):
    story_grid = importlib.import_module(f"{package.__name__}.story_grid")
    ui = importlib.import_module(f"{package.__name__}.ui")


class ReferencePathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.input_dir = self.root / "input"
        self.input_dir.mkdir()
        self.work_dir = self.root / "different_working_directory"
        self.work_dir.mkdir()
        original_cwd = Path.cwd()
        os.chdir(self.work_dir)
        self.addCleanup(os.chdir, original_cwd)
        folder_paths.get_input_directory = lambda: str(self.input_dir)

    def create_image(self, path, color="red", size=(24, 40)):
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", size, color).save(path)
        return path

    def load_batch(self, path):
        return story_grid.StoryGridReferenceBatch().build_batch(
            torch.ones((1, 32, 32, 3)), path, 32, 32, include_grid_reference=False
        )[0]

    def test_relative_input_file_is_independent_of_working_directory(self):
        source = self.create_image(self.input_dir / "story_grid_examples" / "runner.png")
        relative = "story_grid_examples/runner.png"
        self.assertEqual(story_grid.resolve_reference_path(relative), source)
        preview = ui._reference_previews(relative)
        self.assertEqual(preview["errors"], [])
        self.assertEqual(preview["images"][0]["index"], 2)
        self.assertEqual((preview["images"][0]["width"], preview["images"][0]["height"]), (24, 40))
        self.assertEqual(self.load_batch(relative)[0, 16, 16].tolist(), [1.0, 0.0, 0.0])

    def test_input_file_takes_priority_over_existing_cwd_file(self):
        relative = "story_grid_examples/runner.png"
        source = self.create_image(self.input_dir / relative, "red", (24, 40))
        self.create_image(self.work_dir / relative, "blue", (40, 24))
        self.assertEqual(story_grid.resolve_reference_path(relative), source)
        preview = ui._reference_previews(relative)
        self.assertEqual(preview["images"][0]["width"], 24)
        self.assertEqual(self.load_batch(relative)[0, 16, 16].tolist(), [1.0, 0.0, 0.0])

    def test_absolute_path_keeps_existing_behavior(self):
        source = self.create_image(self.root / "external" / "runner.png", "blue")
        self.create_image(self.input_dir / "runner.png", "red")
        self.assertEqual(story_grid.resolve_reference_path(str(source)), source)
        self.assertEqual(ui._reference_previews(str(source))["errors"], [])
        self.assertEqual(self.load_batch(str(source))[0, 16, 16].tolist(), [0.0, 0.0, 1.0])

    def test_existing_cwd_relative_file_remains_supported(self):
        source = self.create_image(self.work_dir / "legacy" / "runner.png", "blue")
        relative = "legacy/runner.png"
        self.assertEqual(story_grid.resolve_reference_path(relative), source)
        self.assertEqual(ui._reference_previews(relative)["errors"], [])
        self.assertEqual(self.load_batch(relative)[0, 16, 16].tolist(), [0.0, 0.0, 1.0])

    def test_missing_relative_file_reports_the_input_location(self):
        relative = "story_grid_examples/missing.png"
        expected = self.input_dir / relative
        self.assertEqual(story_grid.resolve_reference_path(relative), expected)
        with self.assertRaisesRegex(FileNotFoundError, re.escape(str(expected))):
            self.load_batch(relative)
        preview = ui._reference_previews(relative)
        self.assertEqual(preview["images"], [])
        self.assertEqual(preview["errors"], [{"index": 2, "filename": "missing.png", "message": "Image file not found."}])

    def test_preview_and_batch_keep_multiple_reference_order(self):
        self.create_image(self.input_dir / "story_grid_examples/pursuer.png", "red", (24, 40))
        self.create_image(self.input_dir / "story_grid_examples/runner.png", "blue", (40, 24))
        paths = "story_grid_examples/pursuer.png\nstory_grid_examples/runner.png"
        preview = ui._reference_previews(paths)
        self.assertEqual([item["filename"] for item in preview["images"]], ["pursuer.png", "runner.png"])
        self.assertEqual([item["index"] for item in preview["images"]], [2, 3])
        batch = self.load_batch(paths)
        self.assertEqual(batch.shape, (2, 32, 32, 3))
        self.assertEqual(batch[:, 16, 16].tolist(), [[1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])


if __name__ == "__main__":
    unittest.main()

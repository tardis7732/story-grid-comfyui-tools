import json
import re
import time
from math import gcd, isqrt
from pathlib import Path

import folder_paths
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageOps


DEFAULT_SCENARIO = (
    "A calm morning city street with a small delivery robot.\n"
    "The robot finds a glowing blue package.\n"
    "Rain starts and neon signs reflect on the pavement.\n"
    "A cyclist points toward a narrow alley.\n"
    "The robot enters the alley and sees a hidden door.\n"
    "Inside, old monitors show a map of the city.\n"
    "A friendly engineer repairs the robot's wheel.\n"
    "The package opens into a tiny hologram.\n"
    "The hologram reveals a lost rooftop garden.\n"
    "The robot rides an elevator through glass towers.\n"
    "It reaches the garden as sunlight breaks through clouds.\n"
    "The final panel shows the city glowing warmly."
)


def _safe_prefix(value):
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", (value or "").strip())
    return cleaned.strip("._") or "story_grid"


def _clean_prompt_line(line):
    line = line.strip()
    line = re.sub(r"^\s*(?:cell|panel|scene)?\s*[\[#(]?\s*\d+\s*[\])\].:-]\s*", "", line, flags=re.I)
    line = re.sub(r"^\s*r\d+\s*c\d+\s*[:.-]\s*", "", line, flags=re.I)
    return line.strip()


def _cell_prompts(scenario, rows, columns):
    count = max(1, int(rows) * int(columns))
    normalized = (scenario or "").replace("\r\n", "\n").replace("\r", "\n").strip()

    if "\n---\n" in normalized:
        parts = [part.strip() for part in normalized.split("\n---\n")]
    else:
        parts = [_clean_prompt_line(line) for line in normalized.split("\n") if line.strip()]

    parts = [part for part in parts if part]
    if not parts:
        parts = ["A clean cinematic storyboard panel."]

    if len(parts) == 1 and count > 1:
        base = parts[0]
        parts = [f"{base} Panel {index + 1} of {count}." for index in range(count)]

    while len(parts) < count:
        parts.append(f"{parts[-1]} Continuation panel {len(parts) + 1}.")

    return parts[:count]


def _pil_to_tensor(image):
    arr = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    return torch.from_numpy(arr)[None, ...]


def _pil_batch_to_tensor(images):
    tensors = [_pil_to_tensor(image) for image in images]
    if not tensors:
        return torch.zeros((1, 1, 1, 3), dtype=torch.float32)
    return torch.cat(tensors, dim=0)


def _tensor_to_pil_list(images):
    arr = images.detach().cpu().numpy()
    if arr.ndim == 3:
        arr = arr[None, ...]
    arr = np.clip(arr * 255.0, 0, 255).astype(np.uint8)
    return [Image.fromarray(frame).convert("RGB") for frame in arr]


def _draw_grid_reference(width, height, rows, columns, line_width, show_cell_numbers):
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    if line_width > 0:
        for col in range(1, columns):
            x = round(width * col / columns)
            draw.line([(x, 0), (x, height)], fill="black", width=line_width)
        for row in range(1, rows):
            y = round(height * row / rows)
            draw.line([(0, y), (width, y)], fill="black", width=line_width)

    if show_cell_numbers:
        for row in range(rows):
            for col in range(columns):
                index = row * columns + col + 1
                x0 = round(width * col / columns)
                y0 = round(height * row / rows)
                draw.rectangle([x0 + 12, y0 + 12, x0 + 72, y0 + 46], fill="white", outline="black")
                draw.text((x0 + 24, y0 + 20), str(index), fill="black")

    return image


def _parse_reference_paths(value):
    normalized = (value or "").replace("\r\n", "\n").replace("\r", "\n")
    parts = re.split(r"[\n;]+", normalized)
    paths = []
    for part in parts:
        cleaned = part.strip().strip("\"'")
        if cleaned:
            paths.append(cleaned)
    return paths


def resolve_reference_path(path_text):
    path = Path(path_text).expanduser()
    if path.is_absolute():
        return path
    input_path = Path(folder_paths.get_input_directory()) / path
    if input_path.is_file() or not path.is_file():
        return input_path
    return path.resolve()


def _contain_on_canvas(image, width, height):
    image = image.convert("RGB")
    canvas = Image.new("RGB", (width, height), "white")
    fitted = ImageOps.contain(image, (width, height), method=Image.Resampling.LANCZOS)
    x = (width - fitted.width) // 2
    y = (height - fitted.height) // 2
    canvas.paste(fitted, (x, y))
    return canvas


def _build_credit_prompt(scenario, rows, columns, width, height, prompts, show_cell_numbers=False):
    board_divisor = gcd(width, height)
    cell_width = width * rows
    cell_height = height * columns
    cell_divisor = gcd(cell_width, cell_height)
    text_policy = (
        "Include only small shot numbers matching the reference grid. "
        "Do not add captions, speech bubbles, other labels, logos, watermarks, or extra text."
        if show_cell_numbers
        else "Do not add captions, speech bubbles, labels, panel numbers, watermarks, or extra text."
    )
    lines = [
        f"Use the first attached reference image as an exact {rows} row by {columns} column storyboard grid.",
        f"Generate one combined {width}x{height} image sheet with a {width // board_divisor}:{height // board_divisor} aspect ratio, not separate files.",
        f"Each grid cell has a {cell_width // cell_divisor}:{cell_height // cell_divisor} aspect ratio before border trimming.",
        "Every grid cell must contain one distinct illustration matching its assigned prompt.",
        "Keep the panel borders aligned to the reference grid so the result can be sliced cleanly.",
        text_policy,
        "Keep visual style consistent across all cells.",
        "Use any additional attached reference images for character, prop, and location identity.",
        "",
        "Overall scenario:",
        (scenario or "").strip(),
        "",
        "Cell prompts in reading order:",
    ]

    for index, prompt in enumerate(prompts, start=1):
        row = (index - 1) // columns + 1
        col = (index - 1) % columns + 1
        lines.append(f"{index}. row {row}, column {col}: {prompt}")

    return "\n".join(lines).strip()


def _fit_to_target(image, width, height):
    if image.size == (width, height):
        return image.convert("RGB")
    return ImageOps.fit(image.convert("RGB"), (width, height), method=Image.Resampling.LANCZOS)


def _crop_cells(image, rows, columns, trim):
    width, height = image.size
    cells = []
    boxes = []

    for row in range(rows):
        for col in range(columns):
            x0 = round(width * col / columns)
            x1 = round(width * (col + 1) / columns)
            y0 = round(height * row / rows)
            y1 = round(height * (row + 1) / rows)
            left = min(x1 - 1, x0 + trim)
            right = max(left + 1, x1 - trim)
            top = min(y1 - 1, y0 + trim)
            bottom = max(top + 1, y1 - trim)
            box = (left, top, right, bottom)
            boxes.append(box)
            cells.append(image.crop(box).convert("RGB"))

    if cells:
        min_width = min(cell.width for cell in cells)
        min_height = min(cell.height for cell in cells)
        cells = [
            cell if cell.size == (min_width, min_height) else ImageOps.fit(cell, (min_width, min_height))
            for cell in cells
        ]

    return cells, boxes


class StoryGridReference:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "scenario": ("STRING", {"default": DEFAULT_SCENARIO, "multiline": True}),
                "rows": ("INT", {"default": 3, "min": 1, "max": 12, "step": 1}),
                "columns": ("INT", {"default": 4, "min": 1, "max": 12, "step": 1}),
                "width": ("INT", {"default": 1920, "min": 256, "max": 4096, "step": 1}),
                "height": ("INT", {"default": 1080, "min": 256, "max": 4096, "step": 1}),
                "grid_line_width": ("INT", {"default": 4, "min": 0, "max": 64, "step": 1}),
                "show_cell_numbers": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "INT", "INT", "INT", "INT")
    RETURN_NAMES = ("reference_grid", "credit_prompt", "rows", "columns", "width", "height")
    FUNCTION = "build"
    CATEGORY = "Storyboard/Grid"

    def build(self, scenario, rows, columns, width, height, grid_line_width, show_cell_numbers):
        rows = int(rows)
        columns = int(columns)
        width = int(width)
        height = int(height)
        grid_line_width = int(grid_line_width)
        prompts = _cell_prompts(scenario, rows, columns)
        reference = _draw_grid_reference(width, height, rows, columns, grid_line_width, bool(show_cell_numbers))
        credit_prompt = _build_credit_prompt(
            scenario, rows, columns, width, height, prompts, show_cell_numbers=bool(show_cell_numbers)
        )
        return (_pil_to_tensor(reference), credit_prompt, rows, columns, width, height)


class StoryGridReferenceBatch:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "reference_grid": ("IMAGE",),
                "reference_image_paths": ("STRING", {"default": "", "multiline": True}),
                "target_width": ("INT", {"default": 1920, "min": 256, "max": 4096, "step": 16}),
                "target_height": ("INT", {"default": 1080, "min": 256, "max": 4096, "step": 16}),
            },
            "optional": {
                "include_grid_reference": ("BOOLEAN", {"default": True}),
                "asset_descriptions": ("STRING", {"forceInput": True, "default": ""}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("reference_images", "reference_notes")
    FUNCTION = "build_batch"
    CATEGORY = "Storyboard/Grid"

    def build_batch(
        self,
        reference_grid,
        reference_image_paths,
        target_width,
        target_height,
        include_grid_reference=True,
        asset_descriptions="",
    ):
        target_width = int(target_width)
        target_height = int(target_height)
        include_grid_reference = bool(include_grid_reference)

        images = []
        notes = []

        if include_grid_reference:
            grid_image = _tensor_to_pil_list(reference_grid)[0]
            images.append(_fit_to_target(grid_image, target_width, target_height))
            notes.append("Image 1: grid layout reference")

        missing = []
        for path_text in _parse_reference_paths(reference_image_paths):
            path = resolve_reference_path(path_text)
            if not path.exists() or not path.is_file():
                missing.append(str(path))
                continue
            with Image.open(path) as image:
                images.append(_contain_on_canvas(image, target_width, target_height))
            notes.append(f"Image {len(notes) + 1}: asset reference")

        if missing:
            raise FileNotFoundError("Missing reference image path(s): " + "; ".join(missing))

        if not images:
            raise ValueError("At least one reference image is required.")

        note_text = "Attached reference image order:\n" + "\n".join(notes)
        if asset_descriptions.strip():
            note_text += "\n\nAsset roles and appearance:\n" + asset_descriptions.strip()
        return (_pil_batch_to_tensor(images), note_text)


class StoryGridAPISize:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "width": ("INT", {"forceInput": True}),
                "height": ("INT", {"forceInput": True}),
            }
        }

    RETURN_TYPES = ("COMBO", "INT", "INT")
    RETURN_NAMES = ("gemini_aspect_ratio", "gpt_width", "gpt_height")
    FUNCTION = "resolve"
    CATEGORY = "Storyboard/Grid"

    def resolve(self, width, height):
        width = int(width)
        height = int(height)
        if width <= 0 or height <= 0:
            raise ValueError("Board width and height must be positive.")
        if max(width, height) > 3 * min(width, height):
            raise ValueError("The board aspect ratio exceeds GPT Image 2's 3:1 limit. Adjust the grid or board size.")

        divisor = gcd(width, height)
        ratio_width = width // divisor
        ratio_height = height // divisor
        ratio = f"{ratio_width}:{ratio_height}"
        gemini_ratio = {
            "1:1": "1:1", "2:3": "2:3", "3:2": "3:2", "3:4": "3:4", "4:3": "4:3",
            "4:5": "4:5", "5:4": "5:4", "9:16": "9:16", "16:9": "16:9", "7:3": "21:9",
        }.get(ratio, "auto")

        unit_width = ratio_width * 16
        unit_height = ratio_height * 16
        minimum_scale = max((1024 + unit_width - 1) // unit_width, (1024 + unit_height - 1) // unit_height)
        maximum_scale = min(3840 // unit_width, 3840 // unit_height, isqrt(8_294_400 // (unit_width * unit_height)))
        if minimum_scale <= maximum_scale:
            scale = min(maximum_scale, max(minimum_scale, round(width / unit_width)))
            return (gemini_ratio, unit_width * scale, unit_height * scale)

        candidates = []
        for gpt_width in range(1024, 3841, 16):
            gpt_height = min(3840, max(1024, round(gpt_width * height / width / 16) * 16))
            if gpt_width * gpt_height > 8_294_400 or max(gpt_width, gpt_height) > 3 * min(gpt_width, gpt_height):
                continue
            ratio_error = abs(gpt_width * height / (gpt_height * width) - 1)
            if ratio_error <= 0.005:
                size_error = ((gpt_width - width) / width) ** 2 + ((gpt_height - height) / height) ** 2
                candidates.append((size_error, ratio_error, gpt_width, gpt_height))
        if not candidates:
            raise ValueError("No supported GPT Image 2 size matches this board. Choose a different board aspect ratio.")
        _, _, gpt_width, gpt_height = min(candidates)
        return (gemini_ratio, gpt_width, gpt_height)


class StoryGridModelSwitch:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_choice": ("COMBO", {"options": ["Gemini Pro", "GPT Image 2"], "default": "Gemini Pro"}),
            },
            "optional": {
                "gemini_pro_image": ("IMAGE", {"lazy": True}),
                "gpt_image_2_image": ("IMAGE", {"lazy": True}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("selected_image", "selected_model")
    FUNCTION = "select"
    CATEGORY = "Storyboard/Grid"

    def check_lazy_status(self, model_choice, gemini_pro_image=None, gpt_image_2_image=None):
        if model_choice == "GPT Image 2":
            return [] if gpt_image_2_image is not None else ["gpt_image_2_image"]
        return [] if gemini_pro_image is not None else ["gemini_pro_image"]

    def select(self, model_choice, gemini_pro_image=None, gpt_image_2_image=None):
        if model_choice == "GPT Image 2":
            if gpt_image_2_image is None:
                raise ValueError("GPT Image 2 output is not available.")
            return (gpt_image_2_image, model_choice)

        if gemini_pro_image is None:
            raise ValueError("Gemini Pro output is not available.")
        return (gemini_pro_image, model_choice)


class StoryGridSliceSave:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "generated_grid": ("IMAGE",),
                "rows": ("INT", {"default": 3, "min": 1, "max": 12, "step": 1}),
                "columns": ("INT", {"default": 4, "min": 1, "max": 12, "step": 1}),
                "target_width": ("INT", {"default": 1920, "min": 256, "max": 4096, "step": 16}),
                "target_height": ("INT", {"default": 1080, "min": 256, "max": 4096, "step": 16}),
                "output_prefix": ("STRING", {"default": "story_grid"}),
            },
            "optional": {
                "credit_prompt": ("STRING", {"forceInput": True}),
                "crop_trim_px": ("INT", {"default": 4, "min": 0, "max": 128, "step": 1}),
                "save_full_grid": ("BOOLEAN", {"default": True}),
                "save_cells": ("BOOLEAN", {"default": True}),
                "preserve_cell_aspect": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("cell_images", "manifest_json")
    FUNCTION = "slice_and_save"
    CATEGORY = "Storyboard/Grid"
    OUTPUT_NODE = True

    def slice_and_save(
        self,
        generated_grid,
        rows,
        columns,
        target_width,
        target_height,
        output_prefix,
        credit_prompt="",
        crop_trim_px=4,
        save_full_grid=True,
        save_cells=True,
        preserve_cell_aspect=False,
    ):
        rows = int(rows)
        columns = int(columns)
        target_width = int(target_width)
        target_height = int(target_height)
        crop_trim_px = int(crop_trim_px)
        save_full_grid = bool(save_full_grid)
        save_cells = bool(save_cells)
        preserve_cell_aspect = bool(preserve_cell_aspect)

        safe_prefix = _safe_prefix(output_prefix)
        run_id = time.strftime("%Y%m%d-%H%M%S")
        subfolder = f"{safe_prefix}/{run_id}"
        output_dir = Path(folder_paths.get_output_directory()) / subfolder
        output_dir.mkdir(parents=True, exist_ok=True)

        all_cells = []
        ui_images = []
        manifest = {
            "rows": rows,
            "columns": columns,
            "target_width": target_width,
            "target_height": target_height,
            "crop_trim_px": crop_trim_px,
            "preserve_cell_aspect": preserve_cell_aspect,
            "credit_prompt": credit_prompt or "",
            "grids": [],
        }

        source_images = _tensor_to_pil_list(generated_grid)
        for grid_index, source in enumerate(source_images, start=1):
            generated = _fit_to_target(source, target_width, target_height)
            grid_tag = f"grid_{grid_index:02d}" if len(source_images) > 1 else "grid"
            grid_record = {
                "source_size": list(source.size),
                "saved_size": [target_width, target_height],
                "files": {},
                "cells": [],
            }

            if save_full_grid:
                full_name = "generated_grid.png" if len(source_images) == 1 else f"{grid_tag}_generated_grid.png"
                generated.save(output_dir / full_name)
                grid_record["files"]["generated_grid"] = str(output_dir / full_name)
                ui_images.append({"filename": full_name, "subfolder": subfolder, "type": "output"})

            cells, boxes = _crop_cells(generated, rows, columns, crop_trim_px)
            if preserve_cell_aspect:
                cell_width = max(1, round(target_width / columns))
                cell_height = max(1, round(target_height / rows))
                cells = [_fit_to_target(cell, cell_width, cell_height) for cell in cells]
            all_cells.extend(cells)

            if save_cells:
                cell_subdir = output_dir / "cells" / grid_tag
                cell_subdir.mkdir(parents=True, exist_ok=True)
                cell_subfolder = f"{subfolder}/cells/{grid_tag}"
                for index, (cell, box) in enumerate(zip(cells, boxes), start=1):
                    row = (index - 1) // columns + 1
                    col = (index - 1) % columns + 1
                    name = f"cell_{index:02d}_r{row}_c{col}.png"
                    cell.save(cell_subdir / name)
                    grid_record["cells"].append(
                        {
                            "index": index,
                            "row": row,
                            "column": col,
                            "crop_box": list(box),
                            "saved_size": list(cell.size),
                            "file": str(cell_subdir / name),
                        }
                    )
                    ui_images.append({"filename": name, "subfolder": cell_subfolder, "type": "output"})

            manifest["grids"].append(grid_record)

        manifest_path = output_dir / "manifest.json"
        manifest["files"] = {"manifest": str(manifest_path)}
        manifest_json = json.dumps(manifest, ensure_ascii=False, indent=2)
        manifest_path.write_text(manifest_json, encoding="utf-8")

        return {
            "ui": {"images": ui_images, "text": [manifest_json]},
            "result": (_pil_batch_to_tensor(all_cells), manifest_json),
        }

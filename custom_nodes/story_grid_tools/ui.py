import asyncio
import base64
import io
import json
from pathlib import Path

from aiohttp import web
from PIL import Image, ImageOps, UnidentifiedImageError
from server import PromptServer

from .story_grid import _parse_reference_paths, resolve_reference_path


def _reference_previews(paths, include_grid_reference=True):
    images = []
    errors = []
    start = 2 if include_grid_reference else 1
    for index, path_text in enumerate(_parse_reference_paths(paths), start=start):
        entry = {"index": index, "filename": Path(path_text).name}
        if path_text.replace("\\", "/").startswith("//") or "://" in path_text:
            errors.append({**entry, "message": "Use a local image file path."})
            continue
        path = resolve_reference_path(path_text)
        try:
            if not path.is_file():
                errors.append({**entry, "message": "Image file not found."})
                continue
            with Image.open(path) as source:
                thumbnail = ImageOps.exif_transpose(source)
                width, height = thumbnail.size
                thumbnail.thumbnail((512, 384), Image.Resampling.LANCZOS)
                thumbnail = thumbnail.convert("RGBA")
                preview = Image.new("RGB", thumbnail.size, "white")
                preview.paste(thumbnail, mask=thumbnail.getchannel("A"))
                buffer = io.BytesIO()
                preview.save(buffer, format="JPEG", quality=86)
            images.append({
                **entry,
                "width": width,
                "height": height,
                "data_url": "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii"),
            })
        except PermissionError:
            errors.append({**entry, "message": "Image file cannot be read."})
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError):
            errors.append({**entry, "message": "Cannot preview this image. Check the file and format."})
    return {"images": images, "errors": errors}


@PromptServer.instance.routes.post("/story_grid/reference-preview")
async def reference_preview(request):
    try:
        body = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return web.json_response({"error": "Expected a JSON object."}, status=400)
    if not isinstance(body, dict) or not isinstance(body.get("paths"), str):
        return web.json_response({"error": "paths must be a string."}, status=400)
    include_grid_reference = body.get("include_grid_reference", True)
    if not isinstance(include_grid_reference, bool):
        return web.json_response({"error": "include_grid_reference must be a boolean."}, status=400)
    result = await asyncio.to_thread(_reference_previews, body["paths"], include_grid_reference)
    return web.json_response(result)

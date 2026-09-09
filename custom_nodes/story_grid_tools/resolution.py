import re
from math import ceil, floor, gcd, isqrt, lcm, log, sqrt


# Gemini Pro's published 1K sizes; 2K and 4K double and quadruple both axes.
# https://ai.google.dev/gemini-api/docs/image-generation#aspect_ratios_and_image_size
GEMINI_SIZES = {
    "1:1": (1024, 1024),
    "2:3": (848, 1264),
    "3:2": (1264, 848),
    "3:4": (896, 1200),
    "4:3": (1200, 896),
    "4:5": (928, 1152),
    "5:4": (1152, 928),
    "9:16": (768, 1376),
    "16:9": (1376, 768),
    "21:9": (1584, 672),
}
RESOLUTIONS = {"1K": 1024, "2K": 2048, "4K": 3840}
MODEL_CHOICES = ["Gemini Pro", "GPT Image 2"]
GPT_MIN_PIXELS = 655_360
GPT_MAX_PIXELS = 8_294_400
GPT_MAX_EDGE = 3840


def _gpt_size(p, q, rows, columns, resolution):
    if max(p, q) > min(p, q) * 3:
        raise ValueError("GPT Image 2는 전체 보드 비율이 3:1 이내여야 합니다. 행·열 또는 보드 비율을 조절하세요.")

    long_ratio = max(p, q) / min(p, q)
    target_edge = min(
        max(RESOLUTIONS[resolution], sqrt(GPT_MIN_PIXELS * long_ratio)),
        GPT_MAX_EDGE,
        sqrt(GPT_MAX_PIXELS * long_ratio),
    )
    step = lcm(16 // gcd(p, 16), 16 // gcd(q, 16), columns // gcd(p, columns), rows // gcd(q, rows))
    max_scale = min(GPT_MAX_EDGE // max(p, q), isqrt(GPT_MAX_PIXELS // (p * q)))
    candidates = [
        (p * k, q * k)
        for k in range(step, max_scale + 1, step)
        if p * q * k * k >= GPT_MIN_PIXELS
    ]
    if candidates:
        exact = min(candidates, key=lambda size: (abs(max(size) - target_edge), -size[0] * size[1]))
        if abs(max(exact) / target_edge - 1) <= 0.1:
            return exact

    # An exact ratio can have a coarse 16px lattice that collapses two size tiers.
    ratio = p / q
    candidates = []
    for height in range(16, GPT_MAX_EDGE + 1, 16):
        ideal = height * ratio / 16
        for width in {floor(ideal) * 16, ceil(ideal) * 16}:
            if width < 16 or width > GPT_MAX_EDGE:
                continue
            if max(width, height) > 3 * min(width, height):
                continue
            if not GPT_MIN_PIXELS <= width * height <= GPT_MAX_PIXELS:
                continue
            error = abs(width / height / ratio - 1)
            if error <= 0.005:
                candidates.append((width, height, error))
    if not candidates:
        raise ValueError("이 보드 비율에 맞는 GPT Image 2 해상도가 없습니다. 보드 비율 프리셋을 선택하세요.")
    width, height, _ = min(candidates, key=lambda size: (abs(max(size[:2]) - target_edge), size[2]))
    return width, height


def _save_size(p, q, rows, columns, generated_width, generated_height):
    area = generated_width * generated_height
    step = lcm(columns // gcd(p, columns), rows // gcd(q, rows))
    scale = max(1, round(sqrt(area / (p * q)) / step)) * step
    width, height = p * scale, q * scale
    if 0.8 * area <= width * height <= 1.25 * area:
        return width, height

    # Keep unusual ratios near native size instead of making a huge exact-ratio upsample.
    ratio = p / q
    ideal_height = sqrt(area / ratio) / rows
    candidates = []
    for cell_height in range(max(1, floor(ideal_height * 0.8)), ceil(ideal_height * 1.2) + 1):
        ideal_width = cell_height * rows * ratio / columns
        for cell_width in {max(1, floor(ideal_width)), max(1, ceil(ideal_width))}:
            width, height = cell_width * columns, cell_height * rows
            error = abs(width / height / ratio - 1)
            if error <= 0.005 and 0.8 * area <= width * height <= 1.25 * area:
                candidates.append((width, height, error))
    if not candidates:
        raise ValueError("이 행·열 조합에서 컷 크기를 맞출 수 없습니다. 보드 비율 프리셋을 선택하세요.")
    width, height, _ = min(candidates, key=lambda size: (abs(size[0] * size[1] / area - 1), size[2]))
    return width, height


def generation_sizes(width, height, rows, columns, model_choice, resolution):
    if model_choice not in MODEL_CHOICES:
        raise ValueError("모델은 Gemini Pro 또는 GPT Image 2를 선택하세요.")
    if resolution not in RESOLUTIONS:
        raise ValueError("생성 해상도는 1K, 2K, 4K 중에서 선택하세요.")
    for name, value in (("width", width), ("height", height), ("rows", rows), ("columns", columns)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} 값은 양의 정수여야 합니다.")
    if rows > 12 or columns > 12 or max(width, height) > 16384:
        raise ValueError("행·열은 1~12, 보드 크기는 16384px 이내로 설정하세요.")

    divisor = gcd(width, height)
    p, q = width // divisor, height // divisor
    board_ratio = f"{p}:{q}"
    ratio = p / q
    gemini_ratio = min(
        GEMINI_SIZES,
        key=lambda value: abs(log((int(value.split(":")[0]) / int(value.split(":")[1])) / ratio)),
    )
    factor = {"1K": 1, "2K": 2, "4K": 4}[resolution]
    gemini_width, gemini_height = (value * factor for value in GEMINI_SIZES[gemini_ratio])

    try:
        gpt_width, gpt_height = _gpt_size(p, q, rows, columns, resolution)
    except ValueError:
        if model_choice == "GPT Image 2":
            raise
        gpt_width, gpt_height = None, None
    gpt_size = f"{gpt_width}x{gpt_height}" if gpt_width is not None else "auto"
    if model_choice == "Gemini Pro":
        generated_width, generated_height = gemini_width, gemini_height
    else:
        generated_width, generated_height = gpt_width, gpt_height
    save_width, save_height = _save_size(p, q, rows, columns, generated_width, generated_height)

    notes = []
    if model_choice == "Gemini Pro" and gemini_ratio != board_ratio:
        a, b = map(int, gemini_ratio.split(":"))
        if a * q != b * p:
            notes.append(f"Gemini는 {gemini_ratio}로 생성 후 {board_ratio} 보드에 맞춰 가장자리를 자릅니다.")
    if model_choice == "GPT Image 2" and max(gpt_width, gpt_height) != RESOLUTIONS[resolution]:
        if resolution == "4K":
            notes.append("GPT 4K는 최대 3840px·약 829만 픽셀 제한에 맞춘 가장 큰 크기를 사용합니다.")
        else:
            notes.append(f"GPT의 픽셀 제한과 컷 비율에 맞춰 {gpt_size}px로 생성합니다.")
    if (save_width, save_height) != (generated_width, generated_height):
        notes.append(f"모든 컷을 같은 크기로 나누도록 보드를 {save_width}×{save_height}px로 맞춰 저장합니다.")
    if save_width * q != save_height * p:
        notes.append("정수 픽셀로 컷을 나누기 위해 보드 비율을 0.5% 이내로 조정했습니다.")

    return {
        "model_choice": model_choice,
        "resolution": resolution,
        "board_ratio": board_ratio,
        "gemini_aspect_ratio": gemini_ratio,
        "gemini_resolution": resolution,
        "gemini_width": gemini_width,
        "gemini_height": gemini_height,
        "gpt_size": gpt_size,
        "gpt_width": gpt_width,
        "gpt_height": gpt_height,
        "generated_width": generated_width,
        "generated_height": generated_height,
        "save_width": save_width,
        "save_height": save_height,
        "cell_width": save_width // columns,
        "cell_height": save_height // rows,
        "notes": notes,
    }


class StoryGridResolution:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "width": ("INT", {"default": 1920, "min": 1, "max": 16384, "forceInput": True}),
                "height": ("INT", {"default": 1080, "min": 1, "max": 16384, "forceInput": True}),
                "rows": ("INT", {"default": 3, "min": 1, "max": 12, "forceInput": True}),
                "columns": ("INT", {"default": 4, "min": 1, "max": 12, "forceInput": True}),
                "model_choice": (MODEL_CHOICES, {"default": "GPT Image 2"}),
                "resolution": (list(RESOLUTIONS), {"default": "2K"}),
            },
            "optional": {
                "layout_prompt": ("STRING", {"default": "", "forceInput": True}),
            },
        }

    RETURN_TYPES = ("COMBO", "COMBO", "COMBO", "COMBO", "INT", "INT", "STRING")
    RETURN_NAMES = (
        "gemini_aspect_ratio", "gemini_resolution", "gpt_size", "model_choice",
        "save_width", "save_height", "credit_prompt",
    )
    FUNCTION = "resolve"
    CATEGORY = "Storyboard/Grid"

    def resolve(self, width, height, rows, columns, model_choice, resolution, layout_prompt=""):
        sizes = generation_sizes(width, height, rows, columns, model_choice, resolution)
        size_line = (
            f"Generate one combined storyboard image sheet at {resolution}, using the configured output size "
            f"{sizes['generated_width']}x{sizes['generated_height']}; keep the reference grid layout."
        )
        credit_prompt = re.sub(r"^Generate one combined .+ image sheet.+$", size_line, layout_prompt, count=1, flags=re.M)
        return (
            sizes["gemini_aspect_ratio"], sizes["gemini_resolution"], sizes["gpt_size"], model_choice,
            sizes["save_width"], sizes["save_height"], credit_prompt,
        )

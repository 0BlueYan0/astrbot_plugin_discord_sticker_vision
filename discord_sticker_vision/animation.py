from __future__ import annotations

import asyncio
import hashlib
import math
import urllib.request
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urlparse

from PIL import Image, ImageChops, ImageDraw, ImageOps, ImageStat

from .assets import DiscordVisualAsset


DEFAULT_FRAME_COUNT = 5
MAX_FRAME_SIZE = (160, 160)
PADDING = 8
LABEL_HEIGHT = 18
BACKGROUND = (255, 255, 255, 255)
LABEL_FILL = (32, 32, 32, 255)
SIMILARITY_THRESHOLD = 8.0


async def prepare_visual_assets(
    assets: list[DiscordVisualAsset],
    *,
    cache_dir: Path,
    frame_count: int = DEFAULT_FRAME_COUNT,
) -> list[DiscordVisualAsset]:
    prepared: list[DiscordVisualAsset] = []
    for asset in assets:
        if not asset.animated or not asset.animation_url:
            prepared.append(asset)
            continue

        contact_sheet = await _build_contact_sheet(
            asset.animation_url,
            cache_dir=cache_dir,
            frame_count=frame_count,
        )
        if contact_sheet is None:
            prepared.append(asset)
            continue

        prepared.append(
            replace(
                asset,
                url=str(contact_sheet[0]),
                frame_count=contact_sheet[1],
            )
        )
    return prepared


async def _build_contact_sheet(
    image_ref: str,
    *,
    cache_dir: Path,
    frame_count: int,
) -> tuple[Path, int] | None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{_stable_digest(image_ref)}-{frame_count}.png"
    frame_count_path = cache_path.with_suffix(".frames")
    if cache_path.exists():
        return cache_path, _read_cached_frame_count(frame_count_path, frame_count)

    try:
        image_bytes = await asyncio.to_thread(_read_image_bytes, image_ref)
        generated = await asyncio.to_thread(
            _render_contact_sheet,
            image_bytes,
            frame_count,
            cache_path,
        )
    except Exception:
        return None

    return generated


def _read_image_bytes(image_ref: str) -> bytes:
    if image_ref.startswith(("http://", "https://")):
        request = urllib.request.Request(
            image_ref,
            headers={"User-Agent": "astrbot-plugin-discord-sticker-vision/0.3"},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.read()

    if image_ref.startswith("file://"):
        parsed = urlparse(image_ref)
        return Path(unquote(parsed.path)).read_bytes()

    return Path(image_ref).read_bytes()


def _render_contact_sheet(
    image_bytes: bytes,
    frame_count: int,
    output_path: Path,
) -> tuple[Path, int] | None:
    with Image.open(BytesIO(image_bytes)) as image:
        total_frames = int(getattr(image, "n_frames", 1) or 1)
        if total_frames <= 1:
            return None

        frames = []
        for index in _sample_indices(total_frames, frame_count):
            image.seek(index)
            frame = image.convert("RGBA")
            frame = ImageOps.contain(frame, MAX_FRAME_SIZE, Image.Resampling.LANCZOS)
            frames.append((index + 1, frame.copy()))

    frames = _dedupe_frames(frames)
    if not frames:
        return None

    columns = min(3, len(frames))
    rows = math.ceil(len(frames) / columns)
    cell_width = max(frame.width for _, frame in frames) + PADDING * 2
    cell_height = max(frame.height for _, frame in frames) + PADDING * 2 + LABEL_HEIGHT
    sheet = Image.new("RGBA", (cell_width * columns, cell_height * rows), BACKGROUND)
    draw = ImageDraw.Draw(sheet)

    for frame_number, (source_frame, frame) in enumerate(frames):
        column = frame_number % columns
        row = frame_number // columns
        cell_x = column * cell_width
        cell_y = row * cell_height
        image_x = cell_x + (cell_width - frame.width) // 2
        image_y = cell_y + PADDING
        sheet.alpha_composite(frame, (image_x, image_y))
        draw.text(
            (cell_x + PADDING, cell_y + cell_height - LABEL_HEIGHT),
            f"frame {source_frame}",
            fill=LABEL_FILL,
        )

    sheet.convert("RGB").save(output_path, format="PNG")
    sampled_frame_count = len(frames)
    output_path.with_suffix(".frames").write_text(
        str(sampled_frame_count),
        encoding="utf-8",
    )
    return output_path, sampled_frame_count


def _sample_indices(total_frames: int, frame_count: int) -> list[int]:
    count = max(1, min(frame_count, total_frames))
    if count == 1:
        return [0]

    return sorted(
        {
            round(position * (total_frames - 1) / (count - 1))
            for position in range(count)
        }
    )


def _dedupe_frames(frames: list[tuple[int, Image.Image]]) -> list[tuple[int, Image.Image]]:
    if len(frames) <= 2:
        return frames

    deduped: list[tuple[int, Image.Image]] = [frames[0]]
    middle_frames = frames[1:-1]
    for frame in middle_frames:
        if any(_frames_are_similar(frame[1], kept_frame) for _, kept_frame in deduped):
            continue
        deduped.append(frame)

    deduped.append(frames[-1])
    return deduped


def _frames_are_similar(left: Image.Image, right: Image.Image) -> bool:
    left_sample = _comparison_sample(left)
    right_sample = _comparison_sample(right)
    diff = ImageChops.difference(left_sample, right_sample)
    mean = ImageStat.Stat(diff).mean
    return sum(mean) / len(mean) < SIMILARITY_THRESHOLD


def _comparison_sample(image: Image.Image) -> Image.Image:
    return ImageOps.contain(
        image.convert("RGB"),
        (32, 32),
        Image.Resampling.BILINEAR,
    )


def _read_cached_frame_count(frame_count_path: Path, fallback: int) -> int:
    try:
        return int(frame_count_path.read_text(encoding="utf-8").strip())
    except Exception:
        return fallback


def _stable_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]

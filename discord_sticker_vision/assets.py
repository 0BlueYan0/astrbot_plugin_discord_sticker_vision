from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


CUSTOM_EMOJI_RE = re.compile(
    r"<(?P<animated>a?):(?P<name>[A-Za-z0-9_.~-]{2,32}):(?P<id>\d{15,25})>"
)


@dataclass(frozen=True)
class DiscordVisualAsset:
    kind: str
    name: str
    url: str


def extract_visual_assets(message: Any) -> list[DiscordVisualAsset]:
    """Extract Discord custom emoji and sticker image URLs from a raw message."""
    assets: list[DiscordVisualAsset] = []
    seen: set[tuple[str, str]] = set()

    for asset in _extract_custom_emojis(getattr(message, "content", "") or ""):
        key = (asset.kind, asset.url)
        if key not in seen:
            seen.add(key)
            assets.append(asset)

    stickers = getattr(message, "stickers", None)
    if stickers is None:
        stickers = getattr(message, "sticker_items", None)

    for sticker in stickers or ():
        asset = _sticker_to_asset(sticker)
        if asset is None:
            continue
        key = (asset.kind, asset.url)
        if key not in seen:
            seen.add(key)
            assets.append(asset)

    return assets


def build_content_parts(
    assets: list[DiscordVisualAsset], *, max_assets: int = 8
) -> list[dict[str, object]]:
    """Build AstrBot-compatible content part dictionaries."""
    if max_assets <= 0:
        return []

    parts: list[dict[str, object]] = []
    for index, asset in enumerate(assets[:max_assets], start=1):
        label = _asset_label(asset)
        parts.append({"type": "text", "text": label})
        parts.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": asset.url,
                    "id": f"discord-{asset.kind}-{index}",
                },
            }
        )
    return parts


def build_asset_notice_text(
    assets: list[DiscordVisualAsset], *, max_assets: int = 8
) -> str:
    return "\n".join(_asset_label(asset) for asset in assets[:max_assets])


def _extract_custom_emojis(content: str) -> list[DiscordVisualAsset]:
    assets: list[DiscordVisualAsset] = []
    for match in CUSTOM_EMOJI_RE.finditer(content):
        emoji_id = match.group("id")
        extension = "gif" if match.group("animated") else "png"
        assets.append(
            DiscordVisualAsset(
                kind="emoji",
                name=match.group("name"),
                url=(
                    f"https://cdn.discordapp.com/emojis/{emoji_id}.{extension}"
                    "?size=128&quality=lossless"
                ),
            )
        )
    return assets


def _sticker_to_asset(sticker: Any) -> DiscordVisualAsset | None:
    sticker_id = getattr(sticker, "id", None)
    if sticker_id is None:
        return None

    url = str(getattr(sticker, "url", "") or "")
    if not _is_image_like_url(url):
        url = _fallback_sticker_url(sticker_id, getattr(sticker, "format", None))

    if not url:
        return None

    return DiscordVisualAsset(
        kind="sticker",
        name=str(getattr(sticker, "name", "") or f"sticker-{sticker_id}"),
        url=url,
    )


def _fallback_sticker_url(sticker_id: object, sticker_format: Any) -> str:
    extension = "gif" if _format_name(sticker_format) == "gif" else "png"
    return (
        f"https://cdn.discordapp.com/stickers/{sticker_id}.{extension}"
        "?size=320&quality=lossless"
    )


def _format_name(value: Any) -> str:
    name = getattr(value, "name", None)
    if name:
        return str(name).lower()
    text = str(value or "").lower()
    return text.rsplit(".", maxsplit=1)[-1]


def _is_image_like_url(url: str) -> bool:
    lowered = url.lower().split("?", maxsplit=1)[0]
    return lowered.startswith(("http://", "https://")) and not lowered.endswith(
        ".json"
    )


def _asset_label(asset: DiscordVisualAsset) -> str:
    safe_name = asset.name.replace("\n", " ").strip() or asset.kind
    return f"[Discord {asset.kind}: {safe_name}]"

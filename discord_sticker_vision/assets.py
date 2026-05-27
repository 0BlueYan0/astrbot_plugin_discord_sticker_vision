from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


CUSTOM_EMOJI_RE = re.compile(
    r"<(?P<animated>a?):(?P<name>[A-Za-z0-9_.~-]{2,32}):(?P<id>\d{15,25})>"
)
DISCORD_GIF_ASSET_RE = re.compile(
    r"^https://(?:cdn\.discordapp\.com|media\.discordapp\.net)/"
    r"(?P<route>emojis|stickers)/(?P<id>\d+)\.gif(?:\?.*)?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DiscordVisualAsset:
    kind: str
    name: str
    url: str
    animated: bool = False
    animation_url: str | None = None
    frame_count: int = 0


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
        animated = bool(match.group("animated"))
        assets.append(
            DiscordVisualAsset(
                kind="emoji",
                name=match.group("name"),
                url=(
                    f"https://cdn.discordapp.com/emojis/{emoji_id}.png"
                    "?size=128&quality=lossless"
                ),
                animated=animated,
                animation_url=(
                    f"https://cdn.discordapp.com/emojis/{emoji_id}.gif"
                    "?size=128&quality=lossless"
                    if animated
                    else None
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
        sticker_format = _format_name(getattr(sticker, "format", None))
        animated = sticker_format in {"gif", "apng"}
        url = _fallback_sticker_url(sticker_id)
        if sticker_format == "gif":
            animation_url = _fallback_sticker_url(sticker_id, extension="gif")
        elif sticker_format == "apng":
            animation_url = url
        else:
            animation_url = None
    else:
        animated = _is_discord_gif_asset_url(url) or _format_name(
            getattr(sticker, "format", None)
        ) == "apng"
        animation_url = url if animated else None
        url = _static_preview_url(url)

    if not url:
        return None

    return DiscordVisualAsset(
        kind="sticker",
        name=str(getattr(sticker, "name", "") or f"sticker-{sticker_id}"),
        url=url,
        animated=animated,
        animation_url=animation_url,
    )


def _fallback_sticker_url(sticker_id: object, *, extension: str = "png") -> str:
    return (
        f"https://cdn.discordapp.com/stickers/{sticker_id}.{extension}"
        "?size=320&quality=lossless"
    )


def _static_preview_url(url: str) -> str:
    match = DISCORD_GIF_ASSET_RE.match(url)
    if not match:
        return url

    route = match.group("route").lower()
    asset_id = match.group("id")
    if route == "emojis":
        return (
            f"https://cdn.discordapp.com/emojis/{asset_id}.png"
            "?size=128&quality=lossless"
        )
    return (
        f"https://cdn.discordapp.com/stickers/{asset_id}.png"
        "?size=320&quality=lossless"
    )


def _is_discord_gif_asset_url(url: str) -> bool:
    return bool(DISCORD_GIF_ASSET_RE.match(url))


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
    if asset.animated and asset.frame_count:
        return (
            f"[Discord animated {asset.kind}: {safe_name}; "
            f"sampled into {asset.frame_count} frames]"
        )
    if asset.animated:
        return f"[Discord animated {asset.kind}: {safe_name}]"
    return f"[Discord {asset.kind}: {safe_name}]"

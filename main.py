from __future__ import annotations

import sys

from astrbot.api import logger, star
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Image, Plain
from astrbot.api.provider import ProviderRequest
from astrbot.core.agent.message import ImageURLPart, TextPart

try:
    from .discord_sticker_vision.assets import (
        DiscordVisualAsset,
        build_asset_notice_text,
        build_content_parts,
        extract_visual_assets,
    )
except ImportError:
    from discord_sticker_vision.assets import (
        DiscordVisualAsset,
        build_asset_notice_text,
        build_content_parts,
        extract_visual_assets,
    )


VISUAL_ASSETS_EXTRA_KEY = "discord_sticker_vision_assets"
VISUAL_ASSETS_NORMALIZED_EXTRA_KEY = "discord_sticker_vision_normalized"


class DiscordVisualAssetFilter(filter.CustomFilter):
    def filter(self, event: AstrMessageEvent, cfg) -> bool:
        if _platform_name(event) != "discord":
            return False

        raw_message = _raw_message(event)
        if raw_message is None:
            return False

        assets = extract_visual_assets(raw_message)
        event.set_extra(VISUAL_ASSETS_EXTRA_KEY, assets)
        return bool(assets)


@star.register(
    "discord_sticker_vision",
    "0blueyan0",
    "Send Discord stickers and custom emoji to vision-capable LLMs.",
    "0.1.0",
)
class DiscordStickerVisionPlugin(star.Star):
    def __init__(self, context: star.Context) -> None:
        super().__init__(context)
        self.max_assets = 8

    @filter.custom_filter(DiscordVisualAssetFilter, priority=sys.maxsize)
    async def normalize_discord_visual_assets(self, event: AstrMessageEvent):
        assets = _get_visual_assets(event)
        if not assets:
            return
        _normalize_event_message(event, assets, max_assets=self.max_assets)

    @filter.on_llm_request()
    async def attach_discord_visual_assets(
        self, event: AstrMessageEvent, req: ProviderRequest
    ) -> None:
        if _normalized_assets_already_in_request(event, req):
            return

        if _platform_name(event) != "discord":
            return

        raw_message = _raw_message(event)
        if raw_message is None:
            return

        assets = extract_visual_assets(raw_message)
        if not assets:
            return

        _append_visual_assets(req, assets, max_assets=self.max_assets)

        attached_count = min(len(assets), self.max_assets)
        logger.debug(f"Attached {attached_count} Discord visual asset(s) to LLM request.")


def _platform_name(event: AstrMessageEvent) -> str:
    platform_meta = getattr(event, "platform_meta", None)
    return str(getattr(platform_meta, "name", "") or "").lower()


def _raw_message(event: AstrMessageEvent):
    return getattr(getattr(event, "message_obj", None), "raw_message", None)


def _get_visual_assets(event: AstrMessageEvent) -> list[DiscordVisualAsset]:
    assets = event.get_extra(VISUAL_ASSETS_EXTRA_KEY)
    if isinstance(assets, list):
        return assets

    raw_message = _raw_message(event)
    if raw_message is None:
        return []
    assets = extract_visual_assets(raw_message)
    event.set_extra(VISUAL_ASSETS_EXTRA_KEY, assets)
    return assets


def _append_visual_assets(
    req: ProviderRequest, assets: list[DiscordVisualAsset], *, max_assets: int
) -> None:
    for part in build_content_parts(assets, max_assets=max_assets):
        req.extra_user_content_parts.append(_to_content_part(part))


def _normalize_event_message(
    event: AstrMessageEvent, assets: list[DiscordVisualAsset], *, max_assets: int
) -> None:
    if event.get_extra(VISUAL_ASSETS_NORMALIZED_EXTRA_KEY, False):
        return

    notice_text = build_asset_notice_text(assets, max_assets=max_assets)
    if not notice_text:
        return

    message_obj = getattr(event, "message_obj", None)
    if message_obj is None:
        return

    chain = getattr(message_obj, "message", None)
    if not isinstance(chain, list):
        chain = []
        message_obj.message = chain

    chain.append(Plain(text=notice_text))
    for asset in assets[:max_assets]:
        chain.append(Image(file=asset.url, url=asset.url, filename=asset.name))

    existing_text = (getattr(event, "message_str", "") or "").strip()
    event.message_str = f"{existing_text}\n{notice_text}".strip()
    message_obj.message_str = event.message_str
    event.set_extra(VISUAL_ASSETS_NORMALIZED_EXTRA_KEY, True)


def _normalized_assets_already_in_request(
    event: AstrMessageEvent, req: ProviderRequest
) -> bool:
    return bool(
        event.get_extra(VISUAL_ASSETS_NORMALIZED_EXTRA_KEY, False)
        and getattr(req, "image_urls", None)
    )


def _to_content_part(part: dict[str, object]) -> TextPart | ImageURLPart:
    if part.get("type") == "text":
        return TextPart(text=str(part.get("text", "")))

    if part.get("type") == "image_url":
        image_url = part.get("image_url")
        if not isinstance(image_url, dict):
            raise ValueError("image_url content part must contain a dictionary")
        return ImageURLPart(
            image_url=ImageURLPart.ImageURL(
                url=str(image_url.get("url", "")),
                id=str(image_url.get("id", "")) or None,
            )
        )

    raise ValueError(f"unsupported content part type: {part.get('type')}")

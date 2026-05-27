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
    from .discord_sticker_vision.animation import prepare_visual_assets
except ImportError:
    from discord_sticker_vision.animation import prepare_visual_assets
    from discord_sticker_vision.assets import (
        DiscordVisualAsset,
        build_asset_notice_text,
        build_content_parts,
        extract_visual_assets,
    )


VISUAL_ASSETS_EXTRA_KEY = "discord_sticker_vision_assets"
VISUAL_ASSETS_PREPARED_EXTRA_KEY = "discord_sticker_vision_prepared_assets"
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
    "0.3.0",
)
class DiscordStickerVisionPlugin(star.Star):
    def __init__(self, context: star.Context) -> None:
        super().__init__(context)
        self.max_assets = 8
        self.animation_frame_count = 5
        self.cache_dir = star.StarTools.get_data_dir("discord_sticker_vision") / (
            "animation_cache"
        )

    @filter.custom_filter(DiscordVisualAssetFilter, priority=sys.maxsize)
    async def normalize_discord_visual_assets(self, event: AstrMessageEvent):
        assets = await _get_prepared_visual_assets(
            event,
            cache_dir=self.cache_dir,
            frame_count=self.animation_frame_count,
            max_assets=self.max_assets,
        )
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

        assets = await _get_prepared_visual_assets(
            event,
            cache_dir=self.cache_dir,
            frame_count=self.animation_frame_count,
            max_assets=self.max_assets,
        )
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


async def _get_prepared_visual_assets(
    event: AstrMessageEvent, *, cache_dir, frame_count: int, max_assets: int
) -> list[DiscordVisualAsset]:
    prepared_assets = event.get_extra(VISUAL_ASSETS_PREPARED_EXTRA_KEY)
    if isinstance(prepared_assets, list):
        return prepared_assets

    assets = _get_visual_assets(event)
    prepared_assets = await prepare_visual_assets(
        assets[:max_assets],
        cache_dir=cache_dir,
        frame_count=frame_count,
    )
    _log_animation_preparation(assets[:max_assets], prepared_assets)
    event.set_extra(VISUAL_ASSETS_PREPARED_EXTRA_KEY, prepared_assets)
    return prepared_assets


def _log_animation_preparation(
    raw_assets: list[DiscordVisualAsset], prepared_assets: list[DiscordVisualAsset]
) -> None:
    for raw_asset, prepared_asset in zip(raw_assets, prepared_assets):
        if not raw_asset.animated:
            continue
        if prepared_asset.frame_count:
            logger.info(
                "Prepared Discord animated asset contact sheet: "
                f"{raw_asset.kind} {raw_asset.name} ({prepared_asset.frame_count} frames)."
            )
        else:
            logger.warning(
                "Could not sample Discord animated asset, using static preview: "
                f"{raw_asset.kind} {raw_asset.name}."
            )


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
        chain.append(_to_image_component(asset))

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


def _to_image_component(asset: DiscordVisualAsset) -> Image:
    if asset.url.startswith(("http://", "https://", "base64://", "file://")):
        return Image(file=asset.url, url=asset.url, filename=asset.name)
    return Image.fromFileSystem(asset.url, filename=asset.name)

from __future__ import annotations

from astrbot.api import logger, star
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.provider import ProviderRequest
from astrbot.core.agent.message import ImageURLPart, TextPart

try:
    from .discord_sticker_vision.assets import (
        build_content_parts,
        extract_visual_assets,
    )
except ImportError:
    from discord_sticker_vision.assets import (
        build_content_parts,
        extract_visual_assets,
    )


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

    @filter.on_llm_request()
    async def attach_discord_visual_assets(
        self, event: AstrMessageEvent, req: ProviderRequest
    ) -> None:
        if _platform_name(event) != "discord":
            return

        raw_message = getattr(
            getattr(event, "message_obj", None), "raw_message", None
        )
        if raw_message is None:
            return

        assets = extract_visual_assets(raw_message)
        if not assets:
            return

        for part in build_content_parts(assets, max_assets=self.max_assets):
            req.extra_user_content_parts.append(_to_content_part(part))

        attached_count = min(len(assets), self.max_assets)
        logger.debug(f"Attached {attached_count} Discord visual asset(s) to LLM request.")


def _platform_name(event: AstrMessageEvent) -> str:
    platform_meta = getattr(event, "platform_meta", None)
    return str(getattr(platform_meta, "name", "") or "").lower()


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

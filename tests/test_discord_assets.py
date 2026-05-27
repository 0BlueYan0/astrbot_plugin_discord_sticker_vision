import unittest
from types import SimpleNamespace

from discord_sticker_vision.assets import (
    DiscordVisualAsset,
    build_asset_notice_text,
    build_content_parts,
    extract_visual_assets,
)


class DiscordAssetTests(unittest.TestCase):
    def test_extracts_static_and_animated_custom_emoji_urls_from_content(self):
        message = SimpleNamespace(
            content="look <:blobwave:123456789012345678> <a:dance:987654321098765432>",
            stickers=[],
        )

        assets = extract_visual_assets(message)

        self.assertEqual(
            assets,
            [
                DiscordVisualAsset(
                    kind="emoji",
                    name="blobwave",
                    url="https://cdn.discordapp.com/emojis/123456789012345678.png?size=128&quality=lossless",
                ),
                DiscordVisualAsset(
                    kind="emoji",
                    name="dance",
                    url="https://cdn.discordapp.com/emojis/987654321098765432.png?size=128&quality=lossless",
                    animated=True,
                    animation_url="https://cdn.discordapp.com/emojis/987654321098765432.gif?size=128&quality=lossless",
                ),
            ],
        )

    def test_extracts_sticker_urls_from_message_stickers(self):
        message = SimpleNamespace(
            content="",
            stickers=[
                SimpleNamespace(
                    id=111222333444555666,
                    name="thinking",
                    url="https://media.discordapp.net/stickers/111222333444555666.png",
                    format="png",
                ),
                SimpleNamespace(
                    id=444555666777888999,
                    name="party-gif-url",
                    url="https://media.discordapp.net/stickers/444555666777888999.gif?size=320",
                    format="gif",
                ),
                SimpleNamespace(
                    id=222333444555666777,
                    name="party",
                    format=SimpleNamespace(name="apng"),
                ),
                SimpleNamespace(
                    id=333444555666777888,
                    name="dance",
                    format="gif",
                ),
            ],
        )

        assets = extract_visual_assets(message)

        self.assertEqual(
            assets,
            [
                DiscordVisualAsset(
                    kind="sticker",
                    name="thinking",
                    url="https://media.discordapp.net/stickers/111222333444555666.png",
                ),
                DiscordVisualAsset(
                    kind="sticker",
                    name="party-gif-url",
                    url="https://cdn.discordapp.com/stickers/444555666777888999.png?size=320&quality=lossless",
                    animated=True,
                    animation_url="https://media.discordapp.net/stickers/444555666777888999.gif?size=320",
                ),
                DiscordVisualAsset(
                    kind="sticker",
                    name="party",
                    url="https://cdn.discordapp.com/stickers/222333444555666777.png?size=320&quality=lossless",
                    animated=True,
                    animation_url="https://cdn.discordapp.com/stickers/222333444555666777.png?size=320&quality=lossless",
                ),
                DiscordVisualAsset(
                    kind="sticker",
                    name="dance",
                    url="https://cdn.discordapp.com/stickers/333444555666777888.png?size=320&quality=lossless",
                    animated=True,
                    animation_url="https://cdn.discordapp.com/stickers/333444555666777888.gif?size=320&quality=lossless",
                ),
            ],
        )

    def test_builds_text_and_image_content_parts_with_stable_ids(self):
        assets = [
            DiscordVisualAsset(
                kind="emoji", name="blobwave", url="https://example.test/e.png"
            ),
            DiscordVisualAsset(
                kind="sticker", name="thinking", url="https://example.test/s.png"
            ),
        ]

        parts = build_content_parts(assets, max_assets=2)

        self.assertEqual(
            parts,
            [
                {"type": "text", "text": "[Discord emoji: blobwave]"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "https://example.test/e.png",
                        "id": "discord-emoji-1",
                    },
                },
                {"type": "text", "text": "[Discord sticker: thinking]"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "https://example.test/s.png",
                        "id": "discord-sticker-2",
                    },
                },
            ],
        )

    def test_builds_notice_text_for_downstream_context(self):
        assets = [
            DiscordVisualAsset(
                kind="emoji", name="blobwave", url="https://example.test/e.png"
            ),
            DiscordVisualAsset(
                kind="sticker", name="thinking", url="https://example.test/s.png"
            ),
        ]

        text = build_asset_notice_text(assets, max_assets=2)

        self.assertEqual(
            text,
            "[Discord emoji: blobwave]\n[Discord sticker: thinking]",
        )

    def test_builds_notice_text_for_sampled_animation_context(self):
        asset = DiscordVisualAsset(
            kind="emoji",
            name="dance",
            url="/tmp/dance-contact-sheet.png",
            animated=True,
            animation_url="https://example.test/dance.gif",
            frame_count=5,
        )

        text = build_asset_notice_text([asset])

        self.assertEqual(
            text,
            "[Discord animated emoji: dance; sampled into 5 frames]",
        )


if __name__ == "__main__":
    unittest.main()

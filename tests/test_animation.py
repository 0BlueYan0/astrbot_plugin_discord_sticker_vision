import tempfile
import unittest
from pathlib import Path

from PIL import Image

from discord_sticker_vision.animation import prepare_visual_assets
from discord_sticker_vision.assets import DiscordVisualAsset


class AnimationTests(unittest.IsolatedAsyncioTestCase):
    async def test_prepares_animated_gif_as_contact_sheet_png(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            gif_path = temp_path / "source.gif"
            frame_a = Image.new("RGBA", (12, 10), (255, 0, 0, 255))
            frame_b = Image.new("RGBA", (12, 10), (0, 255, 0, 255))
            frame_c = Image.new("RGBA", (12, 10), (0, 0, 255, 255))
            frame_a.save(
                gif_path,
                save_all=True,
                append_images=[frame_b, frame_c],
                duration=80,
                loop=0,
            )
            asset = DiscordVisualAsset(
                kind="emoji",
                name="dance",
                url="https://cdn.discordapp.com/emojis/123.png?size=128&quality=lossless",
                animated=True,
                animation_url=str(gif_path),
            )

            prepared = await prepare_visual_assets(
                [asset],
                cache_dir=temp_path / "cache",
                frame_count=3,
            )

            self.assertEqual(len(prepared), 1)
            self.assertTrue(prepared[0].animated)
            self.assertEqual(prepared[0].kind, "emoji")
            self.assertEqual(prepared[0].frame_count, 3)
            self.assertTrue(prepared[0].url.endswith(".png"))
            self.assertTrue(Path(prepared[0].url).exists())

            with Image.open(prepared[0].url) as contact_sheet:
                self.assertEqual(contact_sheet.format, "PNG")
                self.assertGreater(contact_sheet.width, frame_a.width)
                self.assertGreater(contact_sheet.height, frame_a.height)

    async def test_keeps_static_asset_unchanged(self):
        asset = DiscordVisualAsset(
            kind="emoji",
            name="blobwave",
            url="https://cdn.discordapp.com/emojis/123.png?size=128&quality=lossless",
        )

        prepared = await prepare_visual_assets([asset], cache_dir=Path("/tmp"))

        self.assertEqual(prepared, [asset])


if __name__ == "__main__":
    unittest.main()

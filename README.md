# astrbot_plugin_discord_sticker_vision

AstrBot plugin that forwards Discord custom emoji and sticker images to
vision-capable LLM providers.

## What it does

When AstrBot is about to send a Discord message to the LLM, this plugin inspects
the raw Discord message and appends extra user content parts:

- Discord custom emoji, including animated custom emoji
- Discord stickers exposed by the Discord adapter

The plugin adds a short text label before each image so the model can tell
whether the image came from an emoji or a sticker.

## Requirements

- AstrBot `>=4.17.0`
- Discord platform adapter
- A provider/model that supports image input
- Discord bot message content intent enabled

## Install

Place this repository under AstrBot's plugin directory:

```bash
AstrBot/data/plugins/astrbot_plugin_discord_sticker_vision
```

Then restart AstrBot or reload plugins from the WebUI.

## Notes

- Normal Discord Unicode emoji are text, so they are left unchanged.
- Custom emoji CDN URLs are generated from Discord's `<:name:id>` and
  `<a:name:id>` syntax.
- Sticker URLs are read from the Discord message when available. If AstrBot only
  exposes a sticker id and format, the plugin falls back to Discord's sticker
  CDN PNG/GIF URL.
- The plugin limits each request to 8 visual assets to avoid bloating a single
  LLM request.

## Development

Run the local tests with:

```bash
python3 -m unittest tests.test_discord_assets -v
```

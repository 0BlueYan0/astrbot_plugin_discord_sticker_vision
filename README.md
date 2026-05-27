# Discord Emoji & Sticker Vision

Discord Emoji & Sticker Vision 是一個 AstrBot 插件，用來把 Discord 自訂表情符號與貼圖圖片轉交給支援視覺輸入的 LLM provider。

## 功能

當 AstrBot 準備把 Discord 訊息送給 LLM 時，這個插件會檢查原始 Discord 訊息，並附加額外的使用者內容區塊：

- Discord 自訂表情符號，包含動態自訂表情符號
- Discord adapter 暴露出的 Discord 貼圖

插件會在每張圖片前加入簡短文字標籤，讓模型能分辨圖片來源是表情符號還是貼圖。

## 需求

- AstrBot `>=4.17.0`
- Discord platform adapter
- 支援圖片輸入的 provider/model
- Discord bot 已啟用 message content intent

## 安裝

將此 repository 放到 AstrBot 的插件目錄：

```bash
AstrBot/data/plugins/astrbot_plugin_discord_sticker_vision
```

接著重新啟動 AstrBot，或在 WebUI 重新載入插件。

## 注意事項

- 一般 Discord Unicode emoji 本來就是文字，因此會維持原樣。
- 自訂表情符號的 CDN URL 會從 Discord 的 `<:name:id>` 與 `<a:name:id>` 語法產生。
- 貼圖 URL 會優先從 Discord 訊息讀取；如果 AstrBot 只提供貼圖 id 與格式，插件會 fallback 到 Discord 的 sticker CDN PNG/GIF URL。
- 插件會將每次 request 限制在最多 8 個視覺素材，避免單次 LLM request 過度膨脹。

## 開發

執行本地測試：

```bash
python3 -m unittest tests.test_discord_assets -v
```

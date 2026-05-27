# 更新日誌

本專案遵循語意化版本號。所有值得使用者注意的變更都會記錄在這裡。

## [0.3.0] - 2026-05-27

### 新增

- 支援動態 Discord 自訂表情符號與動態貼圖的取樣處理。
- 新增 5 格 PNG contact sheet 產生流程，讓支援視覺輸入的 LLM 可以從多張影格推測動畫內容。
- 新增動畫素材快取目錄：`data/plugin_data/discord_sticker_vision/animation_cache`。
- 新增 `requirements.txt`，宣告 `Pillow>=10.0.0` 依賴。
- 新增動畫 contact sheet 單元測試。

### 變更

- 動態素材會優先嘗試使用動畫來源產生 contact sheet，再交給 AstrBot 與 LLM。
- 動態素材的上下文標籤會標示取樣影格數，例如 `[Discord animated emoji: dance; sampled into 5 frames]`。
- 插件版本更新為 `0.3.0`。

### 注意事項

- 如果 Discord CDN 沒有提供可讀取的動畫來源，插件會 fallback 到 PNG 靜態預覽。

## [0.2.0] - 2026-05-27

### 新增

- 將 Discord 貼圖與自訂表情符號補進 AstrBot message chain，讓其他插件可以在上下文中讀取。
- 支援與 `astrbot_plugin_group_chat_plus` 這類被動決定是否回覆的插件搭配使用。

### 變更

- 插件本身不主動呼叫 LLM，也不因為看到貼圖就強制回覆。
- 所有 Discord 對話只要包含貼圖或自訂表情符號，就會先做素材正規化。

### 修正

- 動態 Discord custom emoji 改用 PNG 靜態預覽，避免 provider 對 GIF 解析為空。
- Discord GIF 貼圖 fallback 改用 PNG 靜態預覽。

## [0.1.0] - 2026-05-27

### 新增

- 初版插件。
- 支援從 Discord 訊息解析自訂表情符號與貼圖 URL。
- 支援在 LLM request 中附加圖片內容與簡短來源標籤。
- 新增基本單元測試。

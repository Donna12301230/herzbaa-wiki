# 赫滋與羊 HerzBaa｜LLM Wiki＋合作夥伴教學簡報

依 [Karpathy 的 LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 構想，把插畫品牌「赫滋與羊」的公開資料整理成**給 AI 讀的知識庫**，再用它產出**給人看的教學簡報**。

- `raw/`：原始來源（官網、IG、海報轉錄），只增不改
- `wiki/`：AI 維護的知識頁，每句都附出處
- 規則全部寫在 [AGENTS.md](AGENTS.md)

## 成品

| 成品 | 連結 |
|---|---|
| 教學簡報（14 頁，給新合作夥伴／店家） | [slides/brand-intro.html](slides/brand-intro.html)（線上版：https://donna12301230.github.io/herzbaa-wiki/slides/brand-intro.html） |
| 簡報檢查報告 | [slides/檢查報告.md](slides/檢查報告.md) |
| 簡報流程（Graph，含流程圖） | [workflows/brand-slides.md](workflows/brand-slides.md) |

## Wiki 從哪裡開始讀

> Wiki 頁面之間用 Obsidian 的 `[[頁面]]` 連結，在 GitHub 網頁上不能點。想看連結圖，可以下載後用 Obsidian 開啟 `wiki/` 資料夾；在 GitHub 上看，請用下面的連結。

- 目錄：[wiki/index.md](wiki/index.md)
- 品牌：[赫滋與羊](wiki/entities/赫滋與羊.md)、[品牌起源故事](wiki/entities/品牌起源故事.md)、[聽故事・畫故事・展故事](wiki/entities/聽故事畫故事展故事.md)
- 計畫與作品：[故事模特創作計畫](wiki/entities/故事模特創作計畫.md)、[時光抽屜](wiki/entities/時光抽屜.md)
- 合作：[展覽空間合作](wiki/entities/展覽空間合作.md)、[地方文創系列](wiki/entities/地方文創系列.md)、[睏睏創作展](wiki/entities/睏睏創作展.md)、[異業合作](wiki/entities/異業合作.md)
- [合作問答](wiki/faq/合作問答.md)、[品牌時間線](wiki/timeline/品牌時間線.md)、[操作紀錄 log](wiki/log.md)

## 過程紀錄

- [需求訪談紀錄](docs/需求訪談紀錄.md)：先討論、後生成，10 題訪談後才建檔
- [執行紀錄](docs/執行紀錄.md)：每個檢查關卡抓到什麼、怎麼處理
- [Query 測試紀錄](docs/query測試紀錄.md)：用第七週驗收題組測 Wiki
- [第十週作業繳交說明](docs/第十週作業_繳交說明草稿.md)

## 工具

- `python tools/lint.py`：Wiki 健檢（出處、連結、品牌用字、個資與金額、待確認清單）
- `python tools/check_slides.py`：簡報忠實度檢查（每句出處、原文逐字比對、排除清單、HTML 與稿件一致）

Windows 若中文亂碼，先設 `PYTHONIOENCODING=utf-8`。

"""簡報忠實度檢查（workflows/brand-slides.md 節點 ⑥）

用法：python tools/check_slides.py [逐頁稿路徑]
預設檢查 slides/_work/05-逐頁稿.md。有 ERROR 時結束碼為 1。

檢查項目：
1. 每一句（`- ` 開頭）句尾都有〔出處〕
2. 出處頁存在於 wiki，且 public: 可對外
3. 沒有【待確認】【待補】字樣
4. 沒有排除清單（slides/_work/exclude_terms.txt）裡的詞——對應 wiki 頁尾「待確認」段落的內容
5. 【原文】引號內的文字，必須在出處頁裡逐字找得到
6. 品牌用字（赫茲）、金額、非白名單的 Email／電話
7. 電話那一句必須寫明「品牌官方電話」
8. 頁數 10–14
9. 若有 slides/brand-intro.html：逐頁稿每一句都要出現在 HTML 裡（防止渲染時改字），HTML 也要過排除清單、金額、錯字檢查
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "wiki"
sys.path.insert(0, str(ROOT / "tools"))
from lint import EMAIL_RE, PHONE_RE, MONEY_RE, read_list_file  # noqa: E402

SRC_RE = re.compile(r"〔([^〕]+)〕\s*$")
QUOTE_RE = re.compile(r"「(.+?)」")
META_SOURCE = "簡報結構"  # 只允許用在第 1 頁（封面副標）與第 2 頁（目錄），不是事實陳述


def load_pages():
    pages = {}
    for p in WIKI.rglob("*.md"):
        text = p.read_text(encoding="utf-8")
        m = re.search(r"^public:\s*(\S+)", text, re.M)
        pages[p.stem] = (m.group(1) if m else "", text)
    return pages


def norm(s):
    return re.sub(r"[\s「」]", "", s)


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "slides/_work/05-逐頁稿.md"
    lines = path.read_text(encoding="utf-8").splitlines()
    pages = load_pages()
    contacts = set(read_list_file("public_contacts.txt"))
    excl_file = ROOT / "slides/_work/exclude_terms.txt"
    exclude = [t.strip() for t in excl_file.read_text(encoding="utf-8").splitlines()
               if t.strip() and not t.startswith("#")] if excl_file.exists() else []

    errors, n_pages, n_lines, page_no = [], 0, 0, 0
    for i, line in enumerate(lines, 1):
        if line.startswith("## "):
            n_pages += 1
            page_no = n_pages
            continue
        if not line.startswith("- ") or page_no == 0:
            continue
        n_lines += 1
        where = f"第 {page_no} 頁（行 {i}）"
        m = SRC_RE.search(line)
        if not m:
            errors.append(f"{where}：沒有〔出處〕：{line}")
            continue
        body = line[2:m.start()]
        cited = [s.strip() for s in re.split(r"[、,]", m.group(1))]
        for s in cited:
            if s == META_SOURCE and page_no in (1, 2):
                continue
            if s not in pages:
                errors.append(f"{where}：出處「{s}」不是 wiki 頁")
            elif pages[s][0] != "可對外":
                errors.append(f"{where}：出處「{s}」不是可對外頁")
        if "【待確認】" in body or "【待補】" in body:
            errors.append(f"{where}：用到【待確認】或【待補】")
        for t in exclude:
            if t in body:
                errors.append(f"{where}：用到排除清單的「{t}」")
        if "【原文】" in body:
            for q in QUOTE_RE.findall(body):
                # 「……」代表省略：每一段都要逐字出現在出處頁
                segs = [x for x in q.split("……") if x.strip()]
                if not all(any(norm(g) in norm(pages.get(s, ("", ""))[1]) for s in cited) for g in segs):
                    errors.append(f"{where}：【原文】在出處頁找不到逐字對應：「{q}」")
        if "赫茲" in body:
            errors.append(f"{where}：品牌錯字「赫茲」")
        if MONEY_RE.search(body):
            errors.append(f"{where}：出現金額或比例")
        for x in EMAIL_RE.findall(body) + PHONE_RE.findall(body):
            if x not in contacts:
                errors.append(f"{where}：非白名單聯絡方式「{x}」")
        if PHONE_RE.search(body) and "品牌官方電話" not in body and "仁和" not in body:
            errors.append(f"{where}：電話要寫明「品牌官方電話」")

    html_path = ROOT / "slides/brand-intro.html"
    if html_path.exists() and path.name == "05-逐頁稿.md":
        raw_html = html_path.read_text(encoding="utf-8")
        raw_html = re.sub(r"<(script|style)[^>]*>.*?</>", "", raw_html, flags=re.S)
        visible = re.sub(r"<[^>]+>", "", raw_html)
        flat = re.sub(r"[\s：、→｜]", "", visible)  # 排版會把「標籤：內文」拆成兩個元素，比對時忽略這些分隔標點
        for i, line in enumerate(lines, 1):
            m = SRC_RE.search(line) if line.startswith("- ") else None
            if not m:
                continue
            body = re.sub(r"[\s：、→｜]", "", line[2:m.start()].replace("【原文】", ""))
            if body not in flat:
                errors.append(f"HTML：逐頁稿第 {i} 行的句子在 HTML 裡找不到（渲染時改了字？）：{body}")
        for t in exclude:
            if t in visible:
                errors.append(f"HTML：用到排除清單的「{t}」")
        if "赫茲" in visible or MONEY_RE.search(visible):
            errors.append("HTML：出現錯字「赫茲」或金額")

    if not 10 <= n_pages <= 14:
        errors.append(f"頁數 {n_pages}，不在 10–14 頁")

    print(f"檢查 {path.name}：{n_pages} 頁、{n_lines} 句")
    print(f"ERROR（{len(errors)}）")
    for e in errors:
        print("  - " + e)
    print("結果：" + ("✅ 通過" if not errors else "❌ 有錯，退回 ⑤ 逐頁稿"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

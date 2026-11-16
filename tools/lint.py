"""赫滋與羊 LLM Wiki 健檢程式。

用法：python tools/lint.py
Windows 若中文亂碼，先設環境變數 PYTHONIOENCODING=utf-8。
有 ERROR 時結束碼為 1；WARN 和 INFO 只提醒。
"""

from __future__ import annotations

import re
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "wiki"
RAW = ROOT / "raw"
TOOLS = ROOT / "tools"

REQUIRED = ["title", "type", "summary", "keywords", "sources", "public", "updated"]
TYPES = {"entity", "source", "faq", "timeline", "index", "log"}
CATEGORIES = {"角色", "作品", "計畫", "合作案例", "品牌", "地點活動"}
PUBLIC_VALUES = {"可對外", "內部參考"}
NO_INBOUND_NEEDED = {"index", "log"}
STALE_DAYS = 180
SUMMARY_MAX = 40

# 官腔詞：不是錯，但讀起來像公文，提醒改成創作者自己的口吻
OFFICIAL_WORDS = ["致力於", "秉持", "打造", "賦能", "全方位", "一站式", "深耕", "引領", "極致"]

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?<!\d)(09\d{2}[-\s]?\d{3}[-\s]?\d{3}|0\d{1,2}[-\s]?\d{3,4}[-\s]?\d{4})(?!\d)")
MONEY_RE = re.compile(r"(NT\$|新台幣|新臺幣|US\$|\$\s?\d|\d[\d,]*\s?(元|萬元|塊))")
LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)

errors: list[str] = []
warns: list[str] = []
infos: list[str] = []


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def read_list_file(name: str) -> list[str]:
    p = TOOLS / name
    if not p.exists():
        return []
    lines = p.read_text(encoding="utf-8").splitlines()
    return [s.strip() for s in lines if s.strip() and not s.strip().startswith("#")]


def parse_frontmatter(text: str) -> tuple[dict | None, str]:
    m = FM_RE.match(text)
    if not m:
        return None, text
    data: dict = {}
    for line in m.group(1).splitlines():
        line = line.split(" #", 1)[0].rstrip()  # 去掉行尾註解
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        val = val.strip()
        if val.startswith("[") and val.endswith("]"):
            data[key.strip()] = [v.strip() for v in val[1:-1].split(",") if v.strip()]
        else:
            data[key.strip()] = val
    return data, text[m.end():]


def strip_code(text: str) -> str:
    return re.sub(r"```.*?```", "", text, flags=re.S)


def main() -> int:
    pages = sorted(p for p in WIKI.rglob("*.md"))
    raw_files = sorted(p for p in RAW.rglob("*") if p.is_file() and p.name != ".gitkeep")
    raw_stems = {p.stem for p in raw_files}
    private_terms = read_list_file("private_terms.txt")
    public_contacts = set(read_list_file("public_contacts.txt"))

    # --- 檔名重複 ---
    by_stem: dict[str, list[Path]] = {}
    for p in pages:
        by_stem.setdefault(p.stem, []).append(p)
    for stem, ps in by_stem.items():
        if len(ps) > 1:
            errors.append(f"檔名重複「{stem}」：{', '.join(rel(p) for p in ps)}（[[連結]] 會分不清）")

    meta: dict[str, dict] = {}
    bodies: dict[str, str] = {}
    inbound: dict[str, set[str]] = {p.stem: set() for p in pages}

    for p in pages:
        text = p.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        name = rel(p)
        if fm is None:
            errors.append(f"{name}：沒有 frontmatter")
            fm = {}
        meta[p.stem] = fm
        bodies[p.stem] = body

        # --- frontmatter 欄位 ---
        for k in REQUIRED:
            if k not in fm:
                errors.append(f"{name}：frontmatter 缺少 {k}")
        t = fm.get("type")
        if t and t not in TYPES:
            errors.append(f"{name}：type「{t}」不在 {sorted(TYPES)}")
        if t == "entity" and fm.get("category") not in CATEGORIES:
            errors.append(f"{name}：entity 頁的 category 要是 {sorted(CATEGORIES)} 之一")
        if fm.get("public") and fm["public"] not in PUBLIC_VALUES:
            errors.append(f"{name}：public 要是「可對外」或「內部參考」")
        if t == "source" and not p.stem.startswith("src-"):
            errors.append(f"{name}：來源頁檔名要以 src- 開頭")
        if len(str(fm.get("summary", ""))) > SUMMARY_MAX:
            warns.append(f"{name}：summary 超過 {SUMMARY_MAX} 字")

        upd = fm.get("updated")
        if upd:
            try:
                d = datetime.strptime(str(upd), "%Y-%m-%d").date()
                if (date.today() - d).days > STALE_DAYS:
                    warns.append(f"{name}：超過 {STALE_DAYS} 天沒更新（{upd}）")
            except ValueError:
                errors.append(f"{name}：updated 格式要是 YYYY-MM-DD")

        # --- sources 欄位指到存在的來源頁 ---
        srcs = fm.get("sources") or []
        if isinstance(srcs, str):
            srcs = [srcs]
        for s in srcs:
            if not s.startswith("src-") or s not in by_stem:
                errors.append(f"{name}：sources 裡的「{s}」找不到對應的來源頁")
        if t == "entity" and not srcs:
            errors.append(f"{name}：實體頁的 sources 不可為空")

        # --- 來源頁要對應到 raw 檔 ---
        if t == "source":
            raw_stem = p.stem[len("src-"):]
            if raw_stem not in raw_stems:
                errors.append(f"{name}：找不到對應的 raw 檔 raw/**/{raw_stem}.*")

        clean = strip_code(body)

        # --- 實體頁內文要有出處 ---
        if t == "entity" and not re.search(r"\[\[src-", clean):
            errors.append(f"{name}：內文沒有任何（來源：[[src-…]]）出處")

        # --- 連結 ---
        for target in LINK_RE.findall(clean):
            target = target.strip()
            if target not in by_stem:
                errors.append(f"{name}：連結 [[{target}]] 指到不存在的頁面")
            else:
                inbound[target].add(p.stem)

    # --- index 有列到每一頁 ---
    if "index" in bodies:
        listed = set(LINK_RE.findall(bodies["index"]))
        for stem in by_stem:
            if stem != "index" and stem not in listed:
                errors.append(f"wiki/index.md 沒有列到「{stem}」")
    else:
        errors.append("缺少 wiki/index.md")
    if "log" not in by_stem:
        errors.append("缺少 wiki/log.md")

    # --- 孤兒頁（index 以外沒有頁面連過來） ---
    for stem, srcs in inbound.items():
        if stem in NO_INBOUND_NEEDED:
            continue
        if not (srcs - {"index"}):
            warns.append(f"孤兒頁「{stem}」：除了 index 以外沒有頁面連過來")

    # --- 文字檢查：wiki 頁 ---
    for p in pages:
        name = rel(p)
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if line.startswith("keywords:"):
                continue
            if "赫茲" in line:
                errors.append(f"{name}:{i}：出現錯字「赫茲」（正確是赫滋）")
            for w in OFFICIAL_WORDS:
                if w in line:
                    warns.append(f"{name}:{i}：官腔詞「{w}」")
            for m in EMAIL_RE.findall(line):
                if m not in public_contacts:
                    errors.append(f"{name}:{i}：出現 Email「{m}」（官方窗口請加進 tools/public_contacts.txt）")
            for m in PHONE_RE.findall(line):
                if m not in public_contacts:
                    errors.append(f"{name}:{i}：疑似電話「{m}」")
            if MONEY_RE.search(line):
                errors.append(f"{name}:{i}：出現金額，對外一律寫「請洽創作者」")
            for term in private_terms:
                if term in line:
                    errors.append(f"{name}:{i}：出現敏感詞（private_terms.txt 第 {private_terms.index(term) + 1} 個）")
            for tag in ("【待確認】", "【待補】"):
                if tag in line and p.stem not in NO_INBOUND_NEEDED:
                    infos.append(f"{name}:{i}：{tag} {line.strip()[:50]}")

    # --- 文字檢查：raw 檔（也會公開） ---
    for p in raw_files:
        if p.suffix.lower() not in {".md", ".txt"}:
            continue
        name = rel(p)
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for term in private_terms:
                if term in line:
                    errors.append(f"{name}:{i}：raw 出現敏感詞（private_terms.txt 第 {private_terms.index(term) + 1} 個）")
            for m in EMAIL_RE.findall(line) + PHONE_RE.findall(line):
                if m not in public_contacts:
                    warns.append(f"{name}:{i}：raw 出現聯絡資訊「{m}」，確認是公開的官方窗口")

    # --- 輸出 ---
    print(f"頁面 {len(pages)} 個、raw 檔 {len(raw_files)} 個、敏感詞 {len(private_terms)} 個")
    for label, items in (("ERROR", errors), ("WARN", warns), ("INFO", infos)):
        print(f"\n{label}（{len(items)}）")
        for it in items:
            print(f"  - {it}")
    print("\n結果：" + ("❌ 有錯誤要修" if errors else "✅ 沒有錯誤"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

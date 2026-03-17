import csv
import re
import sys
import time
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup, Tag, NavigableString

BASE_FIRST_PAGE = "https://m.cuoceng.com/book/category/6b09b233-4d99-4f8f-aeb0-f9772e107d49.html"
BASE_PAGE_FMT = "https://m.cuoceng.com/book/category/6b09b233-4d99-4f8f-aeb0-f9772e107d49/{page}.html"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36"
    ),
    "Referer": "https://m.cuoceng.com/",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def build_page_url(page: int) -> str:
    if page <= 1:
        return BASE_FIRST_PAGE
    return BASE_PAGE_FMT.format(page=page)


def fetch_html(url: str, timeout: int = 20) -> str:
    resp = SESSION.get(url, timeout=timeout)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or resp.encoding or "utf-8"
    return resp.text


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def find_text_after_label(container: Tag, label: str) -> str:
    """
    在某个条目容器内，寻找形如“字数：xxx”“简介：xxx”的文本。
    """
    text = container.get_text("\n", strip=True)
    m = re.search(rf"{re.escape(label)}\s*：\s*(.+)", text)
    if m:
        return clean_text(m.group(1))
    return ""


def find_book_blocks(soup: BeautifulSoup) -> List[Tag]:
    """
    站点 HTML 可能有轻微变动，因此不死绑 class。
    当前页面上每本书都有一个标题链接，标题通常位于 h2 / heading 附近。
    这里采用“找到阅读链接对应的父级块，再向上归并”的宽松策略。
    """
    blocks = []

    # 优先找包含“简介：”“字数：”的块
    for tag in soup.find_all(True):
        txt = tag.get_text(" ", strip=True)
        if "字数：" in txt and "简介：" in txt:
            # 过滤过大的容器，避免把整页当成一个块
            text_len = len(txt)
            if 30 < text_len < 5000:
                blocks.append(tag)

    # 去重：保留更小、更贴近单本书的容器
    unique = []
    seen = set()
    for blk in blocks:
        key = str(id(blk))
        if key not in seen:
            seen.add(key)
            unique.append(blk)

    # 如果找到很多重叠容器，做一次“只保留不包含其他候选块的最小块”
    final_blocks = []
    for blk in unique:
        has_child_candidate = False
        for other in unique:
            if blk is other:
                continue
            if blk.find(lambda x: x is other):
                has_child_candidate = True
                break
        if not has_child_candidate:
            final_blocks.append(blk)

    # 数量异常时，交给标题链接方案兜底
    if len(final_blocks) >= 8:
        return final_blocks

    # 兜底方案：找标题链接，再向上找同时含“字数：”“简介：”的最小父容器
    candidate_blocks = []
    for a in soup.find_all("a", href=True):
        title = clean_text(a.get_text())
        if not title or title in {"阅读", "搜索", "首页", "书库", "排行", "全本"}:
            continue

        parent = a
        chosen = None
        for _ in range(6):
            parent = parent.parent
            if not isinstance(parent, Tag):
                break
            txt = parent.get_text(" ", strip=True)
            if "字数：" in txt and "简介：" in txt:
                chosen = parent
                break

        if chosen is not None:
            candidate_blocks.append(chosen)

    # 去重
    dedup = []
    ids = set()
    for blk in candidate_blocks:
        if id(blk) not in ids:
            ids.add(id(blk))
            dedup.append(blk)

    return dedup


def extract_title(block: Tag) -> str:
    # 优先找非“阅读”链接
    for a in block.find_all("a", href=True):
        t = clean_text(a.get_text())
        if t and t != "阅读" and len(t) <= 80:
            return t

    # 兜底：从文本中提取
    text = block.get_text("\n", strip=True)
    lines = [clean_text(x) for x in text.splitlines() if clean_text(x)]
    for line in lines:
        if (
            not line.startswith("作者：")
            and not line.startswith("字数：")
            and not line.startswith("更新到：")
            and not line.startswith("简介：")
            and line != "阅读"
            and len(line) <= 80
        ):
            return line
    return ""


def extract_words(block: Tag) -> str:
    return find_text_after_label(block, "字数")


def extract_intro(block: Tag) -> str:
    intro = find_text_after_label(block, "简介")
    if intro:
        return intro

    text = block.get_text("\n", strip=True)
    m = re.search(r"简介\s*：\s*(.+?)(?:阅读|$)", text, flags=re.S)
    if m:
        return clean_text(m.group(1))
    return ""


def parse_page(html: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    blocks = find_book_blocks(soup)

    results = []
    seen = set()

    for block in blocks:
        name = extract_title(block)
        words = extract_words(block)
        intro = extract_intro(block)

        if not name or not words:
            continue

        key = (name, words, intro)
        if key in seen:
            continue
        seen.add(key)

        results.append({
            "name": name,
            "words": words,
            "intro": intro,
        })

    # 最后一层兜底：直接从整页文本正则抽取
    if results:
        return results

    text = soup.get_text("\n", strip=True)
    pattern = re.compile(
        r"""
        (?P<name>[^\n]+)\s+
        作者：.*?\s+
        字数：(?P<words>[^\n]+)\s+
        更新到：.*?\s+
        简介：(?P<intro>.*?)
        (?=\s+阅读\s+|$)
        """,
        re.S | re.X,
    )

    fallback = []
    seen = set()
    for m in pattern.finditer(text):
        item = {
            "name": clean_text(m.group("name")),
            "words": clean_text(m.group("words")),
            "intro": clean_text(m.group("intro")),
        }
        key = (item["name"], item["words"], item["intro"])
        if key not in seen and item["name"] and item["words"]:
            seen.add(key)
            fallback.append(item)

    return fallback


def crawl(max_pages: int, sleep_sec: float = 0.6) -> List[Dict[str, str]]:
    all_items = []

    for page in range(1, max_pages + 1):
        url = build_page_url(page)
        print(f"[+] 抓取第 {page} 页: {url}")

        try:
            html = fetch_html(url)
            items = parse_page(html)
            print(f"    提取到 {len(items)} 条")
            all_items.extend(items)
        except Exception as e:
            print(f"    第 {page} 页失败: {e}")

        time.sleep(sleep_sec)

    # 跨页去重
    deduped = []
    seen = set()
    for item in all_items:
        key = (item["name"], item["words"], item["intro"])
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped


def save_csv(items: List[Dict[str, str]], output_file: str) -> None:
    with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "words", "intro"])
        writer.writeheader()
        writer.writerows(items)


def main():
    # 用法：
    # python cuoceng_spider.py 40
    # python cuoceng_spider.py 40 result.csv
    if len(sys.argv) < 2:
        print("用法: python cuoceng_spider.py <页数> [输出文件名]")
        sys.exit(1)

    try:
        max_pages = int(sys.argv[1])
        if max_pages <= 0:
            raise ValueError
    except ValueError:
        print("页数必须是正整数")
        sys.exit(1)

    output_file = sys.argv[2] if len(sys.argv) >= 3 else "cuoceng_books.csv"

    items = crawl(max_pages=max_pages)
    save_csv(items, output_file)

    print(f"\n完成，共保存 {len(items)} 条到 {output_file}")


if __name__ == "__main__":
    main()
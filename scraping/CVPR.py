import csv
import json
import re
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

BASE_URL = "https://openaccess.thecvf.com"
INDEX_URL = "https://openaccess.thecvf.com/CVPR2024?day=all"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

DETAIL_HREF_RE = re.compile(r"^/content/CVPR2024/html/.+_paper\.html$")
PROCEEDINGS_RE = re.compile(
    r"Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition \(CVPR\),?\s*2024",
    re.IGNORECASE,
)


def clean_text(text: Optional[str]) -> str:
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def safe_console_text(text: str) -> str:
    cleaned = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned.encode("ascii", errors="backslashreplace").decode("ascii")


def log(message: str) -> None:
    try:
        print(safe_console_text(message))
    except OSError:
        pass


def get_soup(session: requests.Session, url: str) -> BeautifulSoup:
    resp = session.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def extract_detail_urls(index_soup: BeautifulSoup) -> List[str]:
    urls = []
    seen = set()

    for a in index_soup.find_all("a", href=True):
        href = a["href"].strip()
        if DETAIL_HREF_RE.search(href):
            full_url = urljoin(BASE_URL, href)
            if full_url not in seen:
                seen.add(full_url)
                urls.append(full_url)

    return urls


def find_title(soup: BeautifulSoup) -> str:
    # 常见 CVF 结构优先
    selectors = [
        ("div", {"id": "papertitle"}),
        ("div", {"class": "ptitle"}),
        ("div", {"class": "papertitle"}),
        ("h1", {}),
        ("h2", {}),
        ("title", {}),
    ]

    for name, attrs in selectors:
        node = soup.find(name, attrs=attrs)
        text = clean_text(node.get_text(" ", strip=True)) if node else ""
        if text and "CVPR 2024" not in text and "Open Access" not in text:
            return text

    # 回退：找最像标题的较长文本
    candidates = []
    for tag in soup.find_all(["div", "p", "span", "strong"]):
        text = clean_text(tag.get_text(" ", strip=True))
        if not text:
            continue
        if len(text) < 20:
            continue
        if "Abstract" in text or "Related Material" in text:
            continue
        if "Proceedings of the IEEE/CVF" in text:
            continue
        candidates.append(text)

    return candidates[0] if candidates else ""


def find_authors_and_citation(soup: BeautifulSoup) -> Dict[str, str]:
    full_line = ""
    authors = ""
    citation = ""

    text_nodes = []
    for tag in soup.find_all(["div", "p"]):
        text = clean_text(tag.get_text(" ", strip=True))
        if text:
            text_nodes.append(text)

    for text in text_nodes:
        if PROCEEDINGS_RE.search(text):
            full_line = text
            break

    if full_line:
        parts = re.split(
            r";\s*(Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition \(CVPR\),?\s*2024.*)",
            full_line,
            maxsplit=1,
            flags=re.IGNORECASE,
        )
        if len(parts) >= 3:
            authors = clean_text(parts[0])
            citation = clean_text(parts[1])
        else:
            m = PROCEEDINGS_RE.search(full_line)
            if m:
                authors = clean_text(full_line[:m.start("0")] if "0" in getattr(m, "groupindex", {}) else full_line[:m.start()])
                citation = clean_text(full_line[m.start():])

    return {
        "authors_line": full_line,
        "authors": authors,
        "citation": citation,
    }


def find_section_content(soup: BeautifulSoup, heading_text: str) -> str:
    heading = None

    # 先找精确标题节点
    for tag in soup.find_all(["h2", "h3", "h4", "div", "strong", "b"]):
        text = clean_text(tag.get_text(" ", strip=True))
        if text.lower() == heading_text.lower():
            heading = tag
            break

    # 回退：包含 heading_text 的短节点
    if heading is None:
        for tag in soup.find_all(["div", "p", "strong", "b"]):
            text = clean_text(tag.get_text(" ", strip=True))
            if text.lower() == heading_text.lower():
                heading = tag
                break

    if heading is None:
        return ""

    chunks = []
    for sib in heading.next_siblings:
        if isinstance(sib, NavigableString):
            text = clean_text(str(sib))
            if text:
                chunks.append(text)
            continue

        if not isinstance(sib, Tag):
            continue

        sib_text = clean_text(sib.get_text(" ", strip=True))
        if not sib_text:
            continue

        # 遇到下一个明显段落标题就停止
        if sib_text in {"Related Material", "BibTeX", "bibtex", "Cite this paper"}:
            break

        if sib.name in {"h1", "h2", "h3", "h4"}:
            break

        chunks.append(sib_text)

    # 有些页面摘要拆成多段
    return clean_text(" ".join(chunks))


def find_material_links(soup: BeautifulSoup, detail_url: str) -> Dict[str, str]:
    pdf_url = ""
    supp_url = ""
    arxiv_url = ""

    for a in soup.find_all("a", href=True):
        text = clean_text(a.get_text(" ", strip=True)).lower()
        href = a["href"].strip()
        full_url = urljoin(detail_url, href)

        if text == "pdf" or href.lower().endswith(".pdf"):
            if not pdf_url:
                pdf_url = full_url
        elif text in {"supp", "supplemental", "supplementary"} or "supp" in href.lower():
            if not supp_url:
                supp_url = full_url
        elif "arxiv" in text or "arxiv.org" in href.lower():
            if not arxiv_url:
                arxiv_url = full_url

    return {
        "pdf_url": pdf_url,
        "supp_url": supp_url,
        "arxiv_url": arxiv_url,
    }


def parse_bibtex(soup: BeautifulSoup) -> str:
    # 常见情况：页面尾部有 pre 或文本块
    for tag in soup.find_all(["pre", "div", "p"]):
        text = clean_text(tag.get_text("\n", strip=True))
        if text.startswith("@InProceedings{") or text.startswith("@inproceedings{"):
            return text
    return ""


def parse_detail_page(session: requests.Session, detail_url: str) -> Dict[str, str]:
    soup = get_soup(session, detail_url)

    title = find_title(soup)
    author_info = find_authors_and_citation(soup)
    abstract = find_section_content(soup, "Abstract")
    links = find_material_links(soup, detail_url)
    bibtex = parse_bibtex(soup)

    return {
        "title": title,
        "authors": author_info["authors"],
        "authors_line": author_info["authors_line"],
        "citation": author_info["citation"],
        "abstract": abstract,
        "detail_url": detail_url,
        "pdf_url": links["pdf_url"],
        "supp_url": links["supp_url"],
        "arxiv_url": links["arxiv_url"],
        "bibtex": bibtex,
    }


def save_json(records: List[Dict[str, str]], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def save_csv(records: List[Dict[str, str]], path: str) -> None:
    if not records:
        return

    fieldnames = [
        "title",
        "authors",
        "authors_line",
        "citation",
        "abstract",
        "detail_url",
        "pdf_url",
        "supp_url",
        "arxiv_url",
        "bibtex",
    ]

    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def main() -> None:
    session = requests.Session()

    log(f"Fetching index page: {INDEX_URL}")
    index_soup = get_soup(session, INDEX_URL)

    detail_urls = extract_detail_urls(index_soup)
    log(f"Found {len(detail_urls)} detail pages")

    records = []
    for i, url in enumerate(detail_urls, 1):
        try:
            record = parse_detail_page(session, url)
            if record["title"]:
                records.append(record)
            log(f"[{i}/{len(detail_urls)}] OK - {record['title'][:80]}")
        except Exception as e:
            log(f"[{i}/{len(detail_urls)}] FAILED - {url} - {e}")
        time.sleep(0.2)

    save_json(records, "cvpr2024_papers.json")
    save_csv(records, "cvpr2024_papers.csv")
    log(f"Saved {len(records)} records to cvpr2024_papers.json and cvpr2024_papers.csv")


if __name__ == "__main__":
    main()

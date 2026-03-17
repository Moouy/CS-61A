import json
import os
import re
import sys
import time
import hashlib
import urllib.request
import urllib.parse
from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
IMAGE_MIME_PREFIXES = (
    "image/jpeg",
    "image/png",
    "image/webp",
)


def safe_filename(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]+', "_", name)
    name = re.sub(r"\s+", "_", name).strip("._")
    return name or "file"


def guess_extension_from_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.lower()
    for ext in IMAGE_EXTENSIONS:
        if path.endswith(ext):
            return ext
    return ".jpg"


def build_name_from_url(url: str, index: int) -> str:
    parsed = urllib.parse.urlparse(url)
    path_name = os.path.basename(parsed.path)
    path_name = safe_filename(path_name)

    if not path_name or "." not in path_name:
        ext = guess_extension_from_url(url)
        digest = hashlib.md5(url.encode("utf-8")).hexdigest()[:12]
        return f"img_{index:05d}_{digest}{ext}"

    stem, ext = os.path.splitext(path_name)
    if ext.lower() not in IMAGE_EXTENSIONS:
        ext = guess_extension_from_url(url)

    digest = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
    return f"{safe_filename(stem)}_{digest}{ext}"


def is_image_entry(entry: dict) -> bool:
    response = entry.get("response", {})
    content = response.get("content", {}) or {}
    mime_type = (content.get("mimeType") or "").lower()
    url = entry.get("request", {}).get("url", "")

    if any(mime_type.startswith(prefix) for prefix in IMAGE_MIME_PREFIXES):
        return True

    lower_url = url.lower()
    return any(lower_url.split("?", 1)[0].endswith(ext) for ext in IMAGE_EXTENSIONS)


def extract_image_urls_from_har(har_path: Path) -> list[str]:
    with har_path.open("r", encoding="utf-8") as f:
        har = json.load(f)

    entries = har.get("log", {}).get("entries", [])
    urls = []
    seen = set()

    for entry in entries:
        if not is_image_entry(entry):
            continue

        url = entry.get("request", {}).get("url", "")
        if not url:
            continue

        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            continue

        if url not in seen:
            seen.add(url)
            urls.append(url)

    return urls


def save_url_list(urls: list[str], out_txt: Path) -> None:
    with out_txt.open("w", encoding="utf-8") as f:
        for url in urls:
            f.write(url + "\n")


def download_file(url: str, out_path: Path, timeout: int = 30) -> tuple[bool, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/146.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.instagram.com/",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        with out_path.open("wb") as f:
            f.write(data)
        return True, "ok"
    except Exception as e:
        return False, str(e)


def download_all(urls: list[str], output_dir: Path, sleep_seconds: float = 0.5) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    fail_count = 0

    for i, url in enumerate(urls, start=1):
        filename = build_name_from_url(url, i)
        out_path = output_dir / filename

        if out_path.exists():
            print(f"[{i}/{len(urls)}] 已存在，跳过: {out_path.name}")
            continue

        ok, msg = download_file(url, out_path)
        if ok:
            success_count += 1
            print(f"[{i}/{len(urls)}] 下载成功: {out_path.name}")
        else:
            fail_count += 1
            print(f"[{i}/{len(urls)}] 下载失败: {url}")
            print(f"    原因: {msg}")

        time.sleep(sleep_seconds)

    print()
    print(f"完成。成功 {success_count} 张，失败 {fail_count} 张。")
    print(f"输出目录: {output_dir.resolve()}")


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python instagram_har_downloader.py instagram.har")
        print("  python instagram_har_downloader.py instagram.har output_dir")
        sys.exit(1)

    har_path = Path(sys.argv[1])
    if not har_path.exists():
        print(f"找不到 HAR 文件: {har_path}")
        sys.exit(1)

    output_dir = Path(sys.argv[2]) if len(sys.argv) >= 3 else Path("instagram_images")

    urls = extract_image_urls_from_har(har_path)
    if not urls:
        print("HAR 中没有提取到图片 URL。")
        sys.exit(1)

    url_list_file = output_dir.parent / "image_urls.txt"
    save_url_list(urls, url_list_file)

    print(f"共提取到 {len(urls)} 个图片 URL")
    print(f"URL 列表已保存到: {url_list_file.resolve()}")
    print()

    download_all(urls, output_dir)


if __name__ == "__main__":
    main()
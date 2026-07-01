import argparse
import json
import os
import random
import re
import time
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
import hashlib
import bencodepy
from urllib.parse import urlparse
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
import requests
from bs4 import BeautifulSoup

SOURCES = [
    {
        "site": "141love",
        "url": "https://141love.net/forum.php?mod=forumdisplay&fid=271&filter=typeid&typeid=557",
        "tag": "动漫精品",
    },
    {
        "site": "hjd2048",
        "url": "https://hjd2048.com/2048/thread.php?fid=5",
        "tag": "岛国有码",
    },
    {
        "site": "hjd2048",
        "url": "https://hjd2048.com/2048/thread.php?fid=4",
        "tag": "岛国无码",
    },
    {
        "site": "hjd2048",
        "url": "https://hjd2048.com/2048/thread.php?fid=13",
        "tag": "西方美人",
    },
    {
        "site": "hjd2048",
        "url": "https://hjd2048.com/2048/thread.php?fid=15",
        "tag": "国产原创",
    },
    {
        "site": "hjd2048",
        "url": "https://hjd2048.com/2048/thread.php?fid=16",
        "tag": "高清中文",
    },
    {
        "site": "hjd2048",
        "url": "https://hjd2048.com/2048/thread.php?fid=18",
        "tag": "三级伦理",
    },
    {
        "site": "sehuatang",
        "url": "https://www.sehuatang.org/forum-104-1.html",
        "tag": "素人系列",
    },
]

SOURCE_URL = (
    "https://141love.net/forum.php?"
    "mod=forumdisplay&fid=271&filter=typeid&typeid=557"
)
SOURCE_TAG = "动漫精品"
API_URL = os.getenv(
    "API",
    "http://127.0.0.1:5050/api/sync/insertCili",
)
COOKIE = os.getenv("cookie", "").strip()
PROCESSED_FILE = Path("processed_threads.json")
IMAGE_DIR = Path(os.getenv("CRAWLER_IMAGE_PATH", "images"))
PARSED_LOG_FILE = Path("logs/logging.json")
STATS_FILE = Path("logs/stats.json")
MAGNET_PATTERN = re.compile(
    r"magnet:\?xt=urn:btih:[a-zA-Z0-9]+(?:&[^\s\"'<>]+)*",
    re.IGNORECASE,
)
INFO_HASH_PATTERN = re.compile(r"(?<![a-fA-F0-9])([a-fA-F0-9]{40})(?![a-fA-F0-9])")
THREAD_PATTERN = re.compile(r"(?:thread-|tid=)(\d+)")
SIZE_PATTERN = re.compile(
    r"(?:影片大小|文件大小|檔案大小|档案大小)[】\]]?\s*[：:]\s*"
    r"([\d.]+)\s*(B|K|KB|M|MB|G|GB|T|TB)",
    re.IGNORECASE,
)
MAKER_PATTERN = re.compile(r"\[([^\[\]]+)\]")
BROWSER_VERIFIED = False

REQUIRED_FIELDS = {
    "title",
    "tag",
    "magnet_url",
    "actors",
    "content",
    "thumb",
    "cover",
    "series",
    "publish_time",
    "sub_tag",
    "duration",
    "maker",
    "collect_page",
    "size",
}

def send_telegram(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message},
            timeout=10,
        )
    except requests.RequestException as error:
        print(f"Telegram notification failed: {error}")

def validate_payload(payload):
    missing = [field for field in REQUIRED_FIELDS if field not in payload]

    if missing:
        raise ValueError(f"missing payload fields: {', '.join(missing)}")

    if not payload["magnet_url"].startswith("magnet:?xt=urn:btih:"):
        raise ValueError("invalid magnet URL")

def build_session(site=None):
    session = requests.Session()
    session.headers.update(
        {
        "User-Agent": (

            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/149.0.0.0 Safari/537.36"
        ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Upgrade-Insecure-Requests": "1",
        }
    )

    if site == "sehuatang":
        session.headers["Referer"] = "https://www.sehuatang.org/"
        session.headers["Host"] = "www.sehuatang.org"
        session.headers["Accept-Language"] = "zh-CN,zh;q=0.9,en;q=0.8"
    elif site == "hjd2048":
        session.headers["Referer"] = "https://hjd2048.com/2048/"
    elif site == "141love":
        session.headers["Referer"] = "https://141love.net/"

    if site == "141love":
        cookie = os.getenv("cookie1", "").strip()
    elif site == "hjd2048":
        cookie = os.getenv("HJD2048_COOKIE", "").strip()
    elif site == "sehuatang":
        cookie = os.getenv("cookie2", "").strip()
    else:
        cookie = os.getenv("cookie1", "").strip()

    if cookie:
        session.headers["Cookie"] = cookie

    return session

def fetch_html(session, url):
    response = session.get(url, timeout=30)
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    return response.text

def fetch_html_with_browser(url):
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        page = context.new_page()

        page.goto(url, wait_until="domcontentloaded", timeout=120000)
        if sys.stdin.isatty():
            input("If Cloudflare/18 page appears, click through it, then press Enter here...")

        html = page.content()
        page.close()
        return html

def extract_thread_links(html):
    soup = BeautifulSoup(html, "html.parser")
    threads = {}

    for row in soup.select("tr"):
        if "typeid=557" not in str(row):
            continue

        for link in row.select("a[href]"):
            href = link.get("href", "")
            match = THREAD_PATTERN.search(href)
            title = link.get_text(" ", strip=True)

            if not match or not title or title in {"New", "0", "1", "2", "3"}:
                continue

            thread_id = match.group(1)
            threads.setdefault(
                thread_id,
                {
                    "thread_id": thread_id,
                    "title": title,
                    "url": urljoin(SOURCE_URL, href),
                },
            )

    return list(threads.values())

def extract_first_image(soup, thread_url):
    for image in soup.select("img[src]"):
        src = image.get("src", "")
        if src and not any(word in src.lower() for word in ("logo", "avatar", "smilie")):
            return urljoin(thread_url, src)
    return ""
    
def download_image(session, image_url, thread_id, referer_url=""):
    if not image_url:
        return ""

    if "thumb-ing.gif" in image_url:
        return ""

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    parsed = urlparse(image_url)
    ext = Path(parsed.path).suffix.lower()

    if ext not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        ext = ".jpg"

    file_path = IMAGE_DIR / f"{thread_id}{ext}"

    try:
        response = session.get(
            image_url,
            timeout=30,
            headers={
                "User-Agent": session.headers.get("User-Agent", ""),
                "Referer": referer_url or "https://www.sehuatang.org/",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            },
        )
        response.raise_for_status()
    except requests.RequestException as error:
        print(f"Could not download image {image_url}: {error}")
        return ""

    with open(file_path, "wb") as f:
        f.write(response.content)

    return str(file_path)

def download_image_with_browser(image_url, thread_id, referer_url=""):
    if not image_url:
        return ""

    if "thumb-ing.gif" in image_url:
        return ""

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    parsed = urlparse(image_url)
    ext = Path(parsed.path).suffix.lower()

    if ext not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        ext = ".jpg"

    file_path = IMAGE_DIR / f"{thread_id}{ext}"

    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]
            page = context.new_page()

            if referer_url:
                page.goto(referer_url, wait_until="networkidle", timeout=120000)
                if sys.stdin.isatty():
                    input("If Cloudflare/18 page appears, click through it, then press Enter here...")
                response = page.request.get(
                    image_url,
                    headers={
                        "Referer": referer_url,
                        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                    },
                    timeout=120000,
                )

                if not response.ok:
                    print(f"Could not download image {image_url}: browser status {response.status}")
                    page.close()
                    return ""

                file_path.write_bytes(response.body())
                page.close()
                return str(file_path)

    except Exception as error:
        print(f"Could not download image {image_url}: {error}")
        return ""

def extract_magnet(html):
    match = MAGNET_PATTERN.search(html)
    if match:
        return match.group(0).replace("&amp;", "&")

    text = BeautifulSoup(html, "html.parser").get_text(" ")

    match = MAGNET_PATTERN.search(text)
    if match:
        return match.group(0).replace("&amp;", "&")

    info_hash = INFO_HASH_PATTERN.search(text)
    if info_hash:
        return f"magnet:?xt=urn:btih:{info_hash.group(1).lower()}"

    return ""


def extract_size(text):
    match = SIZE_PATTERN.search(text)
    if not match:
        return 0

    value = float(match.group(1))
    multipliers = {
        "B": 1,
        "K": 1024,
        "KB": 1024,
        "M": 1024**2,
        "MB": 1024**2,
        "G": 1024**3,
        "GB": 1024**3,
        "T": 1024**4,
        "TB": 1024**4,
    }
    return int(value * multipliers[match.group(2).upper()])

def extract_maker(title):
    ignored_keywords = (
        "BT下载",
        "BT下載",
        "中文字幕",
        "外挂",
        "外掛",
        "MP4",
        "高清",
        "无码",
        "有码",
        "三级",
        "港台",
    )

    for match in MAKER_PATTERN.finditer(title):
        maker = match.group(1).strip()

        if not maker:
            continue

        if any(word in maker for word in ignored_keywords):
            continue

        if re.search(r"\d+(?:\.\d+)?[GMK]B?", maker, re.IGNORECASE):
            continue

        return maker

    return ""

def extract_publish_time(soup):
    html = str(soup)

    match = re.search(
        r"\d{4}-\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2}:\d{2}",
        html,
    )

    if not match:
        print("No publish time found")
        return int(datetime.now().timestamp())

    return int(
        datetime.strptime(
            match.group(0),
            "%Y-%m-%d %H:%M:%S",
        ).timestamp()
    )

def torrent_bytes_to_magnet(torrent_bytes):
    data = bencodepy.decode(torrent_bytes)
    info = data[b"info"]
    info_hash = hashlib.sha1(bencodepy.encode(info)).hexdigest()
    return f"magnet:?xt=urn:btih:{info_hash}"


def download_hjd2048_torrent(session, soup, thread_url):
    link = soup.select_one("a[href*='action=download'][href*='aid=']")
    if not link:
        return ""

    torrent_url = urljoin(thread_url, link.get("href"))
    response = session.get(torrent_url, timeout=30)
    response.raise_for_status()
    content = response.content

    if not content.startswith(b"d"):
        return ""

    return torrent_bytes_to_magnet(content)

def extract_hjd2048_publish_time(soup):
    time_element = soup.select_one(".tiptop span[title]")

    if not time_element:
        return int(datetime.now().timestamp())

    date_text = time_element.get("title", "").strip()

    if not date_text:
        return int(datetime.now().timestamp())

    return int(
        datetime.strptime(
            date_text,
            "%Y-%m-%d %H:%M",
        ).timestamp()
    )

def to_public_image_path(local_path):
    if not local_path:
        return ""

    return f"/sehuatang/img/{Path(local_path).name}"

def parse_thread(session, thread, tag=SOURCE_TAG):
    if "sehuatang.org" in thread["url"]:
        html = fetch_html_with_browser(thread["url"])
    else:
        html = fetch_html(session, thread["url"])

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)

    title_element = soup.select_one("#thread_subject")
    page_title = title_element.get_text(strip=True) if title_element else ""

    title = thread.get("title") or page_title
    if not title:
        raise ValueError("could not find thread title")

    if "閱讀權限高於" in text or "用户登录" in text or "用戶登錄" in text:
        raise PermissionError("thread requires an authorized forum account")

    magnet_url = extract_magnet(html)
    if not magnet_url:
        raise ValueError("no magnet URL found")

    post = soup.select_one(".t_f, .pcb, .postmessage")
    content = post.get_text("\n", strip=True) if post else text[:3000]

    images = extract_images(post, thread["url"], limit=1)
    cover_url = images[0] if images else ""

    if "sehuatang.org" in thread["url"]:
        local_cover = download_image_with_browser(cover_url, thread["thread_id"], thread["url"])
        public_cover = to_public_image_path(local_cover)
    else:
        local_cover = download_image(session, cover_url, thread["thread_id"], thread["url"])
        public_cover = to_public_image_path(local_cover)

    return {
        "title": title,
        "tag": tag,
        "magnet_url": magnet_url,
        "filename": thread["thread_id"],
        "actors": "",
        "content": content,
        "thumb": public_cover,
        "cover": public_cover,
        "series": "",
        "publish_time": extract_publish_time(soup),
        "sub_tag": extract_sub_tags(title, content),
        "duration": 0,
        "maker": extract_maker(f"{title} {content}"),
        "collect_page": thread["url"],
        "size": extract_size(content),
    }

def parse_hjd2048_thread(session, thread, tag):
    html = fetch_html(session, thread["url"])
    soup = BeautifulSoup(html, "html.parser")

    title_element = soup.select_one("#subject_tpc")
    if title_element:
        title = title_element.get_text(strip=True)
    elif soup.title:
        title = soup.title.get_text(strip=True).split("|")[0].strip()
    else:
        raise ValueError("could not find hjd2048 thread title")

    post = (
        soup.select_one("div[id^='postmessage_']")
        or soup.select_one("#read_tpc")
        or soup.select_one(".tpc_content")
        or soup.select_one(".t_msgfont")
        or soup.select_one("#td_tpc")
    )

    if not post:
        page_text = soup.get_text("\n", strip=True)
        if "登录" in page_text or "請登錄" in page_text or "请登录" in page_text:
            raise PermissionError("hjd2048 requires login cookie")
        raise ValueError("could not find hjd2048 post content")

    content = post.get_text("\n", strip=True)
    magnet_url = extract_magnet(html)
    if not magnet_url:
        magnet_url = download_hjd2048_torrent(session, soup, thread["url"])

    if not magnet_url:
        raise ValueError("no magnet URL found")

    images = extract_images(post, thread["url"], limit=1)

    if not images:
        images = extract_images(soup, thread["url"], limit=1)

    cover_url = images[0] if images else ""
    local_cover = download_image(session, cover_url, thread["thread_id"])
    public_cover = to_public_image_path(local_cover)

    return {
        "title": title,
        "tag": tag,
        "magnet_url": magnet_url,
        "filename": thread["thread_id"],
        "actors": "",
        "content": content[:10000],
        "thumb": public_cover,
        "cover": public_cover,
        "series": "",
        "publish_time": extract_hjd2048_publish_time(soup),
        "sub_tag": extract_sub_tags(title, content),
        "duration": 0,
        "maker": extract_maker(f"{title} {content}"),
        "collect_page": thread["url"],
        "size": extract_size(content),
    }

def extract_sub_tags(title, content):
    text = f"{title} {content}"
    tags = []

    mappings = {
        "無修正": "无码",
        "无码": "无码",
        "中文字幕": "中文字幕",
        "外挂": "外挂字幕",
        "外掛": "外挂字幕",
        "有码": "有码",
    }

    for keyword, tag in mappings.items():
        if keyword in text and tag not in tags:
            tags.append(tag)

    return ",".join(tags) or "BT下载"

def load_processed():
    if not PROCESSED_FILE.exists():
        return set()
    return set(json.loads(PROCESSED_FILE.read_text(encoding="utf-8")))


def save_processed(processed):
    PROCESSED_FILE.write_text(
        json.dumps(sorted(processed), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

def extract_images(post, thread_url, limit=2):
    images = []

    if not post:
        return images

    for image in post.select("img[src]"):
        src = (
            image.get("data-original")
            or image.get("data-src")
            or image.get("file")
            or image.get("src")
            or ""
        ).strip()
        if not src:
            continue

        lower_src = src.lower()

        if any(word in lower_src for word in (
            "logo",
            "avatar",
            "smilie",
            "face",
            "icon",
            "common",
            "thumb-ing.gif",
            "none.gif",
            "level",
            "torrent.gif",
        )):
            continue

        full_url = urljoin(thread_url, src)

        if full_url in images:
            continue

        images.append(full_url)

        if len(images) >= limit:
            break

    return images

def submit_payload(session, payload):
    response = session.post(API_URL, json=payload, timeout=30)
    response.raise_for_status()

    result = response.json()

    if result.get("code") == 0:
        return result

    if result.get("msg") == "Data already exists":
        return result

    raise RuntimeError(f"API rejected payload: {result}")


def load_stats():
    if not STATS_FILE.exists() or STATS_FILE.stat().st_size == 0:
        return {}

    with STATS_FILE.open("r", encoding="utf-8") as stats_file:
        return json.load(stats_file)


def save_stats(stats):
    STATS_FILE.parent.mkdir(parents=True, exist_ok=True)

    with STATS_FILE.open("w", encoding="utf-8") as stats_file:
        json.dump(stats, stats_file, ensure_ascii=False, indent=2)


def record_stat(stats, site, status):
    today = datetime.now().strftime("%Y-%m-%d")
    day_stats = stats.setdefault(
        today,
        {
            "total": 0,
            "success": 0,
            "duplicate": 0,
            "failed": 0,
            "by_source": {},
        },
    )
    source_stats = day_stats["by_source"].setdefault(
        site,
        {
            "total": 0,
            "success": 0,
            "duplicate": 0,
            "failed": 0,
        },
    )

    if status not in {"success", "duplicate", "failed"}:
        status = "failed"

    day_stats["total"] += 1
    day_stats[status] += 1
    source_stats["total"] += 1
    source_stats[status] += 1


def get_result_status(result):
    if result.get("code") == 0:
        return "success"

    if result.get("msg") == "Data already exists":
        return "duplicate"

    return "failed"


def print_daily_summary(stats):
    today_key = datetime.now().strftime("%Y-%m-%d")
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    day_stats = stats.get(today_key, {"total": 0, "success": 0, "duplicate": 0, "failed": 0, "by_source": {}})
    lines = [f"\n今日统计 ({now_text})"]
    lines.append("  总计: {total}  成功: {success}  重复: {duplicate}  失败: {failed}".format(**day_stats))

    for site, source_stats in day_stats["by_source"].items():
        lines.append("  [{site}] 总: {total}  成功: {success}  重复: {duplicate}  失败: {failed}".format(site=site, **source_stats))

    summary = "\n".join(lines)
    print(summary)
    return summary


def crawl(limit, submit, stats):
    session = build_session()
    processed = load_processed()
    try:
        listing_html = fetch_html(session, SOURCE_URL)
    except requests.RequestException as error:
        print(f"Could not load listing page: {error}")
        return
    threads = extract_thread_links(listing_html)
    candidates = [thread for thread in threads if thread["thread_id"] not in processed]

    print(f"Found {len(threads)} thread links; checking up to {min(limit, len(candidates))}.")

    for thread in candidates[:limit]:
        try:
            payload = parse_thread(session, thread)
            validate_payload(payload)

            print(f"\nReady: {payload['title']}")
            print(f"Magnet: {payload['magnet_url'][:100]}")

            if submit:
                result = submit_payload(session, payload)
                print(f"API response: {result}")
                record_stat(stats, "141love", get_result_status(result))
                save_stats(stats)
                processed.add(thread["thread_id"])
                save_processed(processed)
            else:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
                record_stat(stats, "141love", "success")
                save_stats(stats)
        except (requests.RequestException, PermissionError, ValueError, RuntimeError) as error:
            print(f"Skipped {thread['url']}: {error}")
            record_stat(stats, "141love", "failed")
            save_stats(stats)

        time.sleep(random.uniform(2, 5))

def log_parsed_payload(payload):
    PARSED_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    records = []

    if PARSED_LOG_FILE.exists() and PARSED_LOG_FILE.stat().st_size > 0:
        with PARSED_LOG_FILE.open("r", encoding="utf-8") as log_file:
            records = json.load(log_file)

    records.append(
        {
            "logged_at": datetime.now().isoformat(timespec="seconds"),
            "payload": payload,
        }
    )

    with PARSED_LOG_FILE.open("w", encoding="utf-8") as log_file:
        json.dump(records, log_file, ensure_ascii=False, indent=2)

def crawl_source(source, limit, submit, stats):
    session = build_session(source["site"])

    try:
        if source["site"] == "sehuatang":
            listing_html = fetch_html_with_browser(source["url"])
        else:
            listing_html = fetch_html(session, source["url"])
    except Exception as error:
        print(f"Could not load listing page {source['url']}: {error}")
        return

    if source["site"] == "141love":
        threads = extract_thread_links(listing_html)
    elif source["site"] == "hjd2048":
        threads = extract_hjd2048_thread_links(listing_html, source["url"])
    elif source["site"] == "sehuatang":
        threads = extract_sehuatang_thread_links(listing_html, source["url"])
    else:
        print(f"Unknown site: {source['site']}")
        return

    print(f"\nSource: {source['site']} | Tag: {source['tag']}")
    print(f"Found {len(threads)} thread links; checking up to {min(limit, len(threads))}.")

    for thread in threads[:limit]:
        try:
            if source["site"] == "hjd2048":
                payload = parse_hjd2048_thread(session, thread, source["tag"])
                log_parsed_payload(payload)
            else:
                payload = parse_thread(session, thread, source["tag"])
                log_parsed_payload(payload)
            validate_payload(payload)

            print(f"\nReady: {payload['title']}")
            print(f"Magnet: {payload['magnet_url']}")

            if submit:
                result = submit_payload(session, payload)
                print(f"API response: {result}")
                record_stat(stats, source["site"], get_result_status(result))
                save_stats(stats)
            else:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
                record_stat(stats, source["site"], "success")
                save_stats(stats)

        except (requests.RequestException, PermissionError, ValueError, RuntimeError) as error:
            print(f"Skipped {thread['url']}: {error}")
            record_stat(stats, source["site"], "failed")
            save_stats(stats)

        time.sleep(random.uniform(2, 5))

def crawl_thread(thread_url, submit, stats):
    match = THREAD_PATTERN.search(thread_url)
    if not match:
        print("Invalid thread URL.")
        return

    session = build_session("141love")
    thread = {
        "thread_id": match.group(1),
        "title": "",
        "url": thread_url,
    }

    try:
        payload = parse_thread(session, thread)
        validate_payload(payload)

        print(f"\nReady: {payload['title']}")
        print(f"Magnet: {payload['magnet_url']}")

        if submit:
            result = submit_payload(session, payload)
            print(f"API response: {result}")
            record_stat(stats, "thread-url", get_result_status(result))
            save_stats(stats)
        else:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            record_stat(stats, "thread-url", "success")
            save_stats(stats)

    except (requests.RequestException, PermissionError, ValueError, RuntimeError) as error:
        print(f"Skipped {thread_url}: {error}")
        record_stat(stats, "thread-url", "failed")
        save_stats(stats)

def extract_hjd2048_thread_links(html, source_url):
    soup = BeautifulSoup(html, "html.parser")
    threads = {}

    skip_titles = (
        "公告",
        "置顶",
        "總置頂",
        "总置顶",
        "版规",
        "規則",
        "地址",
        "发布页",
        "防走失",
    )

    for row in soup.select("tr"):
        row_text = row.get_text(" ", strip=True)

        if any(word in row_text for word in skip_titles):
            continue

        link = row.select_one("a[href*='read.php?tid=']")
        if not link:
            continue

        href = link.get("href", "")
        title = link.get_text(" ", strip=True)

        if not title:
            continue

        match = re.search(r"tid=(\d+)", href)
        if not match:
            continue

        thread_id = match.group(1)
        if int(thread_id) < 20000000:
            continue

        threads.setdefault(
            thread_id,
            {
                "thread_id": thread_id,
                "title": title,
                "url": urljoin(source_url, href),
            },
        )

    return list(threads.values())

def extract_sehuatang_thread_links(html, source_url):
    soup = BeautifulSoup(html, "html.parser")
    threads = {}

    for link in soup.select("tbody[id^='normalthread_'] a.xst[href]"):
        href = link.get("href", "")
        title = link.get_text(" ", strip=True)

        if not title:
            continue

        match = (
            re.search(r"thread-(\d+)-\d+-\d+\.html", href)
            or re.search(r"(?:viewthread\.php\?tid=|tid=)(\d+)", href)
        )
        if not match:
            continue

        thread_id = match.group(1)

        threads.setdefault(
            thread_id,
            {
                "thread_id": thread_id,
                "title": title,
                "url": urljoin(source_url, href),
            },
        )

    return list(threads.values())

def main():
    parser = argparse.ArgumentParser(description="Crawl authorized 141love BT threads.")
    parser.add_argument("--limit", type=int, default=3, help="maximum threads to inspect")
    parser.add_argument(
        "--submit",
        action="store_true",
        help="submit records to the local insertCili API; default is dry-run",
    )
    parser.add_argument(
    "--thread-url",
    help="preview or submit one specific thread URL",
    )
    parser.add_argument(
    "--all-sources",
    action="store_true",
    help="crawl all configured source URLs",
    )
    args = parser.parse_args()
    stats = load_stats()

    if args.thread_url:
        crawl_thread(args.thread_url, args.submit, stats)
    elif args.all_sources:
        for source in SOURCES:
            crawl_source(source, args.limit, args.submit, stats)
    else:
        crawl(max(args.limit, 1), args.submit, stats)

    summary = print_daily_summary(stats)
    send_telegram(summary)

if __name__ == "__main__":
        main()

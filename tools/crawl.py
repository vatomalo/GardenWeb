"""Export Garden Restaurant's public WordPress pages and front-end assets."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from html import unescape
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
from time import monotonic, sleep
from urllib.error import HTTPError
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree
from hashlib import sha256

from lxml import html

BASE = "https://www.gardenrestaurant.no/"
MAIN = {"gardenrestaurant.no", "www.gardenrestaurant.no"}
ASSET_HOSTS = MAIN | {"www-static.gardenrestaurant.no"}
ASSET_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".ico", ".avif", ".mp4", ".webm",
             ".css", ".js", ".woff", ".woff2", ".eot", ".ttf", ".pdf"}
LIVE = {"/cart/", "/checkout/", "/my-account/", "/wp-login.php"}
MAP = "https://maps.google.com/maps?q=Storgata%202%2C%203611%20Kongsberg&output=embed"
CSS_URL = re.compile(r"""url\(\s*(?P<quote>['"]?)(?P<url>[^'")]+)(?P=quote)\s*\)""", re.I)
MAX_SIZE = 28 * 1024 * 1024
MAX_PAGES = 100
MAX_ASSETS = 1200
CACHE = None
NEXT_REQUEST = 0.0


def absolute(base, target):
    target = unescape(target.strip())
    raw = urlsplit(urljoin(base, target))
    if raw.scheme not in ("http", "https") or raw.username or raw.password:
        return ""
    return urlunsplit(("https", raw.netloc, quote(unquote(raw.path) or "/", safe="/!$&'()*+,;=:@-._~"),
                       raw.query, ""))


def page_url(base, value):
    address = absolute(base, value)
    if not address:
        return ""
    u = urlsplit(address)
    if (u.hostname not in MAIN or u.query or u.path.startswith(("/wp-", "/feed/", "/comments/feed/"))
            or u.path in LIVE or PurePosixPath(u.path).suffix):
        return ""
    path = u.path.rstrip("/") + "/"
    return urljoin(BASE, path)


def asset_url(base, target):
    if target.lstrip().startswith(("data:", "#")):
        return ""
    address = absolute(base, target)
    u = urlsplit(address)
    if (u.hostname in ASSET_HOSTS and PurePosixPath(u.path).suffix.lower() in ASSET_EXT
            and "/wp-admin/" not in u.path):
        # Static file query strings only select versions on this site.
        return urlunsplit(("https", u.netloc, u.path, "", ""))
    return ""


def fetch(url):
    global NEXT_REQUEST
    key = sha256(url.encode()).hexdigest()
    record = CACHE / (key + ".json") if CACHE else None
    body_file = CACHE / (key + ".body") if CACHE else None
    if record and record.is_file() and body_file.is_file():
        return (body_file.read_bytes(), json.loads(record.read_text())["mime"]), None

    for attempt in range(3):
        sleep(max(0, NEXT_REQUEST - monotonic()))
        NEXT_REQUEST = monotonic() + 1.05
        try:
            with urlopen(Request(url, headers={"User-Agent": "GardenRestaurant public source export/1.0"}),
                         timeout=12) as response:
                target = urlsplit(response.url)
                if target.hostname not in ASSET_HOSTS:
                    return None, f"Redirected outside the public restaurant site ({target.hostname})"
                body = response.read(MAX_SIZE + 1)
                if len(body) > MAX_SIZE:
                    return None, "Asset exceeds 28 MiB"
                mime = response.headers.get_content_type()
                if record:
                    body_file.write_bytes(body)
                    record.write_text(json.dumps({"mime": mime}))
                return (body, mime), None
        except HTTPError as exc:
            if exc.code != 429 or attempt == 2:
                return None, str(exc)
            retry_after = exc.headers.get("Retry-After") or ""
            pause = max(35, int(retry_after)) if retry_after.isdecimal() else 35
            if pause > 180:
                return None, f"HTTP 429; Retry-After requests {pause}s"
            print(f"Origin rate limited the export. Waiting {pause}s per request policy.", flush=True)
            NEXT_REQUEST = monotonic() + pause
        except OSError as exc:
            return None, str(exc)


def locations(url):
    obj, err = fetch(url)
    if err:
        raise RuntimeError(err)
    return [item.text for item in ElementTree.fromstring(obj[0]).findall(".//{*}loc")]


def page_path(url):
    return unquote(urlsplit(url).path).lstrip("/") + "index.html"


def asset_path(url):
    u = urlsplit(url)
    pieces = []
    for segment in unquote(u.path).split("/"):
        if segment in ("", ".", ".."):
            continue
        clean = re.sub(r'[<>:"\\|?*\x00-\x1f]', "_", segment).rstrip(". ")
        pieces.append(clean or "_")
    if len(pieces[-1]) > 115:
        tail = PurePosixPath(pieces[-1]).suffix
        pieces[-1] = pieces[-1][:75] + "-" + sha256(url.encode()).hexdigest()[:14] + tail
    return "/".join(("_assets", u.hostname, *pieces))


def css_targets(body):
    for match in CSS_URL.finditer(body):
        yield match["url"].strip()


def refs(doc):
    for el in doc.iter():
        if not isinstance(el.tag, str):
            continue
        for k in ("href", "src", "data-src", "data-lazy-src", "poster", "data-thumb", "data-bg", "data-orig-src"):
            value = el.get(k)
            if value:
                yield value
        for k in ("srcset", "data-srcset", "data-lazy-srcset"):
            value = el.get(k)
            if value and not value.lstrip().startswith("data:"):
                for item in value.split(","):
                    words = item.strip().split()
                    if words:
                        yield words[0]
        if el.tag == "style" and el.text:
            yield from css_targets(el.text)
        if el.get("style"):
            yield from css_targets(el.get("style"))


def link_from(here, there):
    return quote(posixpath.relpath(there, posixpath.dirname(here) or "."), safe="/-._~")


def rewrite_css(content, base, here, assets):
    def replace(match):
        target = assets.get(asset_url(base, match["url"]))
        return f"url('{link_from(here, target)}')" if target else match.group()
    return CSS_URL.sub(replace, content)


def rewrite(doc, url, here, pages, assets):
    def rewrite_ref(value, can_page):
        if "maps/embed/v1/" in value and "key=" in value:
            return MAP
        target = assets.get(asset_url(url, value))
        if can_page and not target and not value.startswith("#"):
            target = pages.get(page_url(url, value))
        if target:
            fragment = urlsplit(value).fragment
            return link_from(here, target) + (f"#{fragment}" if fragment else "")
        if value.startswith("/") and not value.startswith("//"):
            return urljoin(url, value)
        return value

    for el in doc.iter():
        if not isinstance(el.tag, str):
            continue
        for key in list(el.attrib):
            if "nonce" in key.lower() or key.lower() == "data-api-key":
                del el.attrib[key]
        for key in ("href", "src", "data-src", "data-lazy-src", "poster", "data-thumb", "data-bg", "data-orig-src"):
            value = el.get(key)
            if value and not (el.tag == "link" and el.get("rel") == "canonical"):
                el.set(key, rewrite_ref(value, key == "href" and el.tag == "a"))
        for key in ("srcset", "data-srcset", "data-lazy-srcset"):
            value = el.get(key)
            if value and not value.lstrip().startswith("data:"):
                entries = [item.strip().split() for item in value.split(",") if item.strip()]
                el.set(key, ", ".join(" ".join([rewrite_ref(parts[0], False), *parts[1:]])
                                      for parts in entries))
        if el.tag == "style" and el.text:
            el.text = rewrite_css(el.text, url, here, assets)
        if el.get("style"):
            el.set("style", rewrite_css(el.get("style"), url, here, assets))
        if el.tag == "script" and el.text:
            el.text = re.sub(r"""(?i)(["']?[\w-]*(?:nonce|api_key|apikey)["']?\s*[:=]\s*)(["'])[^"']+\2""",
                             r"\1\2\2", el.text)
            el.text = re.sub(r"AIza[0-9A-Za-z_-]{30,}", "", el.text)
        if el.tag == "form":
            method = el.get("method", "get").lower()
            if method != "get":
                el.set("action", "#")
                el.set("onsubmit", "return false;")
            else:
                el.set("action", urljoin(url, el.get("action") or url))
        if el.tag == "input" and "nonce" in (el.get("name") or "").lower():
            el.set("value", "")


def main():
    global CACHE
    arg = argparse.ArgumentParser(description=__doc__)
    arg.add_argument("destination", type=Path)
    arg.add_argument("--cache", type=Path)
    args = arg.parse_args()
    CACHE = args.cache
    if CACHE:
        CACHE.mkdir(parents=True, exist_ok=True)
    root = args.destination
    pages, assets, docs, css, failures = {}, {}, {}, {}, {}
    pending = {BASE}
    for sitemap in locations(urljoin(BASE, "wp-sitemap.xml")):
        pending.update(page for url in locations(sitemap) if (page := page_url(BASE, url)))
    skipped = [urljoin(BASE, path) for path in sorted(LIVE)]
    asset_queue = set()
    with ThreadPoolExecutor(max_workers=1) as pool:
        while pending and len(docs) < MAX_PAGES:
            batch = sorted(pending)[:MAX_PAGES - len(docs)]
            pending.clear()
            for url, (result, err) in zip(batch, pool.map(fetch, batch)):
                if err:
                    failures[url] = err
                    continue
                body, mime = result
                if mime != "text/html":
                    continue
                doc = html.fromstring(body, parser=html.HTMLParser(encoding="utf-8"))
                docs[url], pages[url] = doc, page_path(url)
                for node in doc.xpath("//a[@href]"):
                    node_url = page_url(url, node.get("href"))
                    if node_url and node_url not in docs and node_url not in failures:
                        pending.add(node_url)
                asset_queue.update(asset for target in refs(doc) if (asset := asset_url(url, target)))
            pending.difference_update(docs, failures)
            print(f"Pages collected: {len(docs)}", flush=True)

        while asset_queue and len(assets) < MAX_ASSETS:
            batch = sorted(asset_queue)[:MAX_ASSETS - len(assets)]
            asset_queue.clear()
            for url, (result, err) in zip(batch, pool.map(fetch, batch)):
                if err:
                    failures[url] = err
                    continue
                raw, mime = result
                if mime == "text/html":
                    failures[url] = "Expected an asset but received HTML"
                    continue
                filename = asset_path(url)
                assets[url] = filename
                output = root / filename
                output.parent.mkdir(parents=True, exist_ok=True)
                if output.suffix.lower() == ".css":
                    content = raw.decode("utf-8", "replace")
                    css[url] = content
                    asset_queue.update(asset for target in css_targets(content)
                                       if (asset := asset_url(url, target)))
                else:
                    output.write_bytes(raw)
            asset_queue.difference_update(assets, failures)
            print(f"Assets collected: {len(assets)}", flush=True)

    for url, content in css.items():
        here = assets[url]
        (root / here).write_text(rewrite_css(content, url, here, assets), encoding="utf-8")
    for url, doc in docs.items():
        here = pages[url]
        rewrite(doc, url, here, pages, assets)
        output = root / here
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(html.tostring(doc, encoding="utf-8", doctype="<!doctype html>"))
    manifest = {"domain": BASE, "pages": pages, "assets": assets, "not_archived": skipped,
                "failed": failures}
    (root / "crawl-manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Exported {len(pages)} pages and {len(assets)} assets; {len(failures)} unavailable URLs")


if __name__ == "__main__":
    main()

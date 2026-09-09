from __future__ import annotations

import re
import ssl
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin
from urllib.request import Request, urlopen

import certifi


@dataclass(frozen=True)
class Location:
    name: str
    address: str
    city: str
    state: str
    zip: str
    care_offerings: list[str]
    source_url: str

    def as_dict(self) -> dict:
        return asdict(self)


class _Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((" ".join("".join(self._text).split()), self._href))
            self._href = None


def _get(url: str) -> str:
    req = Request(url, headers={"User-Agent": "OwnershipOS/1.0 (+assessment)"})
    context = ssl.create_default_context(cafile=certifi.where())
    with urlopen(req, timeout=20, context=context) as response:
        return response.read().decode("utf-8")


def _strip(fragment: str) -> str:
    return unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fragment)).strip())


def scrape_locations(base_url: str) -> tuple[list[dict], list[str]]:
    """Scrape every paginated community and return records plus warnings."""
    home_html = _get(base_url.rstrip("/") + "/")
    home_total_match = re.search(r"serve\s+(\d+)\s+communities", home_html, re.I)
    home_total = int(home_total_match.group(1)) if home_total_match else None
    directory = urljoin(base_url.rstrip("/") + "/", "communities")
    detail_urls: dict[str, str] = {}
    page = 1
    declared_total: int | None = None
    while True:
        url = directory if page == 1 else f"{directory}?page={page}"
        html = _get(url)
        if declared_total is None:
            m = re.search(r"(\d+)\s+communities listed", html, re.I)
            declared_total = int(m.group(1)) if m else None
        parser = _Parser(); parser.feed(html)
        for text, href in parser.links:
            if href.startswith("/communities/"):
                detail_urls[urljoin(base_url, href)] = text
        next_link = any("next" in text.lower() for text, _ in parser.links)
        if not next_link:
            break
        page += 1
        if page > 20:
            raise RuntimeError("Pagination safety limit exceeded")

    def parse_detail(url: str) -> dict:
        html = _get(url)
        name_m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.I | re.S)
        address_m = re.search(r"<dt>Address</dt>\s*<dd>(.*?)</dd>", html, re.I | re.S)
        care_m = re.search(r"<dt>Care Offerings</dt>\s*<dd>(.*?)</dd>", html, re.I | re.S)
        if not name_m or not address_m:
            raise ValueError(f"Missing required fields at {url}")
        raw_address = re.sub(r"<br\s*/?>", "\n", address_m.group(1), flags=re.I)
        parts = [_strip(x) for x in raw_address.split("\n") if _strip(x)]
        locality = re.match(r"(.+),\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)$", parts[-1])
        if len(parts) < 2 or not locality:
            raise ValueError(f"Unrecognized address at {url}: {parts}")
        care = re.findall(r'class="badge"[^>]*>(.*?)</span>', care_m.group(1) if care_m else "", re.I | re.S)
        return Location(
            name=_strip(name_m.group(1)), address=" ".join(parts[:-1]),
            city=locality.group(1).strip(), state=locality.group(2), zip=locality.group(3),
            care_offerings=[_strip(x) for x in care], source_url=url,
        ).as_dict()

    # Pages are independent; a small pool keeps daily scans fast and respectful.
    with ThreadPoolExecutor(max_workers=6) as pool:
        locations = list(pool.map(parse_detail, sorted(detail_urls)))
    warnings = []
    if declared_total is not None and declared_total != len(locations):
        warnings.append(f"Directory declared {declared_total} locations but {len(locations)} detail pages were scraped.")
    if home_total is not None and home_total != len(locations):
        warnings.append(f"Homepage claims {home_total} communities while the directory exposes {len(locations)}; no CRM action is inferred from marketing copy alone.")
    return locations, warnings

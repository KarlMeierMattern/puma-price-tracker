import html
import json
import re
from typing import Any, Optional

from bs4 import BeautifulSoup

from models import PriceQuote
from scrapers.http import fetch


def _parse_availability(value: Any) -> Optional[bool]:
    if value is None:
        return None
    text = str(value).lower()
    if "instock" in text.replace(" ", ""):
        return True
    if "outofstock" in text.replace(" ", ""):
        return False
    return None


def _products_from_ld(data: Any) -> list[dict]:
    if isinstance(data, list):
        items: list[dict] = []
        for entry in data:
            items.extend(_products_from_ld(entry))
        return items
    if not isinstance(data, dict):
        return []
    if data.get("@type") == "Product":
        return [data]
    if "@graph" in data:
        return _products_from_ld(data["@graph"])
    return []


def _first_offer(product: dict) -> dict:
    offers = product.get("offers") or {}
    if isinstance(offers, list):
        return offers[0] if offers else {}
    return offers


def sku_matches_color(sku: str, style: str, color_code: str) -> bool:
    normalized = sku.replace("-", "_").strip().lower()
    if not normalized:
        return False
    return bool(
        re.search(
            rf"{re.escape(style)}[_/\-]?{re.escape(color_code)}(?:[^0-9]|$)",
            normalized,
        )
    )


def color_matched(product_cfg: dict, html_text: str, sku: str = "", color: str = "") -> bool:
    if product_cfg.get("color_verified"):
        return True

    style = product_cfg["style"]
    color_code = product_cfg["color_code"]

    if sku_matches_color(sku, style, color_code):
        return True

    blob = " ".join(part for part in [color, html_text[:50000]] if part).lower()
    if re.search(rf"{re.escape(style)}[/\-_]{color_code}(?:[^0-9]|$)", blob):
        return True
    if f"/{style}/{color_code}/" in blob:
        return True

    keywords = product_cfg.get("color_keywords") or []
    return all(keyword.lower() in blob for keyword in keywords)


def scrape(retailer: dict, product_cfg: dict) -> PriceQuote:
    quote = PriceQuote(
        retailer_id=retailer["id"],
        retailer_name=retailer["name"],
        url=retailer["url"],
        price=None,
        color_verified=bool(retailer.get("color_verified")),
    )

    html_text = fetch(retailer["url"])
    if not html_text:
        quote.error = "Could not fetch page"
        return quote

    soup = BeautifulSoup(html_text, "lxml")
    product: Optional[dict] = None

    for script in soup.select('script[type="application/ld+json"]'):
        if not script.string:
            continue
        try:
            data = json.loads(script.string)
        except json.JSONDecodeError:
            continue
        for candidate in _products_from_ld(data):
            product = candidate
            break
        if product:
            break

    if not product:
        quote.error = "No Product JSON-LD found"
        return quote

    offer = _first_offer(product)
    price = offer.get("price")
    if price is None:
        quote.error = "No price in JSON-LD"
        return quote

    quote.product_name = html.unescape(str(product.get("name") or ""))
    quote.sku = str(product.get("sku") or "")
    quote.color = str(product.get("color") or "")
    quote.price = float(price)
    quote.currency = str(offer.get("priceCurrency") or product_cfg.get("currency") or "ZAR")
    quote.in_stock = _parse_availability(offer.get("availability"))
    quote.color_matched = color_matched(product_cfg, html_text, quote.sku, quote.color)
    return quote

import json
import re
from typing import Any, Optional

from bs4 import BeautifulSoup

from models import PriceQuote
from scrapers.http import fetch
from scrapers.json_ld import (
    _first_offer,
    _parse_availability,
    _products_from_ld,
    color_matched,
    sku_matches_color,
)


def _variants_from_page(html_text: str) -> list[dict]:
    match = re.search(
        r'"variants"\s*:\s*(\[.*?\])\s*,\s*"(?:media|images|options)"',
        html_text,
        re.S,
    )
    if not match:
        return []
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return []


def _pick_variant(variants: list[dict], style: str, color_code: Optional[str]) -> Optional[dict]:
    if color_code:
        for variant in variants:
            sku = str(variant.get("sku") or "")
            if sku_matches_color(sku, style, color_code):
                return variant
        return None
    available = [v for v in variants if v.get("available")]
    pool = available or variants
    if not pool:
        return None

    def price_cents(variant: dict) -> float:
        raw = variant.get("price")
        if raw is None:
            return 1e12
        value = float(raw)
        return value / 100 if value > 1000 else value

    return min(pool, key=price_cents)


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
    color_code = retailer.get("match_sku_suffix") or product_cfg.get("color_code")
    variants = _variants_from_page(html_text)
    chosen = _pick_variant(variants, product_cfg["style"], color_code)

    if chosen:
        raw_price = float(chosen.get("price") or 0)
        quote.price = raw_price / 100 if raw_price > 1000 else raw_price
        quote.sku = str(chosen.get("sku") or "")
        quote.in_stock = bool(chosen.get("available"))
        quote.product_name = str(chosen.get("name") or "")
        if not quote.product_name:
            title = soup.find("h1")
            quote.product_name = title.get_text(strip=True) if title else ""
    else:
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
            quote.error = "No Shopify variant or JSON-LD product found"
            return quote

        offer = _first_offer(product)
        price = offer.get("price")
        if price is None:
            quote.error = "No price found"
            return quote

        quote.product_name = str(product.get("name") or "")
        quote.sku = str(product.get("sku") or "")
        quote.color = str(product.get("color") or "")
        quote.price = float(price)
        quote.in_stock = _parse_availability(offer.get("availability"))

        if color_code and not sku_matches_color(quote.sku, product_cfg["style"], color_code):
            quote.error = f"SKU {quote.sku} does not match colour code {color_code}"
            quote.price = None
            return quote

    quote.color_matched = color_matched(product_cfg, html_text, quote.sku, quote.color, retailer)
    return quote

import html
import json
import re
from typing import Optional

from bs4 import BeautifulSoup

from models import PriceQuote
from scrapers.http import fetch
from scrapers.json_ld import color_matched, sku_matches_color


def _decode_variations(html_text: str) -> list[dict]:
    match = re.search(
        r'data-product_variations="(\[.*?\])"',
        html_text,
        re.S,
    )
    if not match:
        return []
    raw = html.unescape(match.group(1))
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def _pick_variation(variations: list[dict], style: str, color_code: Optional[str]) -> Optional[dict]:
    if color_code:
        for variation in variations:
            sku = str(variation.get("sku") or "")
            if sku_matches_color(sku, style, color_code):
                return variation
        return None
    in_stock = [v for v in variations if v.get("is_in_stock")]
    pool = in_stock or variations
    if not pool:
        return None
    return min(pool, key=lambda v: float(v.get("display_price") or 1e12))


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
    title = soup.find("h1")
    quote.product_name = title.get_text(strip=True) if title else ""

    variations = _decode_variations(html_text)
    color_code = retailer.get("match_sku_suffix")
    chosen = _pick_variation(variations, product_cfg["style"], color_code)

    if chosen:
        quote.price = float(chosen.get("display_price"))
        quote.sku = str(chosen.get("sku") or "")
        quote.in_stock = bool(chosen.get("is_in_stock"))
    else:
        amount = soup.select_one("p.price .woocommerce-Price-amount")
        if not amount:
            quote.error = "No WooCommerce price found"
            return quote
        digits = re.sub(r"[^\d.]", "", amount.get_text())
        quote.price = float(digits)

    quote.color_matched = color_matched(product_cfg, html_text, quote.sku, quote.color)
    return quote

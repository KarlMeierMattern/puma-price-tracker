"""Send price-drop alerts via Resend."""

import logging
import os
from typing import Iterable

import requests

from models import PriceQuote

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


def _fmt_price(price: int) -> str:
    return f"R {price:,}".replace(",", "\u202f")


def _quote_row(quote: PriceQuote, msrp: int) -> str:
    saving = msrp - (quote.price_int or msrp)
    stock = (
        "In stock"
        if quote.in_stock is True
        else "Out of stock"
        if quote.in_stock is False
        else "Stock unknown"
    )
    color_note = (
        "Confirmed colour"
        if quote.color_matched
        else "Colour not confirmed on page — check before buying"
    )
    return f"""
    <tr>
      <td style="padding:12px 0;border-bottom:1px solid #eee;vertical-align:top">
        <strong><a href="{quote.url}" style="color:#111;text-decoration:none">{quote.retailer_name}</a></strong><br/>
        <span style="font-size:22px;font-weight:700;color:#0b6623">{_fmt_price(quote.price_int or 0)}</span>
        &nbsp; <span style="color:#666">(save {_fmt_price(saving)})</span><br/>
        <span style="color:#555">{stock}</span> &nbsp;|&nbsp; {color_note}<br/>
        <span style="font-size:13px;color:#777">{quote.product_name}</span>
      </td>
    </tr>"""


def send_alert(product_cfg: dict, quotes: Iterable[PriceQuote]) -> None:
    api_key = os.environ.get("RESEND_API_KEY")
    from_email = os.environ.get("FROM_EMAIL")
    to_email = os.environ.get("TO_EMAIL")

    if not all([api_key, from_email, to_email]):
        raise RuntimeError("Set RESEND_API_KEY, FROM_EMAIL, and TO_EMAIL")

    quotes = list(quotes)
    threshold = product_cfg.get("alert_threshold", product_cfg.get("retail_price", 0))
    msrp = product_cfg.get("msrp", threshold)
    product_name = product_cfg["name"]
    rows = "".join(_quote_row(q, msrp) for q in quotes)
    cheapest = min(q.price_int or threshold for q in quotes)

    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:640px;margin:0 auto;color:#222">
      <h1 style="font-size:20px">Price drop: {product_name}</h1>
      <p>Your alert threshold is {_fmt_price(threshold)} (PUMA full price is {_fmt_price(msrp)}). These listings are below your target now.</p>
      <p><strong>Best price found:</strong> {_fmt_price(cheapest)}</p>
      <table style="width:100%;border-collapse:collapse">{rows}</table>
      <p style="font-size:12px;color:#888;margin-top:24px">
        Prices and stock change quickly. Open the link and confirm size and colour before you buy.
      </p>
    </div>
    """

    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": f"Price alert: {product_name} from {_fmt_price(cheapest)}",
        "html": html_body,
    }

    response = requests.post(
        RESEND_API_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=20,
    )
    if response.status_code >= 400:
        logger.error("Resend error %s: %s", response.status_code, response.text)
        response.raise_for_status()

    logger.info("Alert email sent to %s", to_email)

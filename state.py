"""Track last alerted prices so we only email on new drops."""

import json
from pathlib import Path

STATE_FILE = Path(__file__).parent / "state" / "prices.json"


def load() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"last_alerted": {}, "last_seen": {}}


def save(data: dict) -> None:
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(data, indent=2))


def should_alert(retailer_id: str, price: int, data: dict) -> bool:
    previous = data.get("last_alerted", {}).get(retailer_id)
    return previous != price


def record_run(quotes, alerts, data: dict) -> None:
    last_seen = data.setdefault("last_seen", {})
    for quote in quotes:
        if quote.ok:
            last_seen[quote.retailer_id] = {
                "price": quote.price_int,
                "url": quote.url,
                "color_matched": quote.color_matched,
            }

    last_alerted = data.setdefault("last_alerted", {})
    for quote in alerts:
        if quote.price_int is not None:
            last_alerted[quote.retailer_id] = quote.price_int

    save(data)

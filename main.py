#!/usr/bin/env python3
"""
Puma Deviate NITRO 4 price tracker for South African retailers.

Run:
  python main.py               # check prices, email on new drops
  python main.py --dry-run     # print all quotes, no email
"""

import argparse
import logging
import sys

import yaml
from dotenv import load_dotenv

load_dotenv()

import emailer
import state
from models import PriceQuote
from scrapers import SCRAPERS

logger = logging.getLogger(__name__)


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as handle:
        return yaml.safe_load(handle)


def scrape_all(config: dict) -> list[PriceQuote]:
    product_cfg = config["product"]
    quotes: list[PriceQuote] = []

    for retailer in config.get("retailers", []):
        scraper_name = retailer.get("scraper", "json_ld")
        scraper = SCRAPERS.get(scraper_name)
        if not scraper:
            logger.warning("Unknown scraper %s for %s", scraper_name, retailer["id"])
            continue

        logger.info("Checking %s...", retailer["name"])
        quote = scraper(retailer, product_cfg)
        quotes.append(quote)
        if quote.ok:
            logger.info(
                "%s: R%s (%s)",
                retailer["name"],
                quote.price_int,
                "colour matched" if quote.color_matched else "colour unverified",
            )
        else:
            logger.warning("%s: %s", retailer["name"], quote.error)

    return quotes


def pick_alerts(quotes: list[PriceQuote], config: dict, data: dict) -> list[PriceQuote]:
    retail_price = config["product"]["retail_price"]
    color_required = config.get("color_match_required", True)
    alerts: list[PriceQuote] = []

    for quote in quotes:
        if not quote.ok or quote.price_int is None:
            continue
        if quote.price_int >= retail_price:
            continue
        if color_required and not quote.color_matched:
            continue
        if state.should_alert(quote.retailer_id, quote.price_int, data):
            alerts.append(quote)

    return alerts


def print_report(quotes: list[PriceQuote], config: dict) -> None:
    retail_price = config["product"]["retail_price"]
    print(f"\n{config['product']['name']}")
    print(f"Retail target: R{retail_price:,}".replace(",", " "))
    print("-" * 72)

    for quote in quotes:
        if quote.ok:
            flag = "SALE" if quote.price_int is not None and quote.price_int < retail_price else "    "
            colour = "matched" if quote.color_matched else "unverified"
            stock = (
                "in stock"
                if quote.in_stock is True
                else "out of stock"
                if quote.in_stock is False
                else "stock ?"
            )
            print(
                f"[{flag}] {quote.retailer_name:22} R{quote.price_int:>5}  {colour:10}  {stock:11}  {quote.url}"
            )
        else:
            print(f"[ERR] {quote.retailer_name:22} {'—':>5}  {'—':10}  {'—':11}  {quote.error}")


def run(config: dict, dry_run: bool = False) -> int:
    quotes = scrape_all(config)
    data = state.load()
    alerts = pick_alerts(quotes, config, data)

    print_report(quotes, config)

    if dry_run:
        if alerts:
            print(f"\nWould email {len(alerts)} alert(s).")
        return 0

    if alerts:
        emailer.send_alert(config["product"], alerts)

    state.record_run(quotes, alerts, data)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Track Puma Deviate NITRO 4 prices in South Africa")
    parser.add_argument("--dry-run", action="store_true", help="Print quotes only; do not email")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    try:
        config = load_config(args.config)
    except OSError as exc:
        logger.error("Could not read config: %s", exc)
        sys.exit(1)

    sys.exit(run(config, dry_run=args.dry_run))


if __name__ == "__main__":
    main()

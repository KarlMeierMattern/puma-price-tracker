# Puma Deviate NITRO 4 price tracker (South Africa)

Checks a curated list of South African retailers for the **Slate Sky / Moody Gray** colourway (style `312123`, colour code `30`) and emails you when the price drops below **R3,500** (PUMA full price is R3,999).

This follows the same pattern as `projects/deceased-estates`: Python scrapers, Resend email alerts, and a GitHub Actions schedule.

## Why a scraper?

South Africa does not have a single price-comparison site that reliably tracks every sports retailer. A small scheduled scraper with a configurable retailer list is the most dependable way to catch short sales on PUMA, Shelflife, specialist running shops, and any other store you add later.

You cannot realistically scrape *every* `.co.za` site. Start with known product pages in `config.yaml` and add more as you find them.

## Run locally

```sh
cd projects/puma-price-tracker
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # add your Resend keys

python main.py --dry-run    # print current prices
python main.py              # email on new drops below R3,500
```

## Configuration

Edit `config.yaml`:

- `product.alert_threshold` — email when price is below this (currently `3500`)
- `product.msrp` — PUMA full price, used for savings in emails (`3999`)
- `color_match_required` — when `true`, only alert if the page looks like the Slate Sky colourway
- `retailers` — add any SA product URL; use `scraper: json_ld` for most shops

Supported scrapers:

| Scraper       | Use for                                      |
|---------------|----------------------------------------------|
| `json_ld`     | Most sites (PUMA, Shelflife, etc.)           |
| `woocommerce` | WordPress/WooCommerce shops like Run-A-Way     |
| `shopify`     | Shopify stores like Durban Runner            |

For Shopify stores with multiple colours on one page, set `match_sku_suffix: "30"`.

## Schedule

GitHub Actions runs twice daily at **06:00 and 18:00 SAST**. Set these secrets in the repo:

- `RESEND_API_KEY`
- `FROM_EMAIL`
- `TO_EMAIL`

## Current retailers

| Store            | Notes                                              |
|------------------|----------------------------------------------------|
| PUMA South Africa| Exact colour URL; full price R3,999                |
| Shelflife        | Style on page; colour not always labelled          |
| Run-A-Way Sport  | R3,899 when checked; colour not confirmed on page  |
| Durban Runner    | Multiple colours; filtered to SKU suffix `30`      |

## Limitations

- Retailers change their HTML; a scraper may need a tweak after a site redesign.
- A low price on an unverified colour page is shown in `--dry-run` but will not trigger an email while `color_match_required: true`.
- Stock levels are best-effort; always confirm on the site before buying.

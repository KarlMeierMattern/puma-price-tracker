from scrapers import json_ld, shopify, woocommerce

SCRAPERS = {
    "json_ld": json_ld.scrape,
    "woocommerce": woocommerce.scrape,
    "shopify": shopify.scrape,
}

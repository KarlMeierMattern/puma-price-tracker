from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PriceQuote:
    retailer_id: str
    retailer_name: str
    url: str
    price: Optional[float]
    currency: str = "ZAR"
    in_stock: Optional[bool] = None
    product_name: str = ""
    sku: str = ""
    color: str = ""
    color_matched: bool = False
    color_verified: bool = False
    error: str = ""

    @property
    def price_int(self) -> Optional[int]:
        if self.price is None:
            return None
        return int(round(self.price))

    @property
    def ok(self) -> bool:
        return self.price is not None and not self.error

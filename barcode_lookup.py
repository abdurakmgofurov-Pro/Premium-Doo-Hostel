# Looks up a product's name by its GTIN barcode in Open Food Facts
# (https://world.openfoodfacts.org), a free, keyless, open product database.
# Used by the "Yangi mahsulot qo'shish" / "Tovar kirimi" barcode scan flows
# in app.py to auto-fill the product name field.
import requests

_API_URL = "https://world.openfoodfacts.org/api/v2/product/{code}.json"
_FIELDS = "product_name,product_name_ru,brands,quantity"
# Open Food Facts blocks requests without a descriptive User-Agent (returns 403).
_HEADERS = {"User-Agent": "PremiumDooHostelFinance/1.0 (abdurakmgofurov@gmail.com)"}


def lookup_product_name(code: str) -> str | None:
    code = (code or "").strip()
    if not code.isdigit():
        return None
    try:
        resp = requests.get(_API_URL.format(code=code), params={"fields": _FIELDS}, headers=_HEADERS, timeout=3)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None
    if data.get("status") != 1:
        return None
    product = data.get("product") or {}
    name = (product.get("product_name_ru") or product.get("product_name") or "").strip()
    if not name:
        return None
    brand = (product.get("brands") or "").split(",")[0].strip()
    if brand and brand.lower() not in name.lower():
        name = f"{brand} {name}"
    qty = (product.get("quantity") or "").strip()
    if qty and qty.lower() not in name.lower():
        name = f"{name} {qty}"
    return name[:200]

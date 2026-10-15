#!/usr/bin/env python3
"""
Bygger en produktkatalog for Meta (Facebook/Instagram-katalogannonser) ur
Abicarts Google-produktfeed – samma FEED_URL som build_local_inventory.py.

Meta laser samma kolumnnamn som Google (id, title, description, availability,
condition, price, sale_price, link, image_link, brand ...), sa vi stadar bara
upp raderna och filtrerar bort det som inte ska annonseras:

  * rader utan bild, lank, titel eller pris
  * slutsalt som inte gar att bestalla (out of stock)
  * pris 0 / platshallarpriser under MIN_PRICE

Extrapriset (sale_price) behalls sa att annonsen visar samma pris som
produktsidan. Utfil: meta_catalog.tsv (TSV, UTF-8). Meta hamtar den via
raw-URL:en pa GitHub (schemalagd hamtning i Commerce Manager).

Miljovariabler:
  FEED_URL     Abicarts feed-URL (obligatorisk)
  OUTPUT       utfil (default: meta_catalog.tsv)
  MIN_PRICE    lagsta pris i SEK for att tas med (default: 50)
"""

import os
import re
import sys

from build_local_inventory import fetch, strip_q  # noqa: E402


def parse_tsv_table(text):
    """Hela Google-TSV:n som lista av dictar (alla kolumner)."""
    lines = text.split(chr(10))
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        return [], []
    header = [strip_q(c) for c in lines[0].rstrip(chr(13)).split(chr(9))]
    rows = []
    for line in lines[1:]:
        line = line.rstrip(chr(13))
        if not line.strip():
            continue
        cells = line.split(chr(9))
        if len(cells) != len(header):
            continue
        rows.append({h: strip_q(cells[i]) for i, h in enumerate(header)})
    return header, rows


COLUMNS = [
    "id", "title", "description", "availability", "condition", "price",
    "sale_price", "link", "image_link", "additional_image_link", "brand",
    "gtin", "mpn", "google_product_category", "product_type",
    "item_group_id", "custom_label_0", "custom_label_1",
]

AVAIL = {
    "in stock": "in stock", "instock": "in stock", "in_stock": "in stock",
    "limited availability": "in stock",
    "on display to order": "available for order",
    "preorder": "preorder", "pre-order": "preorder",
    "backorder": "available for order",
    "available for order": "available for order",
}


def price_value(s):
    m = re.search(r"([\d\s.,]+)", s or "")
    if not m:
        return 0.0
    v = m.group(1).replace(" ", "").replace(" ", "")
    if "," in v and "." in v:
        v = v.replace(".", "").replace(",", ".")
    else:
        v = v.replace(",", ".")
    try:
        return float(v)
    except ValueError:
        return 0.0


def norm_price(s):
    v = price_value(s)
    return f"{v:.2f} SEK" if v > 0 else ""


def clean(s, n=None):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n] if n else s


def main():
    url = os.environ.get("FEED_URL")
    if not url:
        raise SystemExit("FEL: FEED_URL saknas")
    out = os.environ.get("OUTPUT", "meta_catalog.tsv")
    min_price = float(os.environ.get("MIN_PRICE", "50"))

    text = fetch(url).decode("utf-8", errors="replace")
    if re.search(r"administrators have been notified|Administratörerna har meddelats", text):
        raise SystemExit("FEL: feeden svarade med Abicarts felsida – katalogen skrivs INTE om.")
    header, rows = parse_tsv_table(text)
    if len(rows) < 500:
        # Samma skydd som lagerfeeden: en felsida far inte tomma katalogen.
        raise SystemExit(f"FEL: bara {len(rows)} rader i feeden – avbryter utan att skriva.")

    kept, skipped = [], {}
    def skip(why):
        skipped[why] = skipped.get(why, 0) + 1

    for r in rows:
        g = lambda k: (r.get(k) or "").strip()
        avail_raw = g("availability").lower().replace("_", " ")
        avail = AVAIL.get(avail_raw, "out of stock")
        if avail == "out of stock":
            skip("slutsåld"); continue
        if not g("id") or not g("title") or not g("link") or not g("image_link"):
            skip("saknar id/titel/länk/bild"); continue
        price = norm_price(g("price"))
        if not price or price_value(g("price")) < min_price:
            skip("pris saknas/för lågt"); continue
        sale = norm_price(g("sale_price"))
        if sale and price_value(sale) >= price_value(price):
            sale = ""
        desc = clean(g("description"), 4900) or clean(g("title"))
        kept.append({
            "id": g("id"),
            "title": clean(g("title"), 200),
            "description": desc,
            "availability": avail,
            "condition": (g("condition") or "new").lower(),
            "price": price,
            "sale_price": sale,
            "link": g("link"),
            "image_link": g("image_link"),
            "additional_image_link": g("additional_image_link"),
            "brand": clean(g("brand"), 100) or "Cykel & Natur",
            "gtin": g("gtin"),
            "mpn": g("mpn"),
            "google_product_category": g("google_product_category"),
            "product_type": clean(g("product_type"), 750),
            "item_group_id": g("item_group_id"),
            # Etiketter for produktset i Meta: rea / i butik
            "custom_label_0": "rea" if sale else "",
            "custom_label_1": "i lager" if avail == "in stock" else "beställningsvara",
        })

    def esc(v):
        return (v or "").replace("\t", " ").replace("\r", " ").replace("\n", " ")

    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(COLUMNS) + "\n")
        for k in kept:
            f.write("\t".join(esc(k[c]) for c in COLUMNS) + "\n")

    print(f"Meta-katalog: {len(kept)} produkter skrivna till {out} (av {len(rows)} i feeden)")
    for why, n in sorted(skipped.items(), key=lambda x: -x[1]):
        print(f"  bortfiltrerat – {why}: {n}")
    print(f"  kolumner i Abicart-feeden: {', '.join(header)}")


if __name__ == "__main__":
    main()

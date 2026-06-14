#!/usr/bin/env python3
"""
Bygger en lokal lagerfeed for Google Merchant Center fran Abicarts produktfeed.

Abicart-feeden ar tabbavgransad (TSV) och innehaller redan kolumnerna
id, availability, price, store_code och store_address. Skriptet plockar ut
dessa och skriver en separat lokal lagerfeed (det Google saknar idag).

Mappning (online "omgaende leverans" = i butik i Arsta):
  in_stock / in stock   -> in_stock
  limited availability  -> limited_availability
  on display to order   -> on_display_to_order
  allt annat            -> out_of_stock

Miljovariabler:
  FEED_URL              Abicarts feed-URL (obligatorisk)
  STORE_CODE            reserv om feeden saknar store_code (default: lagerplats_arsta)
  OUTPUT                utdatafil (default: local_inventory.txt)
  INCLUDE_OUT_OF_STOCK  "1" = ta med slutsalda rader (default "1")
"""

import os
import sys
import datetime
import urllib.request

G = "{http://base.google.com/ns/1.0}"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (lokalt-lager-bot; merchant local feed)"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def map_availability(raw):
    if not raw:
        return "out_of_stock"
    v = raw.strip().lower().replace("_", " ")
    if v in ("in stock", "instock"):
        return "in_stock"
    if v == "limited availability":
        return "limited_availability"
    if v == "on display to order":
        return "on_display_to_order"
    return "out_of_stock"


def strip_q(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        s = s[1:-1]
    return s.strip()


def parse_tsv(text):
    """Tabbavgransad parsning. Tabb inuti falt ar i praktiken obefintligt i
    en Google-TSV, sa rak split pa tabb ar saakrare an csv-modulen (som kan
    snubbla pa oescapade citattecken i fritextfaltet description)."""
    lines = text.split("\n")
    # hoppa over ev. inledande tomma rader
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        return []
    header = [strip_q(c) for c in lines[0].split("\t")]
    idx = {name: i for i, name in enumerate(header)}
    needed = ["id", "availability", "price"]
    for n in needed:
        if n not in idx:
            raise SystemExit(f"FEL: kolumnen '{n}' saknas i feeden. Hittade: {header}")
    rows = []
    bad = 0
    for line in lines[1:]:
        if not line.strip():
            continue
        cells = line.split("\t")
        if len(cells) != len(header):
            bad += 1
            continue
        rows.append({name: strip_q(cells[i]) for name, i in idx.items()})
    if bad:
        print(f"  varning: {bad} rader hade fel antal kolumner och hoppades over")
    return rows


def parse_xml(data):
    """Reserv om Abicart nagon gang byter till XML-format."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(data)
    out = []
    for item in root.findall(".//item"):
        def t(*tags):
            for tag in tags:
                el = item.find(tag)
                if el is not None and el.text and el.text.strip():
                    return el.text.strip()
            return ""
        out.append({
            "id": t(f"{G}id", "id"),
            "availability": t(f"{G}availability", "availability"),
            "price": t(f"{G}price", "price"),
            "store_code": t(f"{G}store_code", "store_code"),
        })
    return out


def main():
    feed_url = os.environ.get("FEED_URL")
    fallback_store = os.environ.get("STORE_CODE", "lagerplats_arsta")
    output = os.environ.get("OUTPUT", "local_inventory.txt")
    include_oos = os.environ.get("INCLUDE_OUT_OF_STOCK", "1") == "1"

    if not feed_url:
        print("FEL: satt miljovariabeln FEED_URL.", file=sys.stderr)
        return 2

    print(f"Hamtar feed: {feed_url}")
    data = fetch(feed_url)
    head = data.lstrip()[:64]
    if head.startswith(b"<"):
        records = parse_xml(data)
        print("  format: XML")
    else:
        records = parse_tsv(data.decode("utf-8", errors="replace"))
        print("  format: TSV")

    rows = []
    stats = {"in_stock": 0, "out_of_stock": 0, "limited_availability": 0,
             "on_display_to_order": 0, "saknar_id": 0}

    for r in records:
        item_id = (r.get("id") or "").strip()
        if not item_id:
            stats["saknar_id"] += 1
            continue
        availability = map_availability(r.get("availability"))
        stats[availability] = stats.get(availability, 0) + 1
        if availability == "out_of_stock" and not include_oos:
            continue
        store_code = (r.get("store_code") or "").strip() or fallback_store
        rows.append({
            "store_code": store_code,
            "item_id": item_id,
            "availability": availability,
            "price": (r.get("price") or "").strip(),
        })

    cols = ["store_code", "item_id", "availability", "price"]
    with open(output, "w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(cols) + "\n")
        for r in rows:
            f.write("\t".join(r[c] for c in cols) + "\n")

    ts = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    print(f"[{ts}] Klart. {len(records)} produkter -> {len(rows)} rader till {output}")
    print(f"  i lager: {stats['in_stock']}  slutsalda: {stats['out_of_stock']}"
          f"  begransat: {stats['limited_availability']}"
          f"  utan id: {stats['saknar_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

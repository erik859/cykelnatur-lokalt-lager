#!/usr/bin/env python3
"""
Skickar adresser till Bing Webmaster Tools sa att Bing hamtar dem direkt i
stallet for att vanta pa nasta crawl. Bings index matar aven ChatGPT-sokningen,
sa det ar dar vardet ligger - inte i Bings egen trafikandel.

Varfor inte klassisk IndexNow: IndexNow kraver en nyckelfil pa domanens rot
(https://cykelnatur.se/<nyckel>.txt, serverad som text/plain). Abicart ger oss
inte den ytan - allt vi kan skapa ligger under /produkter/ och levereras som
HTML. URL-inlamning med API-nyckel behover ingen fil och ar darfor vagen som
fungerar sa lange butiken ligger pa Abicart.

  VARNING (last 2026-08-14 i Bing Webmaster Tools): "Legacy SOAP and POX APIs
  will be retired on August 31, 2026." JSON-endpointen nedan tillhor samma
  api.svc-familj. Kor skriptet garna nu, men rakna med att endpointen kan
  behova bytas mot Bings REST-/OAuth-variant efter 31 aug 2026. Nyckeln i sig
  overlever bytet - det ar bara URL:en och auth-headern som andras.

Miljovariabler (lokalt via .env, i CI som Actions-secrets):
  BING_API_KEY  Nyckeln fran Bing Webmaster Tools -> Settings -> API access.
                Genererad 2026-08-14. En nyckel per ANVANDARE, inte per sajt.
  SITE_URL      Verifierad sajt i Bing Webmaster Tools.
                Default: https://cykelnatur.se/
  FEED_URL      Abicarts Google-feed. Anvands bara av --from-feed.

Anvandning:
  python bing_submit.py https://cykelnatur.se/produkter/nagot/ ...
  python bing_submit.py --file urls.txt          (en adress per rad)
  python bing_submit.py --from-feed --limit 100  (link-kolumnen ur Abicart-feeden)
  python bing_submit.py --file urls.txt --dry-run

Bing tar emot max 500 adresser per anrop och har en daglig kvot per sajt
(syns under Settings -> API access). Skriptet delar upp i poster om 100.
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

ENDPOINT = "https://ssl.bing.com/webmaster/api.svc/json/SubmitUrlbatch?apikey={key}"
BATCH = 100
UA = "Mozilla/5.0 (cykelnatur-bing-submit)"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def clean(u: str) -> str:
    """Abicart hanger pa ?twsCurrency=SEK&twsShipmentCountry=SE i feedens
    link-kolumn. De parametrarna ar inte kanoniska adresser - skickar vi in dem
    ber vi Bing indexera en variant av sidan i stallet for sidan."""
    return u.split("?", 1)[0].split("#", 1)[0]


def urls_from_feed(feed_url: str, limit: int):
    """Plockar link-kolumnen ur Abicarts Google-feed (tabbavgransad)."""
    text = fetch(feed_url).decode("utf-8", "replace")
    lines = text.splitlines()
    if not lines:
        return []
    header = lines[0].split("\t")
    try:
        col = header.index("link")
    except ValueError:
        sys.exit("Feeden saknar kolumnen 'link'.")
    out = []
    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) <= col:
            continue
        u = clean(parts[col].strip().strip('"'))
        if u.startswith("http"):
            out.append(u)
        if limit and len(out) >= limit:
            break
    return out


def submit(key: str, site: str, urls, dry_run: bool):
    sent = 0
    for i in range(0, len(urls), BATCH):
        chunk = urls[i:i + BATCH]
        payload = json.dumps({"siteUrl": site, "urlList": chunk}).encode("utf-8")
        if dry_run:
            print(f"[dry-run] skulle skicka {len(chunk)} adresser, forsta: {chunk[0]}")
            sent += len(chunk)
            continue
        req = urllib.request.Request(
            ENDPOINT.format(key=key),
            data=payload,
            headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": UA},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8", "replace")
            print(f"OK {len(chunk)} adresser (HTTP {resp.status}) {body[:200]}")
            sent += len(chunk)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:400]
            sys.exit(f"Bing svarade {e.code}: {detail}")
        except urllib.error.URLError as e:
            sys.exit(f"Naddes inte: {e.reason}")
    return sent


def main():
    ap = argparse.ArgumentParser(description="Skicka adresser till Bing Webmaster Tools.")
    ap.add_argument("urls", nargs="*", help="adresser direkt pa kommandoraden")
    ap.add_argument("--file", help="fil med en adress per rad")
    ap.add_argument("--from-feed", action="store_true", help="las link-kolumnen ur FEED_URL")
    ap.add_argument("--limit", type=int, default=0, help="max antal adresser fran feeden")
    ap.add_argument("--dry-run", action="store_true", help="visa vad som skulle skickas")
    args = ap.parse_args()

    key = os.environ.get("BING_API_KEY", "").strip()
    site = os.environ.get("SITE_URL", "https://cykelnatur.se/").strip()
    if not key and not args.dry_run:
        sys.exit(
            "BING_API_KEY saknas.\n"
            "Hamta den i Bing Webmaster Tools -> kugghjulet -> API access -> Copy API Key\n"
            "och lagg den i .env som BING_API_KEY=... (.env ar gitignorerad)."
        )

    urls = list(args.urls)
    if args.file:
        with open(args.file, encoding="utf-8") as fh:
            urls += [l.strip() for l in fh if l.strip() and not l.startswith("#")]
    if args.from_feed:
        feed = os.environ.get("FEED_URL", "").strip()
        if not feed:
            sys.exit("FEED_URL saknas - kravs for --from-feed.")
        urls += urls_from_feed(feed, args.limit)

    # dedupe, behall ordningen
    seen, uniq = set(), []
    for u in (clean(x) for x in urls):
        if u not in seen:
            seen.add(u)
            uniq.append(u)

    if not uniq:
        sys.exit("Inga adresser att skicka. Ange dem som argument, --file eller --from-feed.")

    print(f"{len(uniq)} unika adresser -> {site}")
    n = submit(key, site, uniq, args.dry_run)
    print(f"Klart: {n} adresser {'simulerade' if args.dry_run else 'inskickade'}.")


if __name__ == "__main__":
    main()

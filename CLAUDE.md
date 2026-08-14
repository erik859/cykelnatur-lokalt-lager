# Lokal lagerfeed (Cykel & Natur Årsta) · Projektkontext för Claude Code

## Snabbfakta

| | |
|---|---|
| **Vad** | Bygger en lokal lagerfeed till Google Merchant Center ur Abicarts produktfeed. `build_local_inventory.py` väljer ut rätt kolumner → `local_inventory.txt` som Google hämtar via schemalagd hämtning. Här bor även `bing_submit.py`, som pingar Bing Webmaster Tools om nya/ändrade adresser (samma `FEED_URL` som indata). |
| **Ägarskap** | Hermodex-internt (för egna butiken Cykel & Natur, cykelnatur.se). |
| **Stack** | Python 3 (endast standardbibliotek). Körs i GitHub Actions (cron) – ingen egen server. |
| **Port** | **Ingen** – batch/CLI-skript, ingen webbserver. |
| **Kör** | `python build_local_inventory.py` (läser miljövariabler, se `.env.example`). CI: `.github/workflows/local-inventory.yml`, schemalagt nattligt 04:15. |
| **Git** | `erik859/cykelnatur-lokalt-lager`. `local_inventory.txt` versionshanteras med flit (raw-URL = live feed mot Google). |
| **Fallgropar** | Gitignorera ALDRIG `local_inventory.txt`. Hemligheter (`FEED_URL` m.fl.) sätts som Actions-secrets i CI, lokalt via `.env`. |

## Miljövariabler

| Variabel | Roll |
|---|---|
| `FEED_URL` | Abicart-produktfeed (TSV/XML). KRÄVS. |
| `STORE_CODE` | Butikskod (`lagerplats_arsta`), reserv om en rad saknar värde. |
| `OUTPUT` | Utfil (default `local_inventory.txt`). |
| `INCLUDE_OUT_OF_STOCK` | `1` = ta med slutsålt, `0` = bara det som finns i butik. |
| `BING_API_KEY` | Bing Webmaster Tools-nyckel (Settings → API access). Bara `bing_submit.py`. |
| `SITE_URL` | Verifierad sajt i Bing (default `https://cykelnatur.se/`). Bara `bing_submit.py`. |

Se `README.md` för full bakgrund (varför skriptet behövs, Merchant Center-koppling, mappning online→butik).

## Status
**Inkopplad och i drift** (verifierat 2026-08-11). Merchant Center-konto 484697722,
kompletterande datakälla `PRODUCTS_INVENTORY_FULL SOURCE 2` av typen "Lokalt
produktlager". Google hämtar filen **00:00 svensk tid** varje dygn; senaste
körningen matchade 2 697 av 2 697 produkter utan anmärkning. Bygget kör därför
23:30 svensk tid — flyttar du cron:en måste den ligga före Googles hämtning,
annars levereras gårdagens saldo.

Känt kvarstående: `price` kopieras rakt av från Abicart-feeden och är
**ordinarie pris**, inte extrapriset. Exempel: Nishiki Rush ligger som 13 995 kr
i feeden medan butiken tar 13 495 kr. Prisavvikelse mot landningssidan kan
underkänna lokala annonser — kolla om Abicart-exporten har ett `sale_price`-fält
att läsa i stället.

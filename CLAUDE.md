# Lokal lagerfeed (Cykel & Natur Årsta) · Projektkontext för Claude Code

## Snabbfakta

| | |
|---|---|
| **Vad** | Bygger en lokal lagerfeed till Google Merchant Center ur Abicarts produktfeed. `build_local_inventory.py` väljer ut rätt kolumner → `local_inventory.txt` som Google hämtar via schemalagd hämtning. |
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

Se `README.md` för full bakgrund (varför skriptet behövs, Merchant Center-koppling, mappning online→butik).

## Status
Kvar: koppla in raw-URL:en som lokal lagerdatakälla i Merchant Center
(Inställningar → Datakällor → lokal lagerdatakälla → schemalagd hämtning).

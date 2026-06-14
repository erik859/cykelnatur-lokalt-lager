# Lokal lagerfeed – Cykel och Naturbutiken Årsta

Automatiserar den lokala lagerfeeden till Google Merchant Center utifrån Abicarts
produktfeed. Skriptet hämtar Abicart-feeden en gång per dygn, plockar ut rätt
kolumner till Googles lokala lagerformat och publicerar en fil som Google hämtar själv.

```
Abicart-feed (TSV) ──► build_local_inventory.py ──► local_inventory.txt ──► Google hämtar (schemalagd hämtning)
  (produkter, har redan        (väljer ut store_code,        (separat lokal lagerfeed)
   store_code & availability)    item_id, availability, pris)
```

## Varför behövs skriptet alls?

Abicart lägger redan in `store_code` (`lagerplats_arsta`), `store_address` och
`availability` i produktfeeden. Men Google läser inte de fälten ur *produktkällan* –
lokalt lager måste komma från en *separat lokal lagerdatakälla*. Dessutom heter
kolumnen `id` i feeden, medan Googles lokala lager kräver att den heter `item_id`.
Skriptet bygger bron: det skapar en ren, minimal lokal lagerfeed med exakt rätt
kolumnnamn. (Värt att fråga Abicarts support om de kan exportera en *färdig* lokal
lagerfeed direkt – då behövs inte ens skriptet. Idag verkar de bara lägga fälten i
produktfeeden, vilket Google inte använder för lokalt lager.)

## Vad som behövs

- **FEED_URL** – er Abicart-feed:
  `https://admin.abicart.se/pricefile/153857/google/sv/SEK/SE`
- **STORE_CODE** – behövs egentligen inte, eftersom feeden redan innehåller
  `lagerplats_arsta`. Den används bara som reserv om en rad skulle sakna värdet.
  Se till att exakt samma butikskod (`lagerplats_arsta`) finns satt på butiken i
  Google Företagsprofil → butiken → Avancerad information → Butikskod.

## Alternativ A – kör i GitHub (gratis, ingen egen server)

1. Skapa ett GitHub-repo med dessa filer (`build_local_inventory.py` + mappen `.github/`).
2. **Settings → Secrets and variables → Actions → New repository secret**:
   - `FEED_URL` = Abicart-URL:en ovan
   - `STORE_CODE` = `lagerplats_arsta`
3. Kör en gång manuellt: **Actions → Bygg lokal lagerfeed → Run workflow**.
   Det skapar `local_inventory.txt` i repot.
4. Filen nås på (byt ut ANVÄNDARE/REPO):
   `https://raw.githubusercontent.com/ANVÄNDARE/REPO/main/local_inventory.txt`
   Därefter körs det automatiskt varje natt 04:15.

## Alternativ B – egen server med cron

```bash
FEED_URL="https://admin.abicart.se/pricefile/153857/google/sv/SEK/SE" \
OUTPUT="/var/www/feeds/local_inventory.txt" \
python3 build_local_inventory.py
```
Crontab för daglig körning 04:15:
```
15 4 * * * FEED_URL="https://admin.abicart.se/pricefile/153857/google/sv/SEK/SE" OUTPUT="/var/www/feeds/local_inventory.txt" /usr/bin/python3 /sökväg/build_local_inventory.py
```
Se till att filen nås via en publik URL.

## Koppla in i Merchant Center

1. **Inställningar → Datakällor → lägg till lokal lagerdatakälla.**
2. Välj **schemalagd hämtning** och peka på URL:en till `local_inventory.txt`.
3. **Språk = svenska**, **samma flödesetikett som produktkällan** (produktkällan
   saknar etikett → lämna tom).
4. Slutför **Lägg till lager** under **Tillägg**.
5. Räkna med upp till 24 timmar för första synken av butik + lager.

## Bra att veta

- Mappning: online "i lager / omgående leverans" → `in_stock` i Årsta. Slutsålt
  och förbeställning → `out_of_stock`. Stämmer med att online-lagret speglar butiken.
- Vill ni bara lista det som faktiskt finns i butik: sätt `INCLUDE_OUT_OF_STOCK=0`,
  då utesluts slutsålda rader helt ur den lokala feeden.
- Google stickprovskontrollerar att butikslagret stämmer för annonser för lokala
  butikslager. Håll kopplingen "online = butik" sann, annars kan programmet pausas.
- Skriptet använder bara Pythons standardbibliotek – inga beroenden att installera.
- Om Abicart byter feeden till XML hanterar skriptet det automatiskt (formatet
  upptäcks vid körning).

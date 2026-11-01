# Golden980 — ZaInstrumentom: доступні джерела цін (01.11.2026)

**Scope:** 313 incumbent ZaInstrumentom SKUs + 32 selection candidates = 345 distinct SKU. No changes to Prom or production main.

## Matching audited today
- Compared exact supplier SKU against 5 previously connected brand price lists: TAJIMA (21.08), TAKAGI (08.2026), OLEJNIK (06.10), ROLLINGDOG (08.2026), Blue Dolphin (10.2026).
- **227/345** SKUs matched a brand source selling/RRP list, **118/345** did not match these files. Non-match does *not* establish supplier unavailability.
- Of 227: **93 TAJIMA, 78 TAKAGI, 44 OLEJNIK, 10 ROLLINGDOG, 2 Blue Dolphin**.
- Blue Dolphin had 2 direct wholesale/buyout source price entries. Their applicability to TALPA's **dropship** settlement and VAT treatment is not verified. Do not insert them into confirmed purchase-cost cells.
- Only **3 of 227** matched source RRP differ from Prom snapshot: 1 current product (SKU `1101-1689`, August source older by UAH 5) and 2 prospective candidates (`012450G`, `1301492_1` with August source higher than current supplier feed). Differences are **not** grounds to manually change supplier-controlled RRP; verify live XML.
- **0/345** SKUs have currently verified exact personalized TALPA dropship procurement price in the available sources.

## Private working file
`TALPA_ZaInstrumentom_Source_Evidence_345_2026-11-01.xlsx` in this conversation contains full 345-row source matching, precise source URLs and price type, RRP divergences, buyout-price provenance and next action. **Do not commit it to this public repository** or treat old wholesale/RRP as current dropship cost.

## Next evidence
Request an up-to-date **TALPA partner dropship purchase price per SKU** from ZaInstrumentom (Excel/CSV), including VAT applicability and discount/cost distinction. Match all 345 SKUs by text SKU with old Prom export and live feed before applying net-margin ranking to 980 current and replacements.

**Safety:** previous 35→35 draft PR #24 remains HOLD; owner has expanded project to full Golden980 optimization. Do not update the main production feed or Prom.

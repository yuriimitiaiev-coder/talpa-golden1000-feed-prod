# Golden980 — ZaInstrumentom: доступні джерела цін (01.11.2026)

**Scope:** 313 incumbent ZaInstrumentom SKUs + 32 selection candidates = 345 distinct SKU. No changes to Prom or production main.

## Matching audited today
- Compared exact supplier SKU against 5 previously connected brand price lists: TAJIMA (21.08), TAKAGI (08.2026), OLEJNIK (06.10), ROLLINGDOG (08.2026), Blue Dolphin (10.2026).
- **227/345** SKUs matched a brand source selling/RRP list, **118/345** did not match these files. Non-match does *not* establish supplier unavailability.
- Of 227: **93 TAJIMA, 78 TAKAGI, 44 OLEJNIK, 10 ROLLINGDOG, 2 Blue Dolphin**.
- Blue Dolphin had 2 direct wholesale/buyout source price entries. Their applicability to TALPA's **dropship** settlement and VAT treatment is not verified. Do not insert them into confirmed purchase-cost cells.
- Only **3 of 227** matched source RRP differ from Prom snapshot: 1 current product (SKU `1101-1689`, August source older by UAH 5) and 2 prospective candidates (`012450G`, `1301492_1` with August source higher than current supplier feed). Differences are **not** grounds to manually change supplier-controlled RRP; verify live XML.
- **0/345** SKUs have currently verified exact per-SKU invoiced dropship procurement cost. This does NOT prevent provisional modelling based on the negotiated average discount (see owner clarification).

## Private working file
`TALPA_ZaInstrumentom_Source_Evidence_345_2026-11-01.xlsx` in this conversation contains full 345-row source matching, precise source URLs and price type, RRP divergences, buyout-price provenance and next action. **Do not commit it to this public repository** or treat old wholesale/RRP as current dropship cost.

## Updated commercial method — owner clarification on 02.11.2026
The owner clarified that **there is NO individualized supplier purchasing price list**. Procurement terms are a **negotiated average percentage discount**; this is a portfolio-level average, not guaranteed for each SKU. The percentage itself and per-SKU scenario values are confidential and retained ONLY in the private working workbook.

Do not request a nonexistent partner procurement spreadsheet again. Instead use the average agreed discount for portfolio *scenario screening*, with sensitivity checks for variation in actual discount and channel costs. Record actual invoiced cost as the authoritative amount **only when a concrete transaction is made**. Confirm exceptional costs only on high-risk or shortlisted SKUs; maintain zero evidence for individually verified procurement amounts unless proven.

Private workbook for scenario analysis: `TALPA_Golden980_SIGMA_Za_25pct_Scenario_2026-11-02.xlsx`. Do not commit its financial data or product-level commercial assumptions to this public repository. This changes no Prom product card, accepted price-setting policy, supplier feed, or production rollout state.

**Safety:** previous 35→35 draft PR #24 remains HOLD; owner has expanded project to full Golden980 optimization. Do not update the main production feed or Prom.

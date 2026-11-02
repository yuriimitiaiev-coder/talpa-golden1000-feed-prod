# TALPA Golden980: portfolio-wide review, phase 2 (01.11.2026)

## Decision and scope
Owner instructed **audit all 980 listings and retain only commercially best items**; this supersedes the earlier 35-for-35 shortlisting. Grand Instrument 35 remains a **confirmed exit**, but production cutover stays **HOLD** pending full portfolio decision. Only SIGMA and ZaInstrumentom are eligible sources; budget ≤1000, target ~980 unless weak positions have no suitable substitutes.

## Materials audited
- Latest completed Prom export `export-products-01-11-26_15-51-04.xlsx` (980 current SKU).
- Previous per-SKU audit `TALPA_Golden980_FULL_REVIEW_PHASE1_2026-11-01.xlsx`.
- GitHub Actions latest complete 722-row filtered alternatives ZIP from run 41317665396, artifact `golden980-grand35-candidates` (722 rows; unlike previous quick log 757, actual downloadable archive count is 722).
- Completed TALPA DMS order aggregate: 24 orders, 20 delivered (2026-07-23 – 2026-10-28), 12 SKUs with completed sales currently listed. **Do not publish individual private order details.**
- Historic supplier-commercial analyses `TALPA_SIGMA_02_економіка.xlsx`, `TALPA_аудит_прайсів_Zainstrumentom_повний_15_файлів_2026-08-06.xlsx`. Historical assumed discounts (27% SIGMA / 25% base Za / 30% TAJIMA) are **NOT authoritative TALPA procurement prices**.

## Findings (model ONLY, not actual profitability)
Of 945 non-Grand current SKUs: 99 modelled <0 UAH, 140 modelled 0-30 UAH, 347 modelled 30-80 UAH, 359 >=80 UAH for a **single-item** ProSale order, subject to **15.1% variable costs and 15 UAH fixed**. 167 current products are priced under 250 UAH, but cheap consumables may perform as add-ons; do not auto-remove.

Most concentrated illustrative weaknesses by group:
- Concrete drill bits/augers: 55 SKU, 34 negative.
- Tool accessories: 94 SKU, 30 negative.
- Cutting/grinding disks: 22 SKU, 12 negative.
- Screwdriver bits: 26 SKU, 9 negative.
Current sales evidence protects 12 completed-order SKU from removal **solely** due to absent higher-level traffic data. Historical purchase costs and product-level Prom impressions/clicks/ProSale conversion are still needed.

## Alternative candidates
- Research snapshot contains 722 previously absent, supplier-available SKUs with supplier RRP, picture and group match flags.
- 53 *profile-screened, supplier-stock-screened, commercially plausible* candidates are shortlisted for further review across different tools/categories; **not approved for upload**.
- Large nominal-margin opportunities in source data included pumps, kitchen knives, unrelated goods and repeated niche variants; these were screened out, not treated as best just because of higher theoretical price margin.
- One-stop prices and source rows should be revalidated at cutover.

## Working artifact
Private conversation spreadsheet `TALPA_Golden980_FULL_PORTFOLIO_REVIEW_PHASE2_2026-11-01.xlsx`: 980 current rows, 722 candidate rows, 53 diversified alternatives, 78 group summaries, editable parameter assumptions, supplier-procurement-cost fields, scenario formulae, and public methodology/source list. This working paper must **not be pushed to public GitHub** because it includes TALPA's product-level sales signals.

## Required for final decisions
1. Verify *current personalized B2B procurement cost for each SKU* (supplier retail XML is **not** that). Do not assume 27/25/30% discounts automatically.
2. If available, ingest SKU-level impressions/clicks/orders/ProSale costs from Prom, with exact aggregation period.
3. Compute net per order (single-item ProSale vs combined basket vs own site), revenue velocity, breadth of need, competition, and supplier-stock reliability.
4. Keep value-driving add-on SKU even when single-item order is low margin; protect proven sales subject to checked profitability.
5. Rank 945 current + eligible alternatives; remove 35 Grand; validate only approved replacements, max 980 active + 20 reserve.
6. After approval, **freeze existing Prom feed schedule temporarily**, remove old cards, add new and export IDs, validate feed, publish to GitHub main, and resume Prom 4-hour import. Draft PR #24 must not be merged before these steps.

**Production:** no catalog or feed changes authorized by this memo.

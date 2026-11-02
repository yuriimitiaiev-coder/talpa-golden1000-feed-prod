# Golden980 — ProSale campaign export + DMS reconciliation (02.11.2026)

Status: **ANALYSIS / HOLD.** The user provided `export-prosale_24-08-2026_22-10-2026.xlsx`, with **92 campaign/day/source records over 60 calendar days**.

Key methodological facts:
- The workbook is a **campaign-level export** for one commission-per-order advertising campaign, with Prom.ua and Bigl.ua split. It contains NO SKU / Prom product UID / product-level impressions, clicks, commission attribution or conversion fields.
- Cross-checked against TALPA DMS completed orders for the **same period**. **14 DMS-delivered orders exactly reconcile with the 14 campaign orders by dates, counts, gross order values and actual ProSale fee totals**. The 3 DMS-canceled orders are excluded by the campaign export.
- **9 of these 14 orders** contain only SKUs still present in the current Golden980; the other 5 have an historical SKU that is absent now or no recorded SKU. Of the 9, one is a two-item order. Protect the nine existing sold SKUs pending actual net economics; investigate, but do NOT automatically restore retired items.
- **Crucial:** DMS has order-specific commission figures, and their totals EXACTLY match the campaign spend. Never use a generic uniform 7.4% CPA when a real order fee is available. Observed per-order CPA percentages vary materially. Low or negative *scenario* net margin on some completed orders signals need for a document-backed purchase cost verification.
- The private report `TALPA_ProSale_DMS_Reconciliation_2026-08-24_to_2026-10-22.xlsx` includes actual 92-row campaign records, 14 DMS order checks, 15 item lines, historical sold-SKU crosswalk, week summaries and editable economic scenario assumptions. **Do not push the workbook, order IDs, actual revenue or granular financial records to this public repository.**
- Scenario gross-to-net uses historic supplier quote as of 01.11.2026 or average agreed ZaInstrumentom discount, plus assumed 6% tax, 1.7% acquiring, 15 UAH per order. This **is NOT actual realized net profit** for Aug-Oct because historical per-order invoice costs, acquiring and processing may differ.
- Next needed data for **demand ranking**: Prom seller analytics **«Детально за товарами»** for the same period or latest full 90 days, by SKU or product UID, including impressions, clicks, order quantities and ProSale spend if available. Never allocate aggregate campaign impressions across 980 SKU or infer poor demand from absent SKU sales alone.

Keep production unchanged: the existing auto-synchronized 980 and draft PR #24 remain HOLD pending complete SKU-based data / final assortment decision.

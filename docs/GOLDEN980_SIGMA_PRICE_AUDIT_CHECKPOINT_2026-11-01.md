# Golden980 — SIGMA B2B procurement source checkpoint (01.11.2026)

**Status:** audit completed in private conversation artifact, not production; no Prom.ua changes and no merges.

The owner supplied the B2B spreadsheet named `Прайс лист 01-11-2026.xlsx`. It contains 6,003 SKU/source product rows. A precise text-SKU join found all **632 current SIGMA products** and all **21 shortlisted SIGMA alternatives**, hence **653/653 matched**. This includes five SKUs with suffix `z`; never coerce SKUs to integer or drop suffixes.

Commercial data were taken from the B2B spreadsheet's `Ціна` column M and compared with its `РРЦ` column O and with Prom's 01.11.2026 15:51 exported selling price. The exact VAT treatment and whether column M is final invoice amount for TALPA must still be confirmed; **do not mark them as legally verified procurement costs until then**.

**73 supplier-RRP / Prom-price discrepancies:** 66 among current 632 cards, 7 among 21 alternatives. Recheck whether the supplier's main RRP XML feed has actually changed before any pricing concern is closed. Under the existing historical variable cost scenario, 118/632 existing SIGMA items would have a negative *single-item ProSale scenario* at the sampled Prom price. This is not a measured financial loss and not by itself a reason to delist add-on items; channel-specific actual fees/checkout must be checked.

Private working XLSX generated in the conversation: `TALPA_Golden980_SIGMA_B2B_Economics_653_2026-11-01.xlsx`. It retains all 998 review items: 653 SIGMA with quoted prices and source-row references; 345 ZaInstrumentom still require current partner procurement quotes. New sheets include audit 653, discrepancy 73, and summary. **Do not place private B2B price files, per-SKU procurement costs or financial data in this public GitHub repository.**

Next: get 345 ZaInstrumentom procurement quotes; verify Prom RRP discrepancies against live feeds; evaluate basket sales and documented purchasing economics; rank current 980 against qualified alternatives. Grand 35 exit decision remains in force. Full cutover remains HOLD until the replacement set is economically approved and Prom card IDs are safely migrated.

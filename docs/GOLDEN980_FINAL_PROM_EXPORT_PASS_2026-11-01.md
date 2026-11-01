# Golden980 — post-binding audit PASS (01.11.2026, 15:25 Europe/Kyiv)

## Sources
- Original Prom export: `export-products-01-11-26_11-43-55.xlsx`
- After 1-SKU pilot: `export-products-01-11-26_15-16-14.xlsx`
- After remaining 122: `export-products-01-11-26_15-25-32.xlsx`

## Confirmed via complete comparisons (980 rows × 129 product columns)
- All three exports have **980** unique SKU, **980** unique internal Prom UIDs.
- Same SKU/UID pairing in all three exports; no added or removed products.
- External product IDs: baseline **857** populated; pilot **858**; final **980**.
- The final **980 external IDs are unique**. Exactly **123 external ID cells changed** baseline → final; exactly **122** pilot → final.
- The new external IDs for the 123 SKU equal their corresponding unchanged Prom UIDs, matching staged Golden980 XML identities.
- **Zero other product-cell changes** across the 129-column product export, including retail prices, stock quantities, availability, names and descriptions.
- Exported group-sheet data differs in **one image URL** for a group named «Монтажні пістолети»; no product group changes. This is outside the 123 product-ID binding changes.

## Generation CI verified in non-production PR
- 980 offered SKUs, 20 spare capacity slots, 632 SIGMA, 313 ZaInstrumentom, 35 Grand Instrument.
- Pull-request feed generator and validation pass; price tests and stock-monitor tests pass.
- Grand Instrument prices sourced from the live provider XML `<price>` in Golden980 mode.
- For SIGMA and Grand, quantity 1=available, 0=unavailable when supplier feed lacks exact stock units. ZaInstrumentom uses feed quantity.
- No custom TALPA automated repricing. Provider feeds supply selling/RRP price and availability.

## Production rollout constraints
1. Deploy new Golden980 via the existing GitHub pipeline to the **unchanged** URL `https://yuriimitiaiev-coder.github.io/talpa-golden1000-feed-prod/golden1000.xml`; inspect successful published output.
2. On Prom import UI, configure the **existing** URL to update **price, availability, quantity only**, every 4h. Do not alter names, descriptions, photos or categories. Keep missing-products status `Залишити без змін`; do not force-replace or import absent products. Do **not** enable `Тільки оновлення` expecting simultaneous field checkboxes (the UI hides those options).
3. Validate post-Prom-import export: exact same 980 SKUs and UIDs, 980 unique external IDs, 0 new cards. Verify supplier-sourced prices and available/quantity after an actual cycle.
4. Supplier field `<price>` for Grand is the active feed value, as audited live (all 35/35 offers present), but the assumption that it is the correct published retail/RRP should be checked against the supplier's terms; do not apply a TALPA markup formula.

This document records results from user-provided XLSX files. It does not itself execute a production deployment or change Prom settings.

# Golden980 — Prom external ID pilot PASS (01.11.2026)

## Verified by comparing actual Prom exports
- Baseline: `export-products-01-11-26_11-43-55.xlsx`, 980 products.
- Post-import: `export-products-01-11-26_15-16-14.xlsx`, 980 products.
- Controlled SKU: `4003021`.
- Internal Prom UID: `3257930946` both before and after.
- External ID `Ідентифікатор_товару`: was blank; **now `3257930946`**.
- Full-row diff across 980 products: **exactly one changed field on exactly one SKU** (`Ідентифікатор_товару` of `4003021`).
- No added or removed SKU, no new duplicate, no change to price, quantity, stock, description or groups in either export.
- Prom report at 15:11 confirmed 1 imported, 1 updated, 0 created. The warning about `Опис укр` was ignorable to ID binding.
- External IDs still blank: **122** (down from 123).

## One-time batch for remaining 122
Created `TALPA_GOLDEN980_BIND_REMAINING_122_2026-11-01.xlsx` from the same five-column format and the verified 123-row preflight, excluding the already successful SKU `4003021`. It contains:
`Код_товару, Назва_позиції, Назва_позиції_укр, Унікальний_ідентифікатор, Ідентифікатор_товару`.

All remaining 122 were rechecked against 15:16 Prom export: SKU, names and internal UID match; proposed external ID equals the existing internal UID; 122 proposed IDs are unique and have no collision with existing external IDs.

**To perform:** use the EXACT same manual import settings as the successful pilot; on the actual Prom UI only `Код товару/Артикул` selected for update, `Оновити примусово` enabled, `Тільки оновлення` disabled, `Залишити без змін` for absent products. This is an observed working combination; never recommend selecting per-field flags while `Тільки оновлення` is enabled, as it hides them.

**After batch:** get a fresh 980-item Prom XLSX; verify 980 SKU and UID unchanged; exactly 122 external ID fields filled with previously verified values, zero other field changes, 0 missing IDs, 0 duplicates. Do not publish 4h feed prior to this PASS.

No GitHub main/Prom automatic import changes are made by this documentation commit.

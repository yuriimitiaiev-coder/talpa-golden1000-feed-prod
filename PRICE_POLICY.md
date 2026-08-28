# TALPA Golden1000 price policy

- SIGMA: import the current real retail price published in the supplier XML.
- ZAINSTRUMENTOM: the regular supplier RRP is the TALPA base selling price.
- ZAINSTRUMENTOM may publish temporary retail promotions below RRP. ZaInstrumentom confirmed that the ordinary OPT/DROP discount does **not** stack on top of such a promotional retail price unless they explicitly announce separate OPT/DROP promotional terms.
- Therefore, when a ZaInstrumentom offer contains a promotional `price` below `oldprice`, TALPA must **not** automatically pass that promotional price through to Prom.ua as its selling base. The production feed restores `oldprice` (regular RRP) into `price` and removes the supplier promotion markers.
- ZAINSTRUMENTOM does not provide a separate universal wholesale price in the feed. TALPA must not calculate purchase cost as `RRP × standard drop discount` for an offer that is currently under a supplier retail promotion. Such offers require separate margin control using the actual promotional OPT/DROP terms; absent explicit terms, do not assume the standard discount stacks.
- If the supplier XML has a lower promotional price but no machine-readable regular RRP/`oldprice`, the case must be treated as requiring manual commercial review rather than silently assuming an RRP.
- TALPA promotional/selling adjustments, when independently approved, are managed separately from supplier promotions.
- Availability and quantity are updated from supplier feeds.
- Any future automated margin calculation must distinguish at minimum: regular RRP, supplier promotional retail price, actual TALPA purchase price, and TALPA selling price.

The feed therefore treats supplier promotions as a separate commercial state, not as a new permanent RRP.

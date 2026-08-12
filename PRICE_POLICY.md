# TALPA Golden1000 price policy

- SIGMA: retail price in Prom is controlled by `fallback_price` from the pool. The supplier XML price is NOT pushed to Prom because it can differ from the public retail price.
- ZAINSTRUMENTOM: price is updated from the supplier feed.
- Availability and quantity are updated from supplier feeds for both suppliers.

This policy is intentionally conservative to protect margin.

# TALPA Golden1000 price policy

- SIGMA: import the current real retail price published in the supplier XML.
- ZAINSTRUMENTOM: import the current real retail price (RRP) published in the supplier XML.
- ZAINSTRUMENTOM does not provide a separate wholesale price in the feed; TALPA's purchase cost is calculated internally from the current RRP and the contractual discount percentage.
- Therefore the ZAINSTRUMENTOM RRP in the feed must always remain current: if the supplier changes RRP, both the Prom.ua base price and TALPA's calculated purchase cost/margin must be recalculated from that new RRP.
- TALPA promotional/selling adjustments, when needed, are managed in Prom.ua through its discount mechanism rather than by replacing the supplier RRP in the feed.
- Availability and quantity are updated from supplier feeds for both suppliers.
- Price increases are not a separate optimization priority at this stage; the feed simply keeps supplier RRP current.

The feed therefore treats the supplier's published retail price as the base Prom.ua price and keeps stock status synchronized automatically.

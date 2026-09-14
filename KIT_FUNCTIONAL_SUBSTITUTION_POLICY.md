# TALPA KIT — Functional Substitution Policy v1.0

Status: APPROVED
Effective date: 2026-09-14
Frozen master source: TALPA_KIT_MASTER_FINAL_v1_0

## 1. Purpose

The frozen MASTER remains the ideal TALPA KIT composition and is not rewritten because of temporary stock problems.

Operational readiness answers a different question: can TALPA execute a real KIT order today without losing the core function of the KIT?

## 2. Readiness states

- MASTER READY — the PRIMARY MASTER SKU is quoteable through the normal approved live supplier channel.
- ORDER READY — the PRIMARY is unavailable, but an approved substitution path can execute the order.
- BLOCKED — neither the PRIMARY nor an approved substitution path can safely execute the order.

## 3. Substitution ladder

Always use the best available level and stop at the first safe level:

- A1 PRIMARY — original MASTER SKU from its normal approved supplier channel.
- A2 SAME SKU / ALTERNATIVE SOURCE — the same MASTER SKU from another verified source.
- B EQUIVALENT — another SKU with the same core function and materially equivalent critical parameters.
- C FUNCTIONAL — technically different product that still performs the core job of the KIT.
- D DEGRADED / CONDITIONAL — acceptable operational compromise; the limitation must be explicit.
- HOLD / BLOCKED — no safe operational coverage.

A2/C/D emergency sourcing does not automatically require permanent inclusion in Golden1000.

For permanent Golden1000 ACTIVE publication, the SKU must also be present in the corresponding live supplier feed or have an already-existing safe fallback card. Website availability alone is sufficient only for an order-execution route, not for automatic feed publication.

## 4. Evaluation fields

Each MASTER substitution decision must state:

- CORE FUNCTION — what job the item must perform in the KIT.
- HARD CONSTRAINTS — characteristics that cannot be lost.
- SOFT CONSTRAINTS — characteristics that may be relaxed.
- MAX SUBSTITUTION LEVEL — highest permissible level A2/B/C/D.
- COVERAGE SKU(S) — one or more approved items used to cover the function.
- LIMITATION / NOTE — explicit compromise, if any.

## 5. Functional rule

Preserve the outcome of the work, not necessarily every implementation detail.

Examples:
- cordless drill -> corded drill may be level C when mobility is not a hard KIT requirement;
- cordless SDS-plus rotary hammer -> corded SDS-plus may be level C when impact drilling is the core function;
- 8 mm drill bit -> 10 mm drill bit is not acceptable when hole diameter is a hard constraint;
- a battery from another ecosystem is not acceptable when compatibility is a hard constraint.

## 6. Composite coverage

One MASTER line may be covered by multiple live SKUs when the combined set preserves the required function. Such coverage must be marked COMPOSITE and every component must be quoteable.

## 7. Source hierarchy

For an incoming order check in this order:

1. A1 — normal approved supplier feed.
2. A2 — same SKU from a verified alternative source.
3. B — equivalent item from an approved/verified source.
4. C — functional substitute.
5. D — degraded/conditional substitute.
6. HOLD/BLOCKED.

Before confirming an A2/C/D order, verify current price, stock, delivery time, and KIT margin.

## 8. Golden1000 rollout rule

For a new substitute that must become a Prom product:

1. activate/create the substitute first;
2. build, validate and deploy;
3. confirm it exists and is available in Prom;
4. only then move the unavailable old SKU to RESERVE;
5. return to the steady state 980 ACTIVE + 20 RESERVE.

Never remove the old card before the replacement has been confirmed in Prom.

## 9. MASTER integrity

TALPA_KIT_MASTER_FINAL_v1_0 is not modified by operational substitutions.
The resolver must distinguish FEED UNAVAILABLE from true ORDER BLOCKED.

## 10. Current decision principle

A missing SKU is not by itself a blocked KIT.
Only loss of the required function after exhausting A1 -> A2 -> B -> C -> D is BLOCKED.

## 11. ACTIVE/RESERVE rule for unavailable MASTER and non-replaceable items

A SKU that is unavailable and has no safe live replacement must not permanently consume one of the 980 ACTIVE publication slots.

- Keep the frozen MASTER definition unchanged.
- Move the unavailable SKU to RESERVE rather than deleting it.
- RESERVE is the controlled holding area for HOLD/BLOCKED MASTER items, unavailable items awaiting stock recovery, and approved return candidates.
- Use the freed ACTIVE slot for an available, validated SKU.
- Maintain the steady-state architecture at 980 ACTIVE + 20 RESERVE.
- If a RESERVED MASTER returns to stock or receives an approved A/B/C/D replacement, it may be promoted back to ACTIVE through the controlled rotation process.
- Moving a MASTER SKU to RESERVE changes only publication state; it does not remove the SKU from the frozen MASTER or cancel its ORDER READY substitution route.


# TALPA KIT — Functional Substitution Policy v1.2

Status: APPROVED
Effective date: 2026-09-24
Frozen MASTER source: TALPA_KIT_MASTER_FINAL_v1_0
Frozen MASTER scope: 99 unique PRIMARY SKU

## 1. Source of Truth

TALPA_KIT_MASTER_FINAL_v1_0 remains the frozen current MASTER for this operational rollout.
Temporary stock problems never rewrite the MASTER.
Any permanent structural MASTER change requires a separately approved new revision.

The earlier repository FINAL v1.1 / 96-SKU implementation is retained as historical work and is not the active MASTER source for this rollout.

## 2. Daily operational objective

100% of MASTER functions should be executable with products that TALPA can actually supply today.
Golden1000 remains exactly 1000 configured SKU and uses the controlled ACTIVE/RESERVE architecture.

## 3. Decision sequence for an unavailable PRIMARY

1. Identify the PRIMARY function in its KIT.
2. Check whether another available MASTER SKU already fully covers the function.
3. If yes, record FUNCTION COVERED / MASTER_DUPLICATE and do not create redundant quantity.
4. If no, find the closest functionally equivalent available item from approved supplier channels.
5. Record temporary coverage only in PRIMARY MASTER SKU -> LIVE SUBSTITUTE logic.
6. Keep the frozen MASTER unchanged.
7. Do not let an unavailable product permanently consume an ACTIVE publication slot if its function can be covered safely.

## 4. Substitution ladder

- A1 PRIMARY — original MASTER SKU in its normal approved live feed.
- A2 SAME SKU / ALTERNATIVE SOURCE — same SKU through a verified source; order route only unless feed-backed for publication.
- B EQUIVALENT — same core function and materially equivalent critical parameters.
- C FUNCTIONAL — different implementation but preserves the required job.
- D DEGRADED / CONDITIONAL — usable compromise with explicit limitation.
- FUNCTION COVERED / MASTER_DUPLICATE — another existing MASTER line already provides the full required function.
- HOLD / BLOCKED — no safe current coverage.

## 5. Publication rule

Website or market availability alone is not sufficient for automatic Golden1000 ACTIVE publication.
A substitute may become an ACTIVE Prom product only when it is verified in an approved live supplier feed (or an already approved safe fallback card) and passes build/validation.

Controlled rollout:
1. activate/create replacement;
2. build and validate;
3. deploy;
4. confirm the replacement exists and is available in Prom;
5. only then demote the unavailable old publication slot;
6. preserve 980 ACTIVE + 20 RESERVE = 1000 configured.

## 6. Approved suppliers for MASTER resolver

Priority for sourcing/audit:
SIGMA / ZaInstrumentom / GPL / TEKNOSEL / Grand Instrument / other approved sources.

The automated KIT resolver currently accepts feed-backed coverage from:
GRANDINSTRUMENT / SIGMA / ZAINSTRUMENTOM.

## 7. Composite coverage

One PRIMARY line may be covered by multiple live SKU only when the combined set preserves the required function.
Every component must be quoteable at the time of the order.

## 8. Hard constraints

Dimensions, interface/compatibility, voltage ecosystem, shank type, required diameter, safety class and other function-critical parameters may not be silently relaxed.
A degraded route must state the limitation explicitly.

## 9. Fail-closed principle

If neither PRIMARY nor an approved live route is quoteable, the resolver returns HOLD/BLOCK.
A missing SKU is not automatically a blocked KIT; loss of function after exhausting safe coverage routes is BLOCKED.

## 10. Change control

Analysis -> decision matrix -> approval -> controlled package -> build/validate -> deploy -> fresh Prom export -> acceptance audit.
Production changes are not made from an unapproved replacement list.

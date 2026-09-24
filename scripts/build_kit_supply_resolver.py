#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS_CSV = ROOT / "sources" / "kit_pricing_skus.csv"
SUBSTITUTES_CSV = ROOT / "sources" / "master_live_substitutes.csv"
OUTPUT_JSON = ROOT / "docs" / "kit_supply_resolver.json"

APPROVED_KIT_SUPPLIERS = {"SIGMA", "ZAINSTRUMENTOM", "GRANDINSTRUMENT"}
ACTIVE_SUBSTITUTE_STATUS = "ACTIVE"


def positive_number(text: str | None) -> float | None:
    raw = (text or "").strip().replace(",", ".")
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def quantity_for(source, available: bool) -> int:
    if not available:
        return 0
    raw = (source.findtext("quantity_in_stock") or "").strip()
    if raw:
        try:
            return max(int(float(raw.replace(",", "."))), 0)
        except ValueError:
            pass
    # 1 means available, but exact quantity is not machine-readable.
    return 1


def price_basis_for(partner: str, sku: str, za_adjusted: set[str]) -> str:
    if partner == "ZAINSTRUMENTOM" and sku in za_adjusted:
        return "REGULAR_RRP_NORMALIZED_FROM_OLDPRICE"
    if partner == "ZAINSTRUMENTOM":
        return "REGULAR_RRP_FROM_LIVE_FEED"
    if partner == "SIGMA":
        return "CURRENT_RETAIL_FROM_LIVE_FEED"
    if partner == "GRANDINSTRUMENT":
        return "RETAIL_RRP_FROM_LIVE_FEED"
    return "UNSUPPORTED_SUPPLIER"


def empty_live_item(partner: str, sku: str, role: str, price_basis: str) -> dict[str, object]:
    return {
        "partner": partner,
        "sku": sku,
        "role": role,
        "name": "",
        "brand": "",
        "source_url": "",
        "found": False,
        "available": False,
        "quantity": 0,
        "rrp": None,
        "currency": "UAH",
        "price_basis": price_basis,
        "quoteable": False,
    }


def load_targets() -> list[dict[str, str]]:
    if not TARGETS_CSV.exists():
        raise SystemExit(f"Missing KIT target list: {TARGETS_CSV}")
    targets: list[dict[str, str]] = []
    seen: set[str] = set()
    with TARGETS_CSV.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"partner", "sku"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise SystemExit(f"{TARGETS_CSV.name} must contain columns: {sorted(required)}")
        for raw in reader:
            partner = (raw.get("partner") or "").strip().upper()
            sku = (raw.get("sku") or "").strip()
            if not partner or not sku:
                continue
            if partner not in APPROVED_KIT_SUPPLIERS:
                raise SystemExit(f"Unsupported KIT primary supplier: {partner}/{sku}")
            if sku in seen:
                raise SystemExit(f"Duplicate PRIMARY MASTER SKU in {TARGETS_CSV.name}: {sku}")
            seen.add(sku)
            targets.append({"partner": partner, "sku": sku})
    if not targets:
        raise SystemExit("KIT target list is empty")
    return targets


def load_substitutions() -> dict[str, dict[str, str]]:
    if not SUBSTITUTES_CSV.exists():
        return {}
    required = {
        "primary_master_sku",
        "master_supplier",
        "live_coverage",
        "coverage_mode",
        "status",
        "as_of",
        "note",
    }
    result: dict[str, dict[str, str]] = {}
    with SUBSTITUTES_CSV.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise SystemExit(f"{SUBSTITUTES_CSV.name} must contain columns: {sorted(required)}")
        for raw in reader:
            row = {key: (value or "").strip() for key, value in raw.items()}
            primary = row["primary_master_sku"]
            if not primary:
                continue
            if primary in result:
                raise SystemExit(f"Duplicate substitution rule for PRIMARY MASTER SKU: {primary}")
            row["master_supplier"] = row["master_supplier"].upper()
            row["status"] = row["status"].upper()
            row["coverage_mode"] = row["coverage_mode"].upper()
            result[primary] = row
    return result


def active_pool_map(pool_rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in pool_rows:
        if (row.get("status") or "").upper() != "ACTIVE":
            continue
        sku = (row.get("sku") or "").strip()
        if not sku:
            continue
        if sku in result:
            raise SystemExit(f"Ambiguous ACTIVE pool SKU: {sku}")
        result[sku] = row
    return result


def live_item(
    partner: str,
    sku: str,
    maps: dict[str, dict],
    za_adjusted: set[str],
    *,
    role: str,
) -> dict[str, object]:
    source_map = maps.get(partner)
    if source_map is None:
        return empty_live_item(partner, sku, role, "UNSUPPORTED_SUPPLIER")
    source = source_map.get(sku)
    if source is None:
        return empty_live_item(partner, sku, role, "MISSING_FROM_LIVE_FEED")
    rrp = positive_number(source.findtext("price"))
    available = source.get("available") == "true"
    quantity = quantity_for(source, available)
    name = (
        (source.findtext("name_ua") or "").strip()
        or (source.findtext("name") or "").strip()
    )
    brand = (source.findtext("vendor") or "").strip()
    source_url = (source.findtext("url") or "").strip()
    return {
        "partner": partner,
        "sku": sku,
        "role": role,
        "name": name,
        "brand": brand,
        "source_url": source_url,
        "found": True,
        "available": available,
        "quantity": quantity,
        "rrp": round(rrp, 2) if rrp is not None else None,
        "currency": (source.findtext("currencyId") or "UAH").strip() or "UAH",
        "price_basis": price_basis_for(partner, sku, za_adjusted),
        "quoteable": bool(available and rrp is not None),
    }


def coverage_skus(raw: str) -> list[str]:
    return [part.strip() for part in raw.split("+") if part.strip()]


def write_kit_supply_resolver(
    *,
    pool_rows: list[dict[str, str]],
    sigma_map,
    za_map,
    grand_map,
    za_adjustments: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    targets = load_targets()
    rules = load_substitutions()
    pool = active_pool_map(pool_rows)
    za_adjusted = {item["sku"] for item in (za_adjustments or [])}
    maps = {
        "SIGMA": sigma_map,
        "ZAINSTRUMENTOM": za_map,
        "GRANDINSTRUMENT": grand_map,
    }
    generated_at = datetime.now(timezone.utc).isoformat()
    items: list[dict[str, object]] = []

    target_skus = {target["sku"] for target in targets}
    unknown_rules = sorted(set(rules) - target_skus)
    if unknown_rules:
        raise SystemExit(
            "Substitution registry references SKU outside frozen KIT target list: "
            + ",".join(unknown_rules)
        )

    for target in targets:
        primary_partner = target["partner"]
        primary_sku = target["sku"]
        primary = live_item(primary_partner, primary_sku, maps, za_adjusted, role="PRIMARY")
        rule = rules.get(primary_sku)

        base: dict[str, object] = {
            "primary_partner": primary_partner,
            "primary_sku": primary_sku,
            "primary": primary,
            "coverage_mode": "PRIMARY",
            "rule_status": "",
            "rule_as_of": "",
            "note": "",
            "resolved_items": [primary],
            "decision": "PRIMARY_OK" if primary["quoteable"] else "HOLD",
            "line_action": "KEEP_PRIMARY" if primary["quoteable"] else "BLOCK",
            "can_quote": bool(primary["quoteable"]),
        }

        # A live PRIMARY always wins. The substitute registry is a fallback only.
        if primary["quoteable"]:
            if rule:
                base["coverage_mode"] = rule["coverage_mode"] or "PRIMARY"
                base["rule_status"] = rule["status"]
                base["rule_as_of"] = rule["as_of"]
                base["note"] = rule["note"]
            items.append(base)
            continue

        if not rule:
            base["note"] = "PRIMARY unavailable/missing and no approved substitution rule"
            items.append(base)
            continue

        if rule["master_supplier"] and rule["master_supplier"] != primary_partner:
            raise SystemExit(
                f"Substitution master supplier mismatch for {primary_sku}: "
                f"target={primary_partner}, rule={rule['master_supplier']}"
            )

        base["coverage_mode"] = rule["coverage_mode"] or "HOLD"
        base["rule_status"] = rule["status"]
        base["rule_as_of"] = rule["as_of"]
        base["note"] = rule["note"]

        if rule["status"] != ACTIVE_SUBSTITUTE_STATUS or not rule["live_coverage"]:
            base["decision"] = "HOLD"
            base["line_action"] = "BLOCK"
            base["can_quote"] = False
            base["resolved_items"] = []
            items.append(base)
            continue

        resolved: list[dict[str, object]] = []
        for coverage_sku in coverage_skus(rule["live_coverage"]):
            pool_row = pool.get(coverage_sku)
            if pool_row is None:
                resolved.append(empty_live_item("", coverage_sku, "SUBSTITUTE", "NOT_ACTIVE_IN_GOLDEN_POOL"))
                continue
            replacement_partner = (pool_row.get("supplier") or "").strip().upper()
            if replacement_partner not in APPROVED_KIT_SUPPLIERS:
                resolved.append(
                    empty_live_item(
                        replacement_partner,
                        coverage_sku,
                        "SUBSTITUTE",
                        "SUPPLIER_NOT_APPROVED_FOR_KIT",
                    )
                )
                continue
            item = live_item(
                replacement_partner,
                coverage_sku,
                maps,
                za_adjusted,
                role="SUBSTITUTE",
            )
            if not item["name"]:
                item["name"] = (pool_row.get("fallback_name") or "").strip()
            resolved.append(item)

        all_quoteable = bool(resolved) and all(bool(item["quoteable"]) for item in resolved)
        if all_quoteable:
            is_duplicate_coverage = rule["coverage_mode"] == "MASTER_DUPLICATE"
            is_composite = len(resolved) > 1 or "COMPOSITE" in rule["coverage_mode"]
            if is_duplicate_coverage:
                base["decision"] = "SUBSTITUTE"
                base["line_action"] = "REQUIRE_EXISTING_COVERAGE"
            elif is_composite:
                base["decision"] = "COMPOSITE"
                base["line_action"] = "REPLACE_COMPOSITE"
            else:
                base["decision"] = "SUBSTITUTE"
                base["line_action"] = "REPLACE_1_TO_1"
            base["can_quote"] = True
        else:
            base["decision"] = "HOLD"
            base["line_action"] = "BLOCK"
            base["can_quote"] = False
        base["resolved_items"] = resolved
        items.append(base)

    decision_counts = {
        decision: sum(1 for item in items if item["decision"] == decision)
        for decision in ("PRIMARY_OK", "SUBSTITUTE", "COMPOSITE", "HOLD")
    }
    line_action_counts = {
        action: sum(1 for item in items if item["line_action"] == action)
        for action in (
            "KEEP_PRIMARY",
            "REPLACE_1_TO_1",
            "REPLACE_COMPOSITE",
            "REQUIRE_EXISTING_COVERAGE",
            "BLOCK",
        )
    }
    payload: dict[str, object] = {
        "schema_version": 1,
        "source_master": "TALPA_KIT_MASTER_FINAL_v1_0",
        "source_substitution_registry": SUBSTITUTES_CSV.name,
        "policy": "APPROVED_SUPPLIERS_ONLY",
        "approved_suppliers": sorted(APPROVED_KIT_SUPPLIERS),
        "generated_at_utc": generated_at,
        "configured_sku_count": len(targets),
        "quoteable_count": sum(bool(item["can_quote"]) for item in items),
        "blocked_count": sum(not bool(item["can_quote"]) for item in items),
        "decision_counts": decision_counts,
        "line_action_counts": line_action_counts,
        "items": items,
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        "KIT_SUPPLY_RESOLVER="
        + json.dumps(
            {
                "configured_sku_count": payload["configured_sku_count"],
                "quoteable_count": payload["quoteable_count"],
                "blocked_count": payload["blocked_count"],
                "decision_counts": decision_counts,
                "line_action_counts": line_action_counts,
            },
            ensure_ascii=False,
        )
    )
    return payload

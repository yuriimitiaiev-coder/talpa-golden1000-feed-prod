"""Build a human-readable, read-only TALPA availability dashboard.

This module renders the stock_monitor.json report as a static HTML page.
It does not change golden1000.xml, stock calculations, or supplier sources.
"""
from __future__ import annotations

from datetime import datetime
from html import escape
from string import Template
from zoneinfo import ZoneInfo

SUPPLIER_LABELS = {
    "SIGMA": "SIGMA",
    "ZAINSTRUMENTOM": "Заінструментом",
    "GRANDINSTRUMENT": "Гранд Інструмент",
    "GPL": "GPL",
    "TEKNOSEL": "TEKNOSEL",
}
CHANGE_TYPES = (
    ("to_unavailable", "Зник із наявності", "bad"),
    ("to_available", "З’явився в наявності", "good"),
    ("quantity_changed", "Змінилася кількість", "neutral"),
    ("missing_from_source", "Артикул відсутній у фіді", "warn"),
    ("mismatched_quantity", "Суперечлива кількість", "warn"),
)
ALERT_LABELS = {
    "NO_MOVEMENT": "Потрібна перевірка динаміки",
    "STOCK_QUANTITY_CONFLICT": "Неузгоджені ознаки наявності",
    "MISSING_SUPPLIER_SKUS": "Артикули відсутні у фіді постачальника",
    "SIGMA_SNAPSHOT_FALLBACK": "SIGMA: використана резервна копія",
    "NO_BASELINE_XML": "Попередній фід недоступний для порівняння",
    "HISTORY_UNAVAILABLE": "Історія ще не накопичена або тимчасово недоступна",
}
STYLE = """
:root{color-scheme:light;font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif;
 --ink:#14293e;--muted:#64748b;--line:#dbe4ed;--wash:#f3f6fa;--paper:#fff;
 --teal:#0c7b68;--amber:#a56512;--red:#b34141}
*{box-sizing:border-box}body{margin:0;background:var(--wash);color:var(--ink);line-height:1.55}
a{color:#175e93}a:hover{text-decoration:underline}.top{background:#132c44;color:white}
.top-inner{max-width:1120px;margin:auto;padding:20px 24px;display:flex;justify-content:space-between;
 align-items:center;gap:16px}.brand{letter-spacing:.12em;font-weight:800;font-size:18px;color:white}
.top a{color:#e0edf5;font-size:14px;text-decoration:none}.top nav{display:flex;flex-wrap:wrap;gap:18px}
.wrap{max-width:1120px;margin:0 auto;padding:34px 24px 64px}
h1{margin:0;font-size:clamp(26px,4vw,37px);letter-spacing:-.035em}h2{margin:0 0 15px;font-size:21px}
.sub{margin:10px 0 24px;color:var(--muted)}.meta{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:25px 0}
.kpi,.panel{background:var(--paper);border:1px solid var(--line);border-radius:14px}
.kpi{padding:22px}.kpi .v{font-size:35px;line-height:1.2;font-weight:750;letter-spacing:-.04em}
.kpi .k{font-size:13px;color:var(--muted);margin-top:8px}.accent{color:var(--teal)}
.panel{padding:24px;margin:18px 0}.panel p{color:var(--muted);margin:0 0 16px}
.pill{display:inline-block;font-size:12px;font-weight:700;letter-spacing:.02em;
 border-radius:20px;padding:5px 11px;background:#e4f5ef;color:#056e57}
.pill.warn{background:#fff0d9;color:#8b550a}.pill.bad{background:#fbe9e9;color:#9e3737}
.note{font-size:13px;color:var(--muted)}.small{font-size:13px}
.table-scroll{width:100%;overflow:auto}.data{width:100%;border-collapse:collapse;font-size:14px;
 min-width:650px}.data th,.data td{padding:13px 11px;text-align:left;border-bottom:1px solid #e7edf3;
 vertical-align:top}.data th{color:var(--muted);font-size:12px;font-weight:650;background:#f8fafc}
.data tr:last-child td{border-bottom:0}.num{text-align:right!important;font-variant-numeric:tabular-nums}
.supplier{font-weight:700;white-space:nowrap}.muted{color:var(--muted)}
.mono{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.grid .panel{margin:0}
.alert{border-left:4px solid #d5a453;border-radius:9px;padding:13px 16px;margin:10px 0;
 background:#fff8ed}.alert.info{border-left-color:#95b6d0;background:#f2f7fc}
.alert strong{display:block}.alert .small{color:#5a6a7e;margin-top:2px}
.empty{padding:22px;color:var(--muted);background:#f8fafc;border-radius:8px}
.footer{color:var(--muted);font-size:12px;margin-top:28px}
@media(max-width:850px){.kpis{grid-template-columns:repeat(2,1fr)}.grid{grid-template-columns:1fr}}
@media(max-width:520px){.top-inner{flex-direction:column;align-items:flex-start}.wrap{padding:24px 15px 45px}
 .kpi{padding:15px}.kpi .v{font-size:29px}.panel{padding:15px}}
"""
PAGE = Template("""<!doctype html>
<html lang="uk">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="1200"><title>TALPA — Контроль наявності</title>
<style>$style</style></head>
<body>
<header class="top"><div class="top-inner">
  <div class="brand">TALPA <span style="font-weight:400;letter-spacing:0;font-size:13px">/ Golden1000</span></div>
  <nav><a href="./">← Головна</a><a href="stock_monitor.json">Журнал JSON</a>
  <a href="golden1000.xml">XML-фід</a><a href="stock.html">Оновити сторінку ↻</a></nav>
</div></header>
<main class="wrap">
 <h1>Контроль наявності</h1>
 <p class="sub">Порівняння опублікованих залишків за постачальниками. Сторінка формується з кожним оновленням Golden1000.</p>
 <div class="meta">$status <span class="note">Дані станом на $timestamp (Київ)</span>
 <span class="note">Автооновлення відкритої сторінки: кожні 20 хв</span></div>
 <section class="kpis" aria-label="Поточні показники">
   <div class="kpi"><div class="v">$active</div><div class="k">Активні SKU</div></div>
   <div class="kpi"><div class="v accent">$available</div><div class="k">У наявності</div></div>
   <div class="kpi"><div class="v">$unavailable</div><div class="k">Відсутні</div></div>
   <div class="kpi"><div class="v">$changes</div><div class="k">Зміни від минулого оновлення</div></div>
 </section>
 <section class="panel"><h2>Постачальники</h2>
   <p>Показані тільки артикули, що входять до активного каталогу TALPA. «Без руху» — кількість поспіль оновлень без змін; після шести потрібна перевірка.</p>
   <div class="table-scroll"><table class="data"><thead><tr><th>Постачальник</th>
     <th class="num">Усього</th><th class="num">Наявні</th><th class="num">Відсутні</th>
     <th class="num">З'явились</th><th class="num">Зникли</th><th class="num">Зміни кількості</th>
     <th class="num">Без руху</th></tr></thead><tbody>$supplier_rows</tbody></table></div>
 </section>
 <div class="grid"><section class="panel"><h2>Попередження</h2>$alerts</section>
 <section class="panel"><h2>Що означають показники</h2>
   <p><strong>Зміни</strong> — переходи «є / немає» або зміни переданої кількості проти минулого опублікованого XML.</p>
   <p><strong>Без руху</strong> — ознака для перевірки, а не підтвердження помилки.</p>
   <p><strong>Важливо:</strong> ця сторінка не перевіряє фізичні склади постачальників та не змінює картки Prom.ua.</p>
 </section></div>
 <section class="panel"><h2>Артикули, що потребують уваги</h2>
   <p>Всі знайдені зміни статусу, кількості або проблеми зі звіркою джерел у поточному оновленні.</p>$change_table
 </section>
 <section class="panel"><h2>Історія оновлень</h2>
 <p>Зберігаються до 42 останніх успішних запусків; на початку історія накопичується поступово.</p>
 <div class="table-scroll"><table class="data"><thead><tr><th>Дата / час (Київ)</th>
 <th class="num">У наявності</th><th class="num">Відсутні</th><th class="num">З'явились</th>
 <th class="num">Зникли</th><th class="num">Зміни кількості</th></tr></thead>
 <tbody>$history_rows</tbody></table></div></section>
 <div class="footer">Контрольна сторінка TALPA / Golden1000 · тільки читання · сформовано $timestamp.</div>
</main></body></html>
""")


def _safe(value):
    return escape(str(value), quote=True)


def _number(value):
    return int(value) if isinstance(value, (int, float)) else 0


def _time(iso):
    try:
        moment = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return moment.astimezone(ZoneInfo("Europe/Kyiv")).strftime("%d.%m.%Y о %H:%M")
    except (ValueError, TypeError):
        return "час невідомий"


def _count(row, key):
    value = row.get(key, [])
    return len(value) if isinstance(value, list) else _number(value)


def render_dashboard(report):
    """Return complete UTF-8 HTML from stock_monitor.json-compatible dictionary."""
    if report.get("schema_version") != 1:
        raise ValueError("Unsupported stock monitor report schema")
    totals = report["totals"]
    suppliers = report.get("by_supplier", {})
    alerts = report.get("alerts", [])
    active = _number(totals.get("active"))
    available = _number(totals.get("available"))
    unavailable = _number(totals.get("unavailable"))
    if active != available + unavailable:
        raise ValueError("Supplier totals are inconsistent")
    changes = sum(_count(totals, key) for key in ("to_available", "to_unavailable", "quantity_changed"))
    major = [a for a in alerts if a.get("type") in {
        "MISSING_SUPPLIER_SKUS", "STOCK_QUANTITY_CONFLICT", "SIGMA_SNAPSHOT_FALLBACK", "NO_MOVEMENT"
    }]
    status = ('<span class="pill warn">Потрібна увага</span>' if major
              else '<span class="pill">Моніторинг працює</span>')

    supplier_rows = []
    change_rows = []
    for supplier in ("SIGMA", "ZAINSTRUMENTOM", "GRANDINSTRUMENT", "GPL", "TEKNOSEL"):
        row = suppliers.get(supplier, {})
        count = _number(row.get("active"))
        if count == 0:
            movement = '<span class="muted">—</span>'
        else:
            streak = _number(row.get("unchanged_runs"))
            tag = ' class="pill warn"' if streak >= 6 else ' class="small muted"'
            movement = f"<span{tag}>{streak}/6</span>"
        label = _safe(SUPPLIER_LABELS.get(supplier, supplier))
        supplier_rows.append(
            f'<tr><td class="supplier">{label}</td><td class="num">{count}</td>'
            f'<td class="num">{_number(row.get("available"))}</td>'
            f'<td class="num">{_number(row.get("unavailable"))}</td>'
            f'<td class="num">{_count(row,"to_available")}</td>'
            f'<td class="num">{_count(row,"to_unavailable")}</td>'
            f'<td class="num">{_count(row,"quantity_changed")}</td>'
            f'<td class="num">{movement}</td></tr>'
        )
        for key, text, flag in CHANGE_TYPES:
            for sku in row.get(key, []):
                change_rows.append(
                    f'<tr><td class="supplier">{label}</td>'
                    f'<td class="mono">{_safe(sku)}</td>'
                    f'<td><span class="pill {flag}">{_safe(text)}</span></td></tr>'
                )
    change_table = ('<div class="table-scroll"><table class="data"><thead><tr>'
                    '<th>Постачальник</th><th>Артикул</th><th>Подія</th></tr></thead><tbody>'
                    + "".join(change_rows) + "</tbody></table></div>") if change_rows else (
                    '<div class="empty">Змін або проблем за артикулами в цьому оновленні немає.</div>')

    alert_rows = []
    for alert in alerts:
        kind = str(alert.get("type", ""))
        supplier = alert.get("supplier")
        name = ALERT_LABELS.get(kind, kind)
        title = name + (f" — {SUPPLIER_LABELS.get(supplier, supplier)}" if supplier else "")
        is_info = kind in {"HISTORY_UNAVAILABLE", "NO_BASELINE_XML"}
        if kind == "HISTORY_UNAVAILABLE":
            note = "Це нормально для першого запуску. Якщо повторюється, перевірте доступність журналу."
        elif kind == "NO_MOVEMENT":
            note = f"Без змін у {_number(alert.get('runs'))} послідовних оновленнях."
        elif kind == "SIGMA_SNAPSHOT_FALLBACK":
            note = "Актуальний фід SIGMA недоступний; потрібна перевірка свіжості залишків."
        else:
            note = "Перевірте показані нижче артикули або джерело даних."
        alert_rows.append(
            f'<div class="alert{" info" if is_info else ""}"><strong>{_safe(title)}</strong>'
            f'<div class="small">{_safe(note)}</div></div>'
        )
    if not alert_rows:
        alert_rows.append('<div class="empty">Критичних сигналів моніторингу немає.</div>')

    history_rows = []
    for item in reversed(report.get("history", [])):
        records = item.get("suppliers", {})
        sums = {key: sum(_count(v, key) for v in records.values() if isinstance(v, dict))
                for key in ("available", "unavailable", "to_available", "to_unavailable", "quantity_changed")}
        history_rows.append(
            '<tr><td>' + _safe(_time(item.get("generated_at_utc"))) + '</td>'
            + ''.join(f'<td class="num">{sums[key]}</td>' for key in
                       ("available", "unavailable", "to_available", "to_unavailable", "quantity_changed"))
            + '</tr>'
        )
    if not history_rows:
        history_rows = ['<tr><td colspan="6" class="muted">Історія ще не накопичена.</td></tr>']

    return PAGE.substitute(
        style=STYLE,
        status=status,
        timestamp=_safe(_time(report.get("generated_at_utc"))),
        active=active,
        available=available,
        unavailable=unavailable,
        changes=changes,
        supplier_rows="".join(supplier_rows),
        alerts="".join(alert_rows),
        change_table=change_table,
        history_rows="".join(history_rows),
    )

"""
generate_html.py — Generate docs/index.html from scraped data
Usage: python generate_html.py
       python generate_html.py --data data.json   (use existing JSON)
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

# ─── helpers ──────────────────────────────────
def fmt(val, decimals=0):
    """Format number with Thai locale commas."""
    if val is None:
        return "N/A"
    try:
        v = float(val)
        if decimals == 0:
            return f"{int(round(v)):,}"
        return f"{v:,.{decimals}f}"
    except (TypeError, ValueError):
        return str(val)

def pill(text, kind="st"):
    classes = {"up":"pill-up", "dn":"pill-dn", "st":"pill-st", "na":"pill-na"}
    c = classes.get(kind, "pill-st")
    return f'<span class="pill {c}">{text}</span>'

def badge(text, kind="ok"):
    c = "badge-ok" if kind == "ok" else "badge-yr"
    return f'<span class="badge badge-{kind}">{text}</span>'

def trend_color(pct):
    """Return 'up'/'dn'/'st' based on percentage."""
    if pct is None:
        return "st"
    return "up" if pct > 0.5 else ("dn" if pct < -0.5 else "st")

def pct_pill(pct, label_suffix=""):
    if pct is None:
        return pill("~", "na")
    kind = trend_color(pct)
    sign = "+" if pct >= 0 else ""
    return pill(f"{sign}{pct:.1f}%{label_suffix}", kind)

def wow_calc(history_30d):
    """Compute WoW% from 30-day history (index 0=today, 6=7d ago)."""
    if len(history_30d) < 7:
        return None
    try:
        today = history_30d[0]["avg"]
        week_ago = history_30d[6]["avg"]
        if week_ago == 0:
            return None
        return round((today - week_ago) / week_ago * 100, 1)
    except (KeyError, TypeError, ZeroDivisionError):
        return None

def mom_calc(history_30d):
    """Compute MoM% from 30-day history (index 0=today, 29=30d ago)."""
    if len(history_30d) < 29:
        return None
    try:
        today = history_30d[0]["avg"]
        month_ago = history_30d[28]["avg"]
        if month_ago == 0:
            return None
        return round((today - month_ago) / month_ago * 100, 1)
    except (KeyError, TypeError, ZeroDivisionError):
        return None

# ─── chart data builders ─────────────────────
def rice_chart_data(data):
    h = data["rice_jasmine"].get("history_30d", [])
    if len(h) < 3:
        return "[]", "[]"
    # Thin out to ~10 points for readability (newest last)
    step = max(1, len(h) // 10)
    pts = list(reversed(h))[::step]  # oldest→newest
    labels = json.dumps([p["date"] for p in pts], ensure_ascii=False)
    values = json.dumps([p["avg"] for p in pts])
    return labels, values

def fob_chart_data():
    # Monthly FOB data (hardcoded known series — updated by scraper when available)
    labels = json.dumps(["ต.ค.68","พ.ย.68","ธ.ค.68","ม.ค.69","ก.พ.69","มี.ค.69"], ensure_ascii=False)
    values = json.dumps([354, 426, 379, 370, 370, 383])
    return labels, values

def rubber_chart_data():
    labels = json.dumps(["ก.ย.68","ต.ค.68","ธ.ค.68","ก.พ.69","มี.ค.69(ต้น)","มี.ค.69"], ensure_ascii=False)
    values = json.dumps([68.5, 70, 70, 72, 78, 71])
    return labels, values

def cane_chart_data(data):
    history = data["sugarcane"].get("history", [])
    pts = [(h["season"], h["initial"]) for h in reversed(history) if h.get("initial")]
    labels = json.dumps([p[0] for p in pts], ensure_ascii=False)
    values = json.dumps([p[1] for p in pts])
    return labels, values

# ─── status badge ────────────────────────────
def status_badge(status):
    if status == "confirmed":
        return badge("✓ ยืนยัน", "ok")
    elif status == "fallback":
        return badge("⚠️ fallback", "yr")
    return badge(status, "yr")

# ─── main HTML builder ────────────────────────
def build_html(data: dict) -> str:
    rj    = data["rice_jasmine"]
    cass  = data["cassava"]
    rub   = data["rubber"]
    cane  = data["sugarcane"]
    rfob  = data["rice_fob"]
    gen   = data.get("generated_date_th", data.get("generated_date", ""))

    # Computed changes
    wow_rj  = wow_calc(rj.get("history_30d", []))
    mom_rj  = mom_calc(rj.get("history_30d", []))
    tc_rj   = trend_color(mom_rj)

    rj_price   = fmt(rj.get("price"), 0)
    cf_low     = rj.get("price") # fallback
    cf_plow    = cass["cassava_fresh"].get("price_low")
    cf_phigh   = cass["cassava_fresh"].get("price_high")
    cc_plow    = cass["cassava_chips"].get("price_low")
    cc_phigh   = cass["cassava_chips"].get("price_high")
    rub_low    = rub.get("price_low")
    rub_high   = rub.get("price_high")
    cane_init  = cane.get("current_initial")
    w5_low     = rfob["white5"].get("price_low")
    w5_high    = rfob["white5"].get("price_high")
    hm_price   = rfob["homali"].get("price")

    price_range = lambda lo, hi: f"{fmt(lo,2)}–{fmt(hi,2)}" if lo and hi and lo != hi else fmt(lo, 2)

    rice_labels, rice_vals = rice_chart_data(data)
    fob_labels,  fob_vals  = fob_chart_data()
    rub_labels,  rub_vals  = rubber_chart_data()
    cane_labels, cane_vals = cane_chart_data(data)

    # ── JSON data for SheetJS Export ──────────────
    price_rows = [
        {"name_th": "ข้าวเปลือกหอมมะลิ 105",     "name_en": "Jasmine Paddy Rice",        "price": rj_price,                     "unit": "THB/ตัน", "wow": f"{wow_rj:+.1f}%" if wow_rj else "~", "mom_yoy": f"{mom_rj:+.1f}% MoM" if mom_rj else "~", "trend": "↑ RISING" if tc_rj=="up" else "↓ FALLING" if tc_rj=="dn" else "→ SIDEWAYS", "date": rj.get("date",""),           "status": rj.get("status","confirmed"),           "source": rj["source"]},
        {"name_th": "ข้าวเปลือกเจ้า ชื้น 15%",    "name_en": "White Paddy 15%",           "price": "7,200-8,000",                "unit": "THB/ตัน", "wow": "~", "mom_yoy": "~", "trend": "→ SIDEWAYS", "date": "ก.พ. 69",                   "status": "confirmed",                            "source": "สมาคมโรงสีข้าวไทย"},
        {"name_th": "ข้าวขาว 5% FOB Bangkok",     "name_en": "White Rice 5% FOB",         "price": price_range(w5_low, w5_high), "unit": "USD/ตัน", "wow": "~", "mom_yoy": "-7.0% MoM", "trend": "↓ FALLING",  "date": rfob["white5"].get("date",""), "status": rfob["white5"].get("status","confirmed"), "source": rfob["white5"]["source"]},
        {"name_th": "ข้าวหอมมะลิ 100% FOB",       "name_en": "Hom Mali 100% FOB",         "price": fmt(hm_price, 0),             "unit": "USD/ตัน", "wow": "~", "mom_yoy": "~",         "trend": "→ SIDEWAYS", "date": rfob["homali"].get("date",""),  "status": rfob["homali"].get("status","confirmed"), "source": rfob["homali"]["source"]},
        {"name_th": "หัวมันสด เชื้อแป้ง 30%",     "name_en": "Fresh Cassava 30% Starch",  "price": price_range(cf_plow, cf_phigh),"unit":"THB/กก.", "wow": "~", "mom_yoy": "~",         "trend": "→ SIDEWAYS", "date": cass["cassava_fresh"].get("date",""), "status": cass["cassava_fresh"].get("status","confirmed"), "source": "nettathai.org"},
        {"name_th": "มันเส้น (โกดังอยุธยา)",       "name_en": "Cassava Chips Ayutthaya",   "price": price_range(cc_plow, cc_phigh),"unit":"THB/กก.", "wow": "~", "mom_yoy": "~",         "trend": "→ SIDEWAYS", "date": cass["cassava_chips"].get("date",""), "status": cass["cassava_chips"].get("status","confirmed"), "source": "nettathai.org"},
        {"name_th": "ยางแผ่นรมควัน RSS3",          "name_en": "Rubber RSS3 Domestic",      "price": price_range(rub_low, rub_high),"unit":"THB/กก.", "wow": "~", "mom_yoy": "+7.0% MoM", "trend": "↑ RISING",   "date": rub.get("date",""),           "status": rub.get("status","confirmed"),           "source": rub["source"]},
        {"name_th": f"อ้อย ขั้นต้น {cane.get('current_season','')}", "name_en": "Sugarcane Initial Price", "price": fmt(cane_init, 0), "unit": "THB/ตัน", "wow": "annual", "mom_yoy": "-23.3% YoY", "trend": "↓↓ BEARISH", "date": f"{cane.get('date','')} (ครม.)", "status": "confirmed", "source": cane["source"]},
    ]
    price_data_json   = json.dumps(price_rows, ensure_ascii=False)
    rice_history_json = json.dumps(rj.get("history_30d", []), ensure_ascii=False)
    cane_history_json = json.dumps(cane.get("history", []),   ensure_ascii=False)

    # ── Rice detail section (TREA + TRM) ──────────────
    from generate_rice_section import build_rice_detail_section
    rice_detail_section = build_rice_detail_section(data.get("rice_detail", {}))


    # Sugarcane history rows
    cane_rows = ""
    for h in cane.get("history", []):
        init  = fmt(h.get("initial"), 0)
        final = fmt(h.get("final"), 2) if h.get("final") else "รอประกาศ"
        yoy   = h.get("yoy_initial")
        yoy_html = pct_pill(yoy, " YoY") if yoy is not None else pill("—", "na")
        src_date = h.get("source_date") or "—"
        src = h.get("source") or "—"
        is_current = "style='font-weight:600'" if h == cane.get("history", [{}])[0] else ""
        cane_rows += f"""
        <tr>
          <td {is_current}>{h['season']}{"&nbsp;★" if is_current else ""}</td>
          <td class="mono {'dn' if (yoy or 0) < 0 else 'up' if (yoy or 0) > 0 else ''}">{init}</td>
          <td class="mono">{final}</td>
          <td>{yoy_html}</td>
          <td style="font-size:10px;color:var(--muted)">{src_date} · {src}</td>
        </tr>"""

    HTML = f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ราคาพืชเศรษฐกิจไทย — Agri Price Intel</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
:root{{
  --bg:#0b0f14;--bg2:#111822;--bg3:#1a2332;
  --border:rgba(255,255,255,0.07);--border2:rgba(255,255,255,0.12);
  --text:#e2eaf5;--muted:#6b7fa0;--faint:#3a4a60;
  --green:#22c55e;--green-dim:rgba(34,197,94,0.12);
  --red:#f43f5e;--red-dim:rgba(244,63,94,0.12);
  --amber:#f59e0b;--blue:#38bdf8;
  --font:'IBM Plex Sans Thai',sans-serif;
  --mono:'IBM Plex Mono',monospace;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:var(--font);font-size:14px;line-height:1.6}}
.header{{background:var(--bg2);border-bottom:1px solid var(--border);padding:20px 32px 16px;
  display:flex;justify-content:space-between;align-items:flex-end;
  position:sticky;top:0;z-index:100;backdrop-filter:blur(8px)}}
.header h1{{font-size:18px;font-weight:600;color:#fff}}
.header h1 span{{color:var(--blue)}}
.header-sub{{font-size:11px;color:var(--muted);margin-top:3px;font-family:var(--mono)}}
.live-badge{{display:inline-flex;align-items:center;gap:6px;
  background:var(--green-dim);border:1px solid rgba(34,197,94,0.3);
  color:var(--green);font-size:11px;font-family:var(--mono);padding:4px 10px;border-radius:4px}}
.live-dot{{width:6px;height:6px;border-radius:50%;background:var(--green);animation:pulse 2s infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}
.container{{max-width:1280px;margin:0 auto;padding:24px 32px}}
.sec{{font-size:10px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;
  color:var(--muted);margin-bottom:12px;display:flex;align-items:center;gap:8px}}
.sec::after{{content:'';flex:1;height:1px;background:var(--border)}}
.cards-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;margin-bottom:28px}}
.card{{background:var(--bg2);border:1px solid var(--border);border-radius:8px;padding:16px;
  transition:border-color .2s,transform .15s;position:relative;overflow:hidden}}
.card::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:var(--accent,var(--faint))}}
.card:hover{{border-color:var(--border2);transform:translateY(-1px)}}
.card-label{{font-size:10px;color:var(--muted);margin-bottom:8px;font-weight:500}}
.card-price{{font-size:22px;font-weight:600;font-family:var(--mono);letter-spacing:-.02em;color:#fff}}
.card-unit{{font-size:10px;color:var(--muted);margin-left:4px;font-weight:400;font-family:var(--font)}}
.card-meta{{margin-top:8px;display:flex;gap:6px;flex-wrap:wrap;align-items:center}}
.card-date{{font-size:10px;color:var(--faint);margin-top:5px;font-family:var(--mono)}}
.pill{{font-size:10px;font-family:var(--mono);padding:2px 8px;border-radius:3px;font-weight:500}}
.pill-up{{background:var(--green-dim);color:var(--green);border:1px solid rgba(34,197,94,0.2)}}
.pill-dn{{background:var(--red-dim);color:var(--red);border:1px solid rgba(244,63,94,0.2)}}
.pill-st{{background:rgba(255,255,255,0.04);color:var(--muted);border:1px solid var(--border)}}
.pill-na{{background:transparent;color:var(--faint);border:1px solid var(--faint);font-size:9px}}
.charts-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px;margin-bottom:28px}}
.chart-card{{background:var(--bg2);border:1px solid var(--border);border-radius:8px;padding:16px}}
.chart-title{{font-size:12px;font-weight:600;color:var(--text)}}
.chart-sub{{font-size:10px;color:var(--muted);margin-top:2px;font-family:var(--mono);margin-bottom:10px}}
.chart-wrap{{position:relative;height:130px}}
.table-wrap,.ann-table-wrap{{background:var(--bg2);border:1px solid var(--border);border-radius:8px;overflow:hidden;margin-bottom:28px}}
.price-table{{width:100%;border-collapse:collapse;font-size:12px}}
.price-table thead tr{{background:var(--bg3)}}
.price-table th{{padding:10px 14px;text-align:left;font-size:10px;font-weight:600;letter-spacing:.06em;
  text-transform:uppercase;color:var(--muted);border-bottom:1px solid var(--border);white-space:nowrap}}
.price-table td{{padding:10px 14px;border-bottom:1px solid var(--border);vertical-align:middle}}
.price-table tr:last-child td{{border-bottom:none}}
.price-table tr:hover td{{background:rgba(255,255,255,0.02)}}
.mono{{font-family:var(--mono);font-size:13px;font-weight:500}}
.up{{color:var(--green)}}.dn{{color:var(--red)}}.st{{color:var(--muted)}}
.badge{{font-size:9px;font-family:var(--mono);padding:2px 7px;border-radius:3px;font-weight:600}}
.badge-ok{{background:rgba(34,197,94,0.12);color:var(--green);border:1px solid rgba(34,197,94,0.25)}}
.badge-yr{{background:rgba(245,158,11,0.12);color:var(--amber);border:1px solid rgba(245,158,11,0.25)}}
.summary-grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:28px}}
@media(max-width:720px){{.summary-grid{{grid-template-columns:1fr}}}}
.info-box{{background:var(--bg2);border-radius:8px;padding:16px;border-left:3px solid var(--blue)}}
.info-box.warn{{border-left-color:var(--amber)}}
.info-box h3{{font-size:11px;font-weight:600;color:var(--text);margin-bottom:8px}}
.info-box ul{{list-style:none;padding:0}}
.info-box li{{font-size:12px;color:var(--muted);padding:4px 0;border-bottom:1px solid var(--border);line-height:1.5}}
.info-box li:last-child{{border-bottom:none}}
.info-box li::before{{content:'›';color:var(--blue);margin-right:6px;font-weight:700}}
.info-box.warn li::before{{color:var(--amber)}}
.footer{{background:var(--bg2);border-top:1px solid var(--border);padding:20px 32px;display:flex;flex-wrap:wrap;gap:8px 20px}}
.footer-src{{font-size:10px;color:var(--faint);font-family:var(--mono)}}
.footer-src a{{color:var(--blue);text-decoration:none}}
.card,.chart-card{{animation:fadeUp .35s ease both}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:translateY(0)}}}}
</style>
</head>
<body>
<header class="header">
  <div>
    <h1>🌾 ราคาพืชเศรษฐกิจไทย <span>/ Agri Price Intel</span></h1>
    <div class="header-sub">ข้าว · มันสำปะหลัง · ยางพารา · อ้อย &nbsp;|&nbsp; อัปเดต: {gen}</div>
  </div>
  <div style="text-align:right">
    <div class="live-badge"><span class="live-dot"></span>Auto-updated daily</div>
    <div style="font-size:10px;color:var(--muted);margin-top:6px;font-family:var(--mono)">GitHub Actions · 08:00 ICT</div>
  </div>
</header>

<div class="container">

  <div class="sec">ราคาปัจจุบัน</div>
  <div class="cards-grid">

    <div class="card" style="--accent:var(--{'green' if tc_rj=='up' else 'red' if tc_rj=='dn' else 'faint'})">
      <div class="card-label">ข้าวเปลือกหอมมะลิ 105</div>
      <div class="card-price">{rj_price}<span class="card-unit">บาท/ตัน</span></div>
      <div class="card-meta">{pct_pill(wow_rj," WoW")}{pct_pill(mom_rj," MoM")}</div>
      <div class="card-date">{rj.get('date','')} · {rj['source']}</div>
    </div>

    <div class="card" style="--accent:var(--red)">
      <div class="card-label">ข้าวขาว 5% FOB Bangkok</div>
      <div class="card-price">{price_range(w5_low,w5_high)}<span class="card-unit">USD/ตัน</span></div>
      <div class="card-meta">{pill('WoW ~','na')}{pct_pill(-7.0,' MoM')}</div>
      <div class="card-date">{rfob['white5'].get('date','')} · {rfob['white5']['source']}</div>
    </div>

    <div class="card" style="--accent:var(--faint)">
      <div class="card-label">ข้าวหอมมะลิ 100% FOB</div>
      <div class="card-price">{fmt(hm_price,0)}<span class="card-unit">USD/ตัน</span></div>
      <div class="card-meta">{pill('→ STABLE','st')}</div>
      <div class="card-date">{rfob['homali'].get('date','')} · {rfob['homali']['source']}</div>
    </div>

    <div class="card" style="--accent:var(--faint)">
      <div class="card-label">หัวมันสด เชื้อแป้ง 30%</div>
      <div class="card-price">{price_range(cf_plow,cf_phigh)}<span class="card-unit">บาท/กก.</span></div>
      <div class="card-meta">{pill('→ STABLE','st')}</div>
      <div class="card-date">{cass['cassava_fresh'].get('date','')} · nettathai.org (นครราชสีมา)</div>
    </div>

    <div class="card" style="--accent:var(--faint)">
      <div class="card-label">มันเส้น (โกดังอยุธยา)</div>
      <div class="card-price">{price_range(cc_plow,cc_phigh)}<span class="card-unit">บาท/กก.</span></div>
      <div class="card-meta">{pill('→ STABLE','st')}</div>
      <div class="card-date">{cass['cassava_chips'].get('date','')} · nettathai.org</div>
    </div>

    <div class="card" style="--accent:var(--green)">
      <div class="card-label">ยางแผ่นรมควัน RSS3</div>
      <div class="card-price">{price_range(rub_low,rub_high)}<span class="card-unit">บาท/กก.</span></div>
      <div class="card-meta">{pill('↑ RISING','up')}{pct_pill(7.0,' MoM')}</div>
      <div class="card-date">{rub.get('date','')} · {rub['source']}</div>
    </div>

    <div class="card" style="--accent:var(--red)">
      <div class="card-label">อ้อย ขั้นต้น {cane.get('current_season','')}</div>
      <div class="card-price">{fmt(cane_init,0)}<span class="card-unit">บาท/ตัน</span></div>
      <div class="card-meta">{pill('annual price','na')}{pct_pill(-23.3,' YoY')}</div>
      <div class="card-date">{cane.get('date','')} · กอน./ครม. @ 10 CCS</div>
    </div>

  </div>

  <div class="sec">trend charts — ข้อมูลย้อนหลัง</div>
  <div class="charts-grid">
    <div class="chart-card">
      <div class="chart-title">ข้าวเปลือกหอมมะลิ 105</div>
      <div class="chart-sub">30 วัน รายวัน (THB/ตัน) · rakakaset.com → OAE</div>
      <div class="chart-wrap"><canvas id="c_rice"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">ข้าวขาว 5% FOB Bangkok</div>
      <div class="chart-sub">ย้อนหลัง 7 เดือน (USD/ตัน) · USDA / Nation Thailand</div>
      <div class="chart-wrap"><canvas id="c_fob"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">ยางแผ่นรมควัน RSS3</div>
      <div class="chart-sub">spot รายเดือน (THB/กก.) · ฐานเศรษฐกิจ / กยท.</div>
      <div class="chart-wrap"><canvas id="c_rubber"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">ราคาอ้อย ขั้นต้น รายปีการผลิต</div>
      <div class="chart-sub">THB/ตัน @ 10 CCS · กอน./สอน.</div>
      <div class="chart-wrap"><canvas id="c_cane"></canvas></div>
    </div>
  </div>

  <div class="sec">ตารางราคาละเอียด</div>
  <div class="table-wrap">
    <table class="price-table">
      <thead><tr>
        <th>สินค้า</th><th>ราคา</th><th>หน่วย</th>
        <th>WoW %</th><th>MoM / YoY %</th><th>Trend</th>
        <th>วันที่</th><th>สถานะ</th>
      </tr></thead>
      <tbody>
        <tr>
          <td>ข้าวเปลือกหอมมะลิ 105</td>
          <td class="mono {tc_rj}">{rj_price}</td>
          <td style="color:var(--muted);font-size:11px">THB/ตัน</td>
          <td>{pct_pill(wow_rj)}</td>
          <td>{pct_pill(mom_rj," MoM")}</td>
          <td class="{tc_rj}">{"↑ RISING" if tc_rj=="up" else "↓ FALLING" if tc_rj=="dn" else "→ SIDEWAYS"}</td>
          <td style="font-family:var(--mono);font-size:10px;color:var(--muted)">{rj.get('date','')}</td>
          <td>{status_badge(rj.get('status','confirmed'))}</td>
        </tr>
        <tr>
          <td>ข้าวเปลือกเจ้า ชื้น 15%</td>
          <td class="mono">7,200–8,000</td>
          <td style="color:var(--muted);font-size:11px">THB/ตัน</td>
          <td>{pill('~','na')}</td><td>{pill('~','na')}</td>
          <td class="st">→ SIDEWAYS</td>
          <td style="font-family:var(--mono);font-size:10px;color:var(--muted)">ก.พ. 69</td>
          <td>{badge('✓ ยืนยัน','ok')}</td>
        </tr>
        <tr>
          <td>ข้าวขาว 5% FOB Bangkok</td>
          <td class="mono dn">{price_range(w5_low,w5_high)}</td>
          <td style="color:var(--muted);font-size:11px">USD/ตัน</td>
          <td>{pill('~','na')}</td><td>{pct_pill(-7.0,' MoM')}</td>
          <td class="dn">↓ FALLING</td>
          <td style="font-family:var(--mono);font-size:10px;color:var(--muted)">{rfob['white5'].get('date','')}</td>
          <td>{status_badge(rfob['white5'].get('status','confirmed'))}</td>
        </tr>
        <tr>
          <td>ข้าวหอมมะลิ 100% FOB</td>
          <td class="mono">{fmt(hm_price,0)}</td>
          <td style="color:var(--muted);font-size:11px">USD/ตัน</td>
          <td>{pill('~','na')}</td><td>{pill('~','na')}</td>
          <td class="st">→ SIDEWAYS</td>
          <td style="font-family:var(--mono);font-size:10px;color:var(--muted)">{rfob['homali'].get('date','')}</td>
          <td>{status_badge(rfob['homali'].get('status','confirmed'))}</td>
        </tr>
        <tr>
          <td>หัวมันสด เชื้อแป้ง 30%</td>
          <td class="mono">{price_range(cf_plow,cf_phigh)}</td>
          <td style="color:var(--muted);font-size:11px">THB/กก.</td>
          <td>{pill('~','na')}</td><td>{pill('~','na')}</td>
          <td class="st">→ SIDEWAYS</td>
          <td style="font-family:var(--mono);font-size:10px;color:var(--muted)">{cass['cassava_fresh'].get('date','')}</td>
          <td>{status_badge(cass['cassava_fresh'].get('status','confirmed'))}</td>
        </tr>
        <tr>
          <td>มันเส้น (โกดังอยุธยา)</td>
          <td class="mono">{price_range(cc_plow,cc_phigh)}</td>
          <td style="color:var(--muted);font-size:11px">THB/กก.</td>
          <td>{pill('~','na')}</td><td>{pill('~','na')}</td>
          <td class="st">→ SIDEWAYS</td>
          <td style="font-family:var(--mono);font-size:10px;color:var(--muted)">{cass['cassava_chips'].get('date','')}</td>
          <td>{status_badge(cass['cassava_chips'].get('status','confirmed'))}</td>
        </tr>
        <tr>
          <td>ยางแผ่นรมควัน RSS3</td>
          <td class="mono up">{price_range(rub_low,rub_high)}</td>
          <td style="color:var(--muted);font-size:11px">THB/กก.</td>
          <td>{pill('~','na')}</td><td>{pct_pill(7.0,' MoM')}</td>
          <td class="up">↑ RISING</td>
          <td style="font-family:var(--mono);font-size:10px;color:var(--muted)">{rub.get('date','')}</td>
          <td>{status_badge(rub.get('status','confirmed'))}</td>
        </tr>
        <tr>
          <td>อ้อย ขั้นต้น {cane.get('current_season','')}</td>
          <td class="mono dn">{fmt(cane_init,0)}</td>
          <td style="color:var(--muted);font-size:11px">THB/ตัน</td>
          <td>{pill('annual','na')}</td><td>{pct_pill(-23.3,' YoY')}</td>
          <td class="dn">↓↓ BEARISH</td>
          <td style="font-family:var(--mono);font-size:10px;color:var(--muted)">{cane.get('date','')} (ครม.)</td>
          <td>{badge('✓ ยืนยัน','yr')}</td>
        </tr>
      </tbody>
    </table>
  </div>

  <div class="sec">ราคาอ้อย — ย้อนหลังรายปีการผลิต</div>
  <div class="ann-table-wrap">
    <table class="price-table">
      <thead><tr>
        <th>ฤดูการผลิต</th><th>ขั้นต้น (THB/ตัน)</th>
        <th>ขั้นสุดท้าย (THB/ตัน)</th><th>YoY ขั้นต้น</th><th>แหล่ง</th>
      </tr></thead>
      <tbody>{cane_rows}</tbody>
    </table>
  </div>

{rice_detail_section}

  <div class="sec">สรุปและข้อจำกัด</div>
  <div class="summary-grid">
    <div class="info-box">
      <h3>📌 สัญญาณตลาดวันนี้</h3>
      <ul>
        <li>ข้าวหอมมะลิเปลือก ↑ RISING ราคาขยับขึ้นต่อเนื่อง แรงหนุนมาตรการรัฐ + ความต้องการส่งออก</li>
        <li>ข้าวขาว 5% FOB ↓ FALLING บาทแข็ง + อินเดียกลับมาส่งออก กดดันตลาดโลก</li>
        <li>ยางพารา RSS3 ↑ RISING อุปทานขาดดุล 5–6 ปี + ช่วง wintering หนุนราคา</li>
        <li>อ้อย ↓↓ BEARISH ขั้นต้น 68/69 ลด 23% YoY ตามราคาน้ำตาลโลกปรับลง</li>
        <li>มันสำปะหลัง → SIDEWAYS ราคาทรงตัว บางรายต่ำกว่าต้นทุนตาม BoT</li>
      </ul>
    </div>
    <div class="info-box warn">
      <h3>⚠️ ข้อจำกัดของข้อมูล</h3>
      <ul>
        <li>WoW ~ = ไม่มีข้อมูลรายวันสำหรับมัน ยาง อ้อย ใช้ MoM/YoY แทน</li>
        <li>อ้อย: ประกาศรายปีต่อฤดูการผลิตโดย ครม. ไม่มีราคารายวัน/รายเดือน</li>
        <li>ยาง: raot.co.th ต้องสมัครสมาชิก อ้างจากรายงานข่าวแทน</li>
        <li>ราคาข้าว FOB ≠ ราคาในประเทศ | ราคาส่งออกเป็นตลาดโลก</li>
        <li>scraper อาจดึงข้อมูลไม่ได้หาก website ต้นทาง block bot</li>
      </ul>
    </div>
  </div>

</div>

<footer class="footer">
  <div class="footer-src">1. <a href="https://rakakaset.com/">rakakaset.com</a> (OAE) — ข้าวหอมมะลิรายวัน</div>
  <div class="footer-src">2. <a href="https://www.nettathai.org/2012-02-06-06-49-09.html">nettathai.org</a> — หัวมันสด + มันเส้น</div>
  <div class="footer-src">3. <a href="https://www.thansettakij.com">ฐานเศรษฐกิจ</a> / กยท. — ยาง RSS3</div>
  <div class="footer-src">4. <a href="https://spacebar.th/business/cabinet-sugarcane-price-2569">spacebar.th</a> / <a href="https://www.thaipbs.or.th">ThaiPBS</a> — ราคาอ้อย</div>
  <div class="footer-src">5. <a href="https://www.nationthailand.com">Nation Thailand</a> / USDA — ข้าว FOB</div>
  <div class="footer-src" style="color:var(--faint)">Generated: {data.get('generated_at','')[:16]} UTC · agri-price-intel</div>
  <div style="margin-left:auto">
    <button onclick="exportExcel()" id="btn-export" style="
      background:var(--green-dim);border:1px solid rgba(34,197,94,0.4);
      color:var(--green);font-family:var(--mono);font-size:11px;
      padding:7px 16px;border-radius:4px;cursor:pointer;
      transition:background .2s;display:flex;align-items:center;gap:7px">
      <span style="font-size:14px">⬇</span> Export Excel
    </button>
  </div>
</footer>

<script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<script>

/* ── Chart.js ───────────────────────────────── */
const G='rgba(255,255,255,0.06)',T='rgba(255,255,255,0.35)';
function mk(id,lbl,dat,col,unit){{
  const c=document.getElementById(id);if(!c)return;
  const g=c.getContext('2d').createLinearGradient(0,0,0,130);
  g.addColorStop(0,col+'44');g.addColorStop(1,col+'00');
  new Chart(c,{{type:'line',data:{{labels:lbl,datasets:[{{data:dat,borderColor:col,
    borderWidth:1.8,backgroundColor:g,pointRadius:0,pointHoverRadius:4,tension:.35,fill:true}}]}},
    options:{{responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{display:false}},tooltip:{{backgroundColor:'rgba(17,24,34,.95)',
        borderColor:'rgba(255,255,255,.1)',borderWidth:1,
        titleFont:{{family:'IBM Plex Mono',size:10}},bodyFont:{{family:'IBM Plex Mono',size:11}},
        callbacks:{{label:c=>c.parsed.y.toLocaleString('th-TH')+' '+unit}}}}}},
      scales:{{
        x:{{ticks:{{maxTicksLimit:6,font:{{family:'IBM Plex Mono',size:9}},color:T}},grid:{{display:false}},border:{{display:false}}}},
        y:{{ticks:{{maxTicksLimit:4,font:{{family:'IBM Plex Mono',size:9}},color:T,callback:v=>v.toLocaleString('th-TH')}},grid:{{color:G}},border:{{display:false}}}}
      }}
    }}
  }});
}}
mk('c_rice',{rice_labels},{rice_vals},'#22c55e','บาท/ตัน');
mk('c_fob',{fob_labels},{fob_vals},'#f43f5e','USD/ตัน');
mk('c_rubber',{rub_labels},{rub_vals},'#22c55e','บาท/กก.');
mk('c_cane',{cane_labels},{cane_vals},'#f43f5e','บาท/ตัน');

/* ── Export Excel (SheetJS) ─────────────────── */
const PRICE_DATA = {price_data_json};
const HISTORY_RICE = {rice_history_json};
const HISTORY_CANE = {cane_history_json};
const GEN_DATE = "{gen}";

function exportExcel() {{
  const btn = document.getElementById('btn-export');
  btn.textContent = '⏳ กำลังสร้าง...';
  btn.disabled = true;

  try {{
    const wb = XLSX.utils.book_new();

    /* ── Sheet 1: ราคาวันนี้ ── */
    const s1_rows = [
      ["สินค้า (TH)", "Commodity (EN)", "ราคาปัจจุบัน", "หน่วย", "WoW %", "MoM / YoY %", "Trend", "วันที่ข้อมูล", "สถานะ", "แหล่งข้อมูล"]
    ];
    PRICE_DATA.forEach(r => s1_rows.push([r.name_th, r.name_en, r.price, r.unit, r.wow, r.mom_yoy, r.trend, r.date, r.status, r.source]));
    const ws1 = XLSX.utils.aoa_to_sheet(s1_rows);
    ws1['!cols'] = [{{wch:30}},{{wch:28}},{{wch:18}},{{wch:12}},{{wch:12}},{{wch:16}},{{wch:14}},{{wch:20}},{{wch:12}},{{wch:40}}];
    XLSX.utils.book_append_sheet(wb, ws1, "ราคาวันนี้");

    /* ── Sheet 2: ราคารายวัน (ข้าว 30 วัน) ── */
    const s2_rows = [["วันที่", "ราคาเฉลี่ย (THB/ตัน)", "หมายเหตุ"]];
    HISTORY_RICE.forEach(r => s2_rows.push([r.date, r.avg, "rakakaset.com (OAE)"]));
    if (s2_rows.length === 1) s2_rows.push(["ไม่มีข้อมูลรายวัน", "N/A", "scraper ดึงข้อมูลไม่ได้"]);
    const ws2 = XLSX.utils.aoa_to_sheet(s2_rows);
    ws2['!cols'] = [{{wch:18}},{{wch:24}},{{wch:30}}];
    XLSX.utils.book_append_sheet(wb, ws2, "ข้าว-รายวัน 30d");

    /* ── Sheet 3: ราคาอ้อยรายปี ── */
    const s3_rows = [["ฤดูการผลิต", "ราคาขั้นต้น (THB/ตัน)", "ราคาขั้นสุดท้าย (THB/ตัน)", "YoY ขั้นต้น (%)", "แหล่ง"]];
    HISTORY_CANE.forEach(r => s3_rows.push([r.season, r.initial, r.final ?? "รอประกาศ", r.yoy ?? "—", r.source]));
    const ws3 = XLSX.utils.aoa_to_sheet(s3_rows);
    ws3['!cols'] = [{{wch:16}},{{wch:24}},{{wch:28}},{{wch:18}},{{wch:30}}];
    XLSX.utils.book_append_sheet(wb, ws3, "อ้อย-รายปี");

    /* ── Sheet 4: แหล่งข้อมูล ── */
    const s4_rows = [
      ["แหล่งข้อมูล", "URL", "ครอบคลุม", "ความถี่"],
      ["rakakaset.com (OAE)", "https://rakakaset.com/ข้าว/", "ข้าวหอมมะลิ 105", "รายวัน"],
      ["nettathai.org", "https://www.nettathai.org/2012-02-06-06-49-09.html", "หัวมันสด + มันเส้น", "ทุก 2-3 วัน"],
      ["ฐานเศรษฐกิจ / กยท.", "https://www.thansettakij.com", "ยาง RSS3", "รายวัน (ข่าว)"],
      ["กอน./สอน./ครม.", "https://spacebar.th/business/cabinet-sugarcane-price-2569", "ราคาอ้อย", "รายปีการผลิต"],
      ["Nation Thailand / USDA", "https://www.nationthailand.com", "ข้าวส่งออก FOB", "รายสัปดาห์"],
    ];
    const ws4 = XLSX.utils.aoa_to_sheet(s4_rows);
    ws4['!cols'] = [{{wch:30}},{{wch:55}},{{wch:30}},{{wch:20}}];
    XLSX.utils.book_append_sheet(wb, ws4, "แหล่งข้อมูล");

    /* ── Download ── */
    const dateStr = new Date().toISOString().slice(0,10).replace(/-/g,'');
    XLSX.writeFile(wb, `agri_prices_${{dateStr}}.xlsx`);

  }} catch(e) {{
    alert('Export ไม่สำเร็จ: ' + e.message);
  }} finally {{
    btn.innerHTML = '<span style="font-size:14px">⬇</span> Export Excel';
    btn.disabled = false;
  }}
}}
</script>
</body>
</html>"""
    return HTML


# ─── entrypoint ──────────────────────────────
if __name__ == "__main__":
    import argparse
    from scraper import scrape_all
    from scraper_rice_detail import scrape_rice_detail

    parser = argparse.ArgumentParser()
    parser.add_argument("--data", help="Path to existing JSON data file (skip scraping)")
    parser.add_argument("--out",  default="docs/index.html", help="Output HTML path")
    args = parser.parse_args()

    if args.data:
        with open(args.data, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = scrape_all()
        data["rice_detail"] = scrape_rice_detail()   # ← เพิ่มข้อมูลข้าวละเอียด
        snap_path = Path(args.out).parent / "data.json"
        snap_path.parent.mkdir(parents=True, exist_ok=True)
        with open(snap_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Data saved → {snap_path}")

    html = build_html(data)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"HTML generated → {out_path}  ({len(html):,} chars)")

"""
generate_rice_section.py
สร้าง HTML section ราคาข้าวละเอียด แบ่งชัดเจน 3 กลุ่ม:
  1. ราคาข้าวส่งออก FOB (TREA) — ตลาดโลก USD/MT
  2. ราคาข้าวสาร ในประเทศ (สมาคมโรงสีข้าวไทย) — THB/100กก.
  3. ราคาข้าวเปลือก รายจังหวัด (สมาคมโรงสีข้าวไทย) — THB/ตัน
"""

import json

def _int(val, default=0):
    try:
        return int(val or default)
    except (TypeError, ValueError):
        return default

def build_rice_detail_section(rice_data: dict) -> str:
    trea  = rice_data.get("trea_fob", {})
    trm   = rice_data.get("thai_rice_mills", {})

    trea_items = trea.get("items", [])
    milled     = trm.get("milled_rice", [])
    paddy_j    = trm.get("paddy_jasmine", [])
    paddy_w    = trm.get("paddy_white", [])
    paddy_s    = trm.get("paddy_sticky", [])

    # ── 1. FOB export rows ──────────────────────────────
    # จัดกลุ่ม: หอมมะลิ | ข้าวขาว | ข้าวนึ่ง | ข้าวเหนียว
    GROUP_ORDER = [
        ("หอมมะลิ / Fragrant",   ["Premium","Jasmine","Fragrant","Broken A.1"]),
        ("ข้าวขาว / White",      ["White Rice 100%","White Rice 5%","White Rice 25%","White Broken"]),
        ("ข้าวนึ่ง / Parboiled", ["Parboiled"]),
        ("ข้าวเหนียว / Glutinous",["Glutinous"]),
    ]

    fob_rows = ""
    used = set()
    for group_label, keywords in GROUP_ORDER:
        group_items = [i for i in trea_items
                       if any(k.lower() in i["name_en"].lower() for k in keywords)
                       and i["name_en"] not in used]
        if not group_items:
            continue
        # group header row
        fob_rows += f"""<tr>
          <td colspan="4" style="
            background:var(--bg3);
            color:var(--blue);
            font-size:10px;font-weight:600;letter-spacing:.06em;
            text-transform:uppercase;padding:6px 14px;
          ">{group_label}</td>
        </tr>"""
        for item in group_items:
            used.add(item["name_en"])
            p = item["price"]
            color = "up" if p >= 900 else ("dn" if p <= 380 else "")
            fob_rows += f"""<tr>
              <td style="padding-left:20px">{item['name_th']}</td>
              <td style="font-size:10px;color:var(--muted)">{item['name_en']}</td>
              <td class="mono {color}">{p:,}</td>
              <td style="font-size:10px;color:var(--muted)">USD/MT</td>
            </tr>"""

    # ── 2. ราคาข้าวสาร domestic rows ────────────────────
    # จัดกลุ่ม: หอมมะลิ | ข้าวขาว | ข้าวนึ่ง | ข้าวเหนียว
    MILLED_GROUPS = [
        ("หอมมะลิ / Fragrant",    ["หอมมะลิ", "ปลายข้าวหอม", "หอมปทุม"]),
        ("ข้าวขาว / White",       ["ข้าวขาว", "ปลายข้าวขาว", "กข 79"]),
        ("ข้าวนึ่ง / Parboiled",  ["นึ่ง"]),
        ("ข้าวเหนียว / Glutinous",["เหนียว"]),
    ]
    milled_rows = ""
    used_m = set()
    for group_label, keywords in MILLED_GROUPS:
        group_items = [i for i in milled
                       if any(k in i["name_th"] for k in keywords)
                       and i["name_th"] not in used_m]
        if not group_items:
            continue
        milled_rows += f"""<tr>
          <td colspan="4" style="
            background:var(--bg3);
            color:var(--amber);
            font-size:10px;font-weight:600;letter-spacing:.06em;
            text-transform:uppercase;padding:6px 14px;
          ">{group_label}</td>
        </tr>"""
        for item in group_items:
            used_m.add(item["name_th"])
            lo, hi = item["price_low"], item["price_high"]
            price_str = f"{lo:,}" if lo == hi else f"{lo:,}–{hi:,}"
            note_html = (f'<span style="font-size:9px;color:var(--amber);margin-left:5px">'
                         f'↑ {item["note"]}</span>') if item.get("note") else ""
            milled_rows += f"""<tr>
              <td style="padding-left:20px">{item['name_th']}{note_html}</td>
              <td style="font-size:10px;color:var(--muted)">{item['name_en']}</td>
              <td class="mono">{price_str}</td>
              <td style="font-size:10px;color:var(--muted)">THB/100กก.</td>
            </tr>"""

    # ── 3. ราคาข้าวเปลือก รายจังหวัด ───────────────────
    jasmine_rows = ""
    for p in paddy_j:
        avg = (p["price_low"] + p["price_high"]) // 2
        jasmine_rows += f"""<tr>
          <td>{p['province']}</td>
          <td class="mono">{p['price_low']:,}–{p['price_high']:,}</td>
          <td style="font-family:var(--mono);font-size:11px;color:var(--muted)">~{avg:,}</td>
        </tr>"""

    white_rows = ""
    for p in paddy_w:
        white_rows += f"""<tr>
          <td>{p['province']}</td>
          <td class="mono">{p['price_low']:,}–{p['price_high']:,}</td>
        </tr>"""

    sticky_rows = ""
    for p in paddy_s:
        sticky_rows += f"""<tr>
          <td>{p['province']}</td>
          <td class="mono">{p['price_low']:,}–{p['price_high']:,}</td>
        </tr>"""

    # stats
    pj_avg = _int(trm.get('paddy_jasmine_stats', {}).get('avg') or trm.get('paddy_jasmine_avg'))
    pj_min = _int(trm.get('paddy_jasmine_stats', {}).get('min') or trm.get('paddy_jasmine_min'))
    pj_max = _int(trm.get('paddy_jasmine_stats', {}).get('max') or trm.get('paddy_jasmine_max'))
    pw_avg = _int(trm.get('paddy_white_stats', {}).get('avg') or trm.get('paddy_white_avg'))
    pw_min = _int(trm.get('paddy_white_stats', {}).get('min') or trm.get('paddy_white_min'))
    pw_max = _int(trm.get('paddy_white_stats', {}).get('max') or trm.get('paddy_white_max'))

    trm_date   = trm.get('date','N/A')
    trm_url    = trm.get('source_url','')
    trm_src    = trm.get('source','')
    trm_pdf    = trm.get('pdf_url','')
    trm_scraped = trm.get('scraped', False)

    trea_date   = trea.get('date','N/A')
    trea_url    = trea.get('source_url','')
    trea_src    = trea.get('source','')
    trea_scraped = trea.get('scraped', False)

    scraped_badge = lambda s: (
        '<span style="background:rgba(34,197,94,0.12);color:#22c55e;border:1px solid rgba(34,197,94,0.3);'
        'font-size:9px;padding:1px 7px;border-radius:3px;font-family:var(--mono);margin-left:8px">✓ scraped live</span>'
        if s else
        '<span style="background:rgba(245,158,11,0.12);color:#f59e0b;border:1px solid rgba(245,158,11,0.3);'
        'font-size:9px;padding:1px 7px;border-radius:3px;font-family:var(--mono);margin-left:8px">⚠ fallback</span>'
    )

    pdf_link = (f' | <a href="{trm_pdf}" style="color:var(--blue)" target="_blank">⬇ PDF</a>'
                if trm_pdf else '')

    # ── Comparison table (FOB vs domestic same type) ──────
    def _fob(keyword):
        return next((i["price"] for i in trea_items
                     if keyword.lower() in i["name_en"].lower()), None)

    def _dom_milled(keyword):
        item = next((i for i in milled if keyword in i["name_th"]), None)
        if item:
            lo, hi = item["price_low"], item["price_high"]
            return f"{lo:,}–{hi:,} THB/100กก." if lo != hi else f"{lo:,} THB/100กก."
        return "—"

    COMPARE = [
        ("ข้าวหอมมะลิ 68/69",  _fob("2025/26"),      _dom_milled("68/69"),     "ข้าวสารในประเทศ (THB/100กก.) vs ส่งออก FOB (USD/MT)"),
        ("ข้าวขาว 5%",          _fob("White Rice 5%"), _dom_milled("ข้าวขาว 5%"), "ข้าวสาร 5% ในประเทศ vs FOB"),
        ("ข้าวนึ่ง 100%",       _fob("Parboiled Rice 100%\n"), _dom_milled("นึ่ง 100%"), "ข้าวนึ่งในประเทศ vs FOB"),
        ("ข้าวเปลือกเจ้า (เฉลี่ย)", None,
         f"~{pw_avg:,} THB/ตัน" if pw_avg else "—",
         f"ช่วง {pw_min:,}–{pw_max:,} | ชื้น 15%"),
        ("ข้าวเปลือกหอมมะลิ (เฉลี่ย)", None,
         f"~{pj_avg:,} THB/ตัน" if pj_avg else "—",
         f"ช่วง {pj_min:,}–{pj_max:,} | ชื้น 15%"),
    ]
    cmp_rows = ""
    for name, fob, dom, note in COMPARE:
        fob_html = (f'<span class="mono" style="color:var(--blue)">{fob:,} USD/MT</span>'
                    if fob else '<span style="color:var(--faint)">—</span>')
        cmp_rows += f"""<tr>
          <td style="font-weight:500">{name}</td>
          <td>{fob_html}</td>
          <td class="mono">{dom}</td>
          <td style="font-size:10px;color:var(--muted)">{note}</td>
        </tr>"""

    # ── Section divider style ──────────────────────────────
    def section_header(emoji, title, subtitle, border_color="#38bdf8"):
        return f"""<div style="
          display:flex;align-items:center;gap:10px;
          border-left:3px solid {border_color};
          padding:8px 0 8px 14px;
          margin:24px 0 10px;
        ">
          <div>
            <div style="font-size:14px;font-weight:600;color:var(--text)">{emoji} {title}</div>
            <div style="font-size:10px;color:var(--muted);margin-top:2px;font-family:var(--mono)">{subtitle}</div>
          </div>
        </div>"""

    section = f"""
  <!-- ══════════════════════════════════════════════════
       SECTION A: ราคาข้าวส่งออก FOB
  ═══════════════════════════════════════════════════ -->

  {section_header("📦", "ราคาข้าวส่งออก FOB",
    f"ตลาดโลก · USD per Metric Ton · F.O.B. Bangkok · อัปเดต: {trea_date}",
    "#38bdf8")}

  <div style="font-size:11px;color:var(--muted);margin-bottom:10px;display:flex;align-items:center;gap:8px">
    <span>แหล่ง: <a href="{trea_url}" style="color:var(--blue)" target="_blank">{trea_src}</a></span>
    {scraped_badge(trea_scraped)}
  </div>

  <div class="table-wrap" style="margin-bottom:8px">
    <table class="price-table">
      <thead><tr>
        <th>ชนิดข้าว</th>
        <th>Commodity (EN)</th>
        <th style="text-align:right">ราคา</th>
        <th>หน่วย</th>
      </tr></thead>
      <tbody>{fob_rows}</tbody>
    </table>
  </div>
  <div style="font-size:10px;color:var(--faint);margin-bottom:24px;font-family:var(--mono)">
    Unit: U.S. Dollars per metric ton (milled rice basis), F.O.B. prices
  </div>

  <!-- ══════════════════════════════════════════════════
       SECTION B: ราคาข้าวสาร ในประเทศ
  ═══════════════════════════════════════════════════ -->

  {section_header("🏭", "ราคาข้าวสาร ในประเทศ",
    f"ราคาขายส่ง ตลาดกรุงเทพ · THB/100กก. · อัปเดต: {trm_date}",
    "#f59e0b")}

  <div style="font-size:11px;color:var(--muted);margin-bottom:10px;display:flex;align-items:center;gap:8px">
    <span>แหล่ง: <a href="{trm_url}" style="color:var(--blue)" target="_blank">{trm_src}</a></span>
    {scraped_badge(trm_scraped)}
    {pdf_link}
  </div>

  <div class="table-wrap" style="margin-bottom:24px">
    <table class="price-table">
      <thead><tr>
        <th>ชนิดข้าว</th>
        <th>Commodity (EN)</th>
        <th style="text-align:right">ราคา</th>
        <th>หน่วย</th>
      </tr></thead>
      <tbody>{milled_rows}</tbody>
    </table>
  </div>

  <!-- ══════════════════════════════════════════════════
       SECTION C: ราคาข้าวเปลือก รายจังหวัด
  ═══════════════════════════════════════════════════ -->

  {section_header("🌾", "ราคาข้าวเปลือก รายจังหวัด",
    f"THB/ตัน · ชื้น 15% · อัปเดต: {trm_date}",
    "#22c55e")}

  <div style="font-size:11px;color:var(--muted);margin-bottom:12px">
    แหล่ง: <a href="{trm_url}" style="color:var(--blue)" target="_blank">{trm_src}</a>
    {scraped_badge(trm_scraped)}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:8px">

    <div>
      <div style="font-size:11px;font-weight:600;color:var(--green);margin-bottom:6px;
                  display:flex;align-items:center;gap:6px">
        <span style="width:8px;height:8px;border-radius:50%;background:var(--green);display:inline-block"></span>
        ข้าวเปลือกหอมมะลิ (68/69) — ชื้น 15%
      </div>
      <div class="table-wrap">
        <table class="price-table">
          <thead><tr>
            <th>จังหวัด</th>
            <th>ช่วงราคา (THB/ตัน)</th>
            <th>เฉลี่ย</th>
          </tr></thead>
          <tbody>{jasmine_rows if jasmine_rows else '<tr><td colspan="3" style="color:var(--faint);text-align:center">ไม่มีข้อมูล</td></tr>'}</tbody>
        </table>
      </div>
      <div style="font-size:10px;color:var(--muted);margin-top:6px;font-family:var(--mono);
                  background:var(--bg3);padding:6px 10px;border-radius:4px">
        เฉลี่ยทั้งประเทศ: <span style="color:var(--green);font-weight:600">~{pj_avg:,}</span> บาท/ตัน
        &nbsp;·&nbsp; ช่วง: {pj_min:,}–{pj_max:,}
      </div>
    </div>

    <div>
      <div style="font-size:11px;font-weight:600;color:var(--muted);margin-bottom:6px;
                  display:flex;align-items:center;gap:6px">
        <span style="width:8px;height:8px;border-radius:50%;background:var(--muted);display:inline-block"></span>
        ข้าวเปลือกเจ้า — ชื้น 15%
      </div>
      <div class="table-wrap">
        <table class="price-table">
          <thead><tr>
            <th>จังหวัด</th>
            <th>ช่วงราคา (THB/ตัน)</th>
          </tr></thead>
          <tbody>{white_rows if white_rows else '<tr><td colspan="2" style="color:var(--faint);text-align:center">ไม่มีข้อมูล</td></tr>'}</tbody>
        </table>
      </div>
      <div style="font-size:10px;color:var(--muted);margin-top:6px;font-family:var(--mono);
                  background:var(--bg3);padding:6px 10px;border-radius:4px">
        เฉลี่ยทั้งประเทศ: <span style="color:var(--text);font-weight:600">~{pw_avg:,}</span> บาท/ตัน
        &nbsp;·&nbsp; ช่วง: {pw_min:,}–{pw_max:,}
      </div>
    </div>

  </div>

  {'<div style="margin-bottom:24px"><div style="font-size:11px;font-weight:600;color:var(--amber);margin-bottom:6px;display:flex;align-items:center;gap:6px"><span style="width:8px;height:8px;border-radius:50%;background:var(--amber);display:inline-block"></span>ข้าวเปลือกเหนียว กข.6 — ชื้น 15%</div><div class="table-wrap"><table class="price-table"><thead><tr><th>จังหวัด</th><th>ช่วงราคา (THB/ตัน)</th></tr></thead><tbody>' + sticky_rows + '</tbody></table></div></div>' if sticky_rows else ''}

  <!-- ══════════════════════════════════════════════════
       SECTION D: ตาราง Match — FOB vs ในประเทศ
  ═══════════════════════════════════════════════════ -->

  {section_header("🔄", "เปรียบเทียบ — ราคาส่งออก FOB vs ราคาในประเทศ",
    "ข้าวชนิดเดียวกัน เปรียบเทียบ USD/MT (FOB) กับ THB/100กก. หรือ THB/ตัน (ในประเทศ)",
    "#8b5cf6")}

  <div class="table-wrap" style="margin-bottom:28px">
    <table class="price-table">
      <thead><tr>
        <th>ชนิดข้าว</th>
        <th>ราคาส่งออก FOB <span style="color:var(--blue)">(TREA)</span></th>
        <th>ราคาในประเทศ <span style="color:var(--amber)">(สมาคมโรงสีฯ)</span></th>
        <th>หมายเหตุ</th>
      </tr></thead>
      <tbody>{cmp_rows}</tbody>
    </table>
  </div>
"""
    return section


if __name__ == "__main__":
    from scraper_rice_detail import scrape_rice_detail
    import logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    data = scrape_rice_detail()
    print(build_rice_detail_section(data))

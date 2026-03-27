"""
generate_rice_section.py
สร้าง HTML section สำหรับราคาข้าวละเอียด
import ฟังก์ชันนี้ใน generate_html.py
"""

import json

def build_rice_detail_section(rice_data: dict) -> str:
    trea   = rice_data.get("trea_fob", {})
    trm    = rice_data.get("thai_rice_mills", {})

    trea_items   = trea.get("items", [])
    milled       = trm.get("milled_rice", [])
    paddy_j      = trm.get("paddy_jasmine", [])
    paddy_w      = trm.get("paddy_white", [])
    paddy_s      = trm.get("paddy_sticky", [])

    # ── Match: ราคาข้าวไทย FOB vs ราคาในประเทศ (เทียบชนิดเดียวกัน) ──
    MATCH = [
        {
            "type": "ข้าวหอมมะลิ Premium (68/69)",
            "fob_usd":  next((i["price"] for i in trea_items if "68/69" in i["name_th"] and "Premium" in i["name_en"]), None),
            "dom_thb_range": "3,250–3,416 บาท/100กก.",
            "dom_src": "สมาคมโรงสีข้าวไทย",
            "note": "ราคาในประเทศ = ข้าวสาร, FOB = ส่งออก"
        },
        {
            "type": "ข้าวขาว 5%",
            "fob_usd":  next((i["price"] for i in trea_items if i["name_en"] == "White Rice 5%"), None),
            "dom_thb_range": "1,060–1,080 บาท/100กก.",
            "dom_src": "สมาคมโรงสีข้าวไทย",
            "note": "ราคาในประเทศ = ข้าวสาร"
        },
        {
            "type": "ข้าวเปลือกเจ้า (ชื้น 15%)",
            "fob_usd":  None,
            "dom_thb_range": f"{int(trm.get('paddy_white_min') or 0):,}–{int(trm.get('paddy_white_max') or 0):,} บาท/ตัน",
            "dom_src": "สมาคมโรงสีข้าวไทย",
            "note": f"เฉลี่ยทุกจังหวัด ~{int(trm.get('paddy_white_avg') or 0):,} บาท/ตัน"
        },
        {
            "type": "ข้าวเปลือกหอมมะลิ 68/69",
            "fob_usd":  None,
            "dom_thb_range": f"{int(trm.get('paddy_jasmine_min') or 0):,}–{int(trm.get('paddy_jasmine_max') or 0):,} บาท/ตัน",
            "dom_src": "สมาคมโรงสีข้าวไทย",
            "note": f"เฉลี่ยทุกจังหวัด ~{int(trm.get('paddy_jasmine_avg') or 0):,} บาท/ตัน"
        },
        {
            "type": "ข้าวนึ่ง 100%",
            "fob_usd":  next((i["price"] for i in trea_items if "Parboiled Rice 100%" == i["name_en"]), None),
            "dom_thb_range": "1,110–1,130 บาท/100กก.",
            "dom_src": "สมาคมโรงสีข้าวไทย",
            "note": "ราคาในประเทศ = ข้าวนึ่ง 100% สีอ่อน"
        },
    ]

    # ── Build FOB table rows ──
    fob_rows = ""
    for item in trea_items:
        p = item["price"]
        # color coding
        if p >= 900: color = "up"
        elif p <= 380: color = "dn"
        else: color = ""
        fob_rows += f"""<tr>
          <td>{item['name_th']}</td>
          <td style="font-size:10px;color:var(--muted)">{item['name_en']}</td>
          <td class="mono {color}">{p:,}</td>
          <td style="font-size:10px;color:var(--muted)">USD/MT FOB</td>
        </tr>"""

    # ── Build Milled Rice domestic table ──
    milled_rows = ""
    for item in milled:
        lo, hi = item["price_low"], item["price_high"]
        price_str = f"{lo:,}" if lo == hi else f"{lo:,}–{hi:,}"
        note_html = f'<span style="font-size:9px;color:var(--amber);margin-left:4px">{item["note"]}</span>' if item.get("note") else ""
        milled_rows += f"""<tr>
          <td>{item['name_th']}{note_html}</td>
          <td style="font-size:10px;color:var(--muted)">{item['name_en']}</td>
          <td class="mono">{price_str}</td>
          <td style="font-size:10px;color:var(--muted)">THB/100กก.</td>
        </tr>"""

    # ── Build Paddy Jasmine province table ──
    jasmine_rows = ""
    for p in paddy_j:
        avg = (p["price_low"] + p["price_high"]) // 2
        jasmine_rows += f"""<tr>
          <td>{p['province']}</td>
          <td class="mono">{p['price_low']:,}–{p['price_high']:,}</td>
          <td style="font-family:var(--mono);font-size:11px;color:var(--muted)">~{avg:,}</td>
        </tr>"""

    # ── Build Paddy White province table ──
    white_rows = ""
    for p in paddy_w:
        white_rows += f"""<tr>
          <td>{p['province']}</td>
          <td class="mono">{p['price_low']:,}–{p['price_high']:,}</td>
        </tr>"""

    # ── Match table rows ──
    match_rows = ""
    for m in MATCH:
        fob_html = f'<span class="mono">{m["fob_usd"]:,} USD/MT</span>' if m["fob_usd"] else '<span style="color:var(--faint)">—</span>'
        match_rows += f"""<tr>
          <td style="font-weight:500">{m['type']}</td>
          <td>{fob_html}</td>
          <td class="mono">{m['dom_thb_range']}</td>
          <td style="font-size:10px;color:var(--muted)">{m['note']}</td>
        </tr>"""

    # ── Assemble full section HTML ──
    section = f"""
  <!-- ════════════════════════════════════════════════
       SECTION: ราคาข้าวละเอียด
  ═══════════════════════════════════════════════════ -->
  <div class="sec">ราคาข้าวส่งออก FOB — Thai Rice Exporters Association</div>
  <div style="font-size:11px;color:var(--muted);margin-bottom:10px;font-family:var(--mono)">
    อัปเดต: {trea.get('date','N/A')} | แหล่ง: <a href="{trea.get('source_url','')}" style="color:var(--blue)">{trea.get('source','')}</a>
    &nbsp;|&nbsp; Unit: US Dollars per metric ton (milled rice basis), F.O.B. prices
  </div>
  <div class="table-wrap" style="margin-bottom:18px">
    <table class="price-table">
      <thead><tr>
        <th>ชนิดข้าว (TH)</th>
        <th>Commodity (EN)</th>
        <th>ราคา (USD/MT)</th>
        <th>หน่วย</th>
      </tr></thead>
      <tbody>{fob_rows}</tbody>
    </table>
  </div>

  <div class="sec">ราคาข้าวในประเทศ — สมาคมโรงสีข้าวไทย</div>
  <div style="font-size:11px;color:var(--muted);margin-bottom:10px;font-family:var(--mono)">
    อัปเดต: {trm.get('date','N/A')} | แหล่ง: <a href="{trm.get('source_url','')}" style="color:var(--blue)">{trm.get('source','')}</a>
    &nbsp;|&nbsp; ราคาข้าวสารขายส่ง ส่งตลาดกรุงเทพ (บาท/100กก.)
  </div>
  <div class="table-wrap" style="margin-bottom:18px">
    <table class="price-table">
      <thead><tr>
        <th>ชนิดข้าว (TH)</th><th>Commodity (EN)</th>
        <th>ราคา (THB/100กก.)</th><th>หน่วย</th>
      </tr></thead>
      <tbody>{milled_rows}</tbody>
    </table>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:18px">

    <div>
      <div class="sec" style="margin-top:0">ข้าวเปลือกหอมมะลิ 68/69 — รายจังหวัด (ชื้น 15%)</div>
      <div class="table-wrap">
        <table class="price-table">
          <thead><tr><th>จังหวัด</th><th>ต่ำสุด–สูงสุด (THB/ตัน)</th><th>เฉลี่ย</th></tr></thead>
          <tbody>{jasmine_rows}</tbody>
        </table>
      </div>
      <div style="font-size:10px;color:var(--muted);margin-top:6px;font-family:var(--mono)">
        เฉลี่ยทั้งประเทศ: <span style="color:var(--green);font-weight:500">~{trm.get('paddy_jasmine_avg',0):,} บาท/ตัน</span>
        &nbsp;| ช่วง: {trm.get('paddy_jasmine_min',0):,}–{trm.get('paddy_jasmine_max',0):,}
      </div>
    </div>

    <div>
      <div class="sec" style="margin-top:0">ข้าวเปลือกเจ้า ชื้น 15% — รายจังหวัด</div>
      <div class="table-wrap">
        <table class="price-table">
          <thead><tr><th>จังหวัด</th><th>ต่ำสุด–สูงสุด (THB/ตัน)</th></tr></thead>
          <tbody>{white_rows}</tbody>
        </table>
      </div>
      <div style="font-size:10px;color:var(--muted);margin-top:6px;font-family:var(--mono)">
        เฉลี่ยทั้งประเทศ: <span style="color:var(--text);font-weight:500">~{trm.get('paddy_white_avg',0):,} บาท/ตัน</span>
        &nbsp;| ช่วง: {trm.get('paddy_white_min',0):,}–{trm.get('paddy_white_max',0):,}
      </div>
    </div>

  </div>

  <div class="sec">ตาราง Match — FOB ส่งออก vs ราคาในประเทศ (ชนิดเดียวกัน)</div>
  <div style="font-size:11px;color:var(--muted);margin-bottom:10px">
    เปรียบเทียบราคาข้าวชนิดเดียวกัน: ราคา FOB ตลาดโลก (USD/MT) vs ราคาในประเทศ (THB)
  </div>
  <div class="table-wrap" style="margin-bottom:28px">
    <table class="price-table">
      <thead><tr>
        <th>ชนิดข้าว</th>
        <th>ราคาส่งออก FOB (TREA)</th>
        <th>ราคาในประเทศ (สมาคมโรงสีฯ)</th>
        <th>หมายเหตุ</th>
      </tr></thead>
      <tbody>{match_rows}</tbody>
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

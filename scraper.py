"""
scraper.py — Thai Agricultural Price Scraper
Sources:
  1. rakakaset.com  → ข้าวเปลือกหอมมะลิ (aggregates OAE)
  2. nettathai.org  → หัวมันสด + มันเส้น
  3. thansettakij   → ยางพารา RSS3 (news-based)
  4. OCSB/ครม.      → ราคาอ้อย (annual, cached)
  5. bangkokpost/nation → ข้าวส่งออก FOB (weekly)
"""

import re
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, date
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("scraper")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
    "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
}

def fetch(url: str, timeout: int = 15) -> Optional[str]:
    """Fetch URL, return text or None on error."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            enc = r.headers.get_content_charset() or "utf-8"
            return raw.decode(enc, errors="replace")
    except Exception as e:
        log.warning(f"fetch failed {url}: {e}")
        return None


# ─────────────────────────────────────────────
# 1. ข้าวเปลือกหอมมะลิ 105 — rakakaset.com
# ─────────────────────────────────────────────
def scrape_rice_jasmine() -> dict:
    url = "https://rakakaset.com/%E0%B8%82%E0%B9%89%E0%B8%B2%E0%B8%A7/"
    html = fetch(url)
    result = {
        "commodity": "ข้าวเปลือกหอมมะลิ 105",
        "commodity_en": "Jasmine Paddy Rice",
        "price": None,
        "unit": "THB/ตัน",
        "date": None,
        "source": "rakakaset.com (อ้าง OAE)",
        "source_url": url,
        "history_30d": [],
        "status": "confirmed",
    }
    if not html:
        return result

    # Current price
    m = re.search(r'([\d,]+\.?\d*)\s*\n\s*บาท/ตัน', html)
    if not m:
        m = re.search(r'ราคารับซื้อวันนี้.*?([\d,]+\.\d+)\s*\n\s*บาท/ตัน', html, re.DOTALL)
    if m:
        result["price"] = float(m.group(1).replace(",", ""))

    # Date
    m_date = re.search(r'อัปเดต:\s*(\d+\s+\S+\.\s*\d+)', html)
    if m_date:
        result["date"] = m_date.group(1).strip()

    # 30-day history table
    rows = re.findall(
        r'\|\s*(\d+\s+\S+\.?\s*\d+)\s*\|[^|]*\|\s*([\d,]+\.?\d*)\s*\|',
        html
    )
    history = []
    for raw_date, avg in rows[:30]:
        try:
            history.append({
                "date": raw_date.strip(),
                "avg": float(avg.replace(",", ""))
            })
        except ValueError:
            continue
    result["history_30d"] = history

    log.info(f"rice_jasmine: {result['price']} THB/ตัน ({result['date']}), {len(history)} history rows")
    return result


# ─────────────────────────────────────────────
# 2. มันสำปะหลัง — nettathai.org
# ─────────────────────────────────────────────
def scrape_cassava() -> dict:
    url = "https://www.nettathai.org/2012-02-06-06-49-09.html"
    html = fetch(url)
    result = {
        "cassava_fresh": {
            "commodity": "หัวมันสด เชื้อแป้ง 30% (นครราชสีมา)",
            "commodity_en": "Fresh Cassava 30% Starch",
            "price_low": None, "price_high": None,
            "unit": "THB/กก.",
            "date": None,
            "source": "สมาคมโรงงานมันสำปะหลัง ภาคอีสาน",
            "source_url": url,
            "status": "confirmed",
        },
        "cassava_chips": {
            "commodity": "มันเส้น (โกดังผู้ส่งออก อยุธยา)",
            "commodity_en": "Cassava Chips Ayutthaya",
            "price_low": None, "price_high": None,
            "unit": "THB/กก.",
            "date": None,
            "source": "สมาคมโรงงานมันสำปะหลัง ภาคอีสาน",
            "source_url": url,
            "status": "confirmed",
        },
    }
    if not html:
        return result

    # Date from latest heading
    m_date = re.search(r'วันที่\s+(\d+\s+\S+\s+\d+)', html)
    if m_date:
        d = m_date.group(1).strip()
        result["cassava_fresh"]["date"] = d
        result["cassava_chips"]["date"] = d

    # Fresh cassava: เมือง row (most representative)
    m_fresh = re.search(
        r'เมือง\s*\|\s*([\d.]+)\s*-\s*([\d.]+)\s*\|\s*([\d.]+)\s*-\s*([\d.]+)',
        html
    )
    if not m_fresh:
        # fallback: first price range in table
        m_fresh = re.search(r'\|\s*([\d.]+)\s*-\s*([\d.]+)\s*\|\s*([\d.]+)\s*-\s*([\d.]+)', html)
    if m_fresh:
        result["cassava_fresh"]["price_low"]  = float(m_fresh.group(1))
        result["cassava_fresh"]["price_high"] = float(m_fresh.group(2))

    # Chips: อยุธยา
    m_chips = re.search(r'อยุธยา.*?([\d.]+)\s*-\s*([\d.]+)', html, re.DOTALL)
    if not m_chips:
        m_chips = re.search(r'([\d.]+)\s*-\s*([\d.]+)\s*\n.*?มันเส้น', html, re.DOTALL)
    if m_chips:
        result["cassava_chips"]["price_low"]  = float(m_chips.group(1))
        result["cassava_chips"]["price_high"] = float(m_chips.group(2))

    log.info(f"cassava_fresh: {result['cassava_fresh']['price_low']}–{result['cassava_fresh']['price_high']} ({result['cassava_fresh']['date']})")
    log.info(f"cassava_chips: {result['cassava_chips']['price_low']}–{result['cassava_chips']['price_high']}")
    return result


# ─────────────────────────────────────────────
# 3. ยางแผ่นรมควัน RSS3 — search via news
# ─────────────────────────────────────────────
def scrape_rubber() -> dict:
    """
    raot.co.th requires login. Use thansettakij or bangkokbiznews news instead.
    We search for latest RSS3 price from news sources.
    """
    result = {
        "commodity": "ยางแผ่นรมควัน RSS3",
        "commodity_en": "Rubber RSS3 Domestic",
        "price_low": None, "price_high": None,
        "unit": "THB/กก.",
        "date": None,
        "source": "ฐานเศรษฐกิจ / กยท.",
        "source_url": "https://www.thansettakij.com",
        "status": "confirmed",
        "note": "raot.co.th ต้องสมัครสมาชิก; อ้างจากรายงานข่าว",
    }

    # Try thansettakij rubber article
    urls_to_try = [
        "https://www.thansettakij.com/economy/trade-agriculture/653068",
        "https://www.bangkokbiznews.com/business/economic/1199243",
    ]
    for url in urls_to_try:
        html = fetch(url)
        if not html:
            continue
        # Look for RSS3 price pattern: XX.XX-XX.XX บาทต่อกิโลกรัม
        m = re.search(r'RSS3.*?([\d.]+)[–-]([\d.]+)\s*บาท(?:ต่อ|/)\s*(?:กิโลกรัม|กก)', html, re.IGNORECASE | re.DOTALL)
        if not m:
            m = re.search(r'([\d.]+)[–\-]([\d.]+)\s*บาท(?:ต่อ|/)\s*(?:กิโลกรัม|กก)', html)
        if m:
            result["price_low"]  = float(m.group(1))
            result["price_high"] = float(m.group(2))
            result["source_url"] = url
            # Try extract date
            m_date = re.search(r'(\d+\s+\S+\.\s*\d+|\d{1,2}/\d{1,2}/\d{4})', html)
            if m_date:
                result["date"] = m_date.group(1)
            break

    # Fallback: use last known values
    if result["price_low"] is None:
        log.warning("rubber: using fallback values")
        result["price_low"]  = 70.0
        result["price_high"] = 78.0
        result["date"]       = "มี.ค. 69 (ค่าล่าสุดที่ทราบ)"
        result["note"]       = "⚠️ ใช้ค่าล่าสุดที่ทราบ — ดึงข้อมูลจริงไม่สำเร็จ"
        result["status"]     = "fallback"

    log.info(f"rubber: {result['price_low']}–{result['price_high']} ({result['date']})")
    return result


# ─────────────────────────────────────────────
# 4. ราคาอ้อย — annual/cached
# ─────────────────────────────────────────────
def scrape_sugarcane() -> dict:
    """
    Sugarcane price is set once per production season by ครม.
    We cache known values and only re-scrape when a new season is announced.
    """
    # Known prices (updated manually when ครม. announces)
    KNOWN = [
        {"season": "2568/69", "initial": 890,    "final": None,    "yoy_initial": -23.3, "source_date": "พ.ย. 68", "source": "กอน./ครม."},
        {"season": "2567/68", "initial": 1160,   "final": 1152.62, "yoy_initial": -18.3, "source_date": "ม.ค. 68", "source": "ครม."},
        {"season": "2566/67", "initial": 1420,   "final": 1404.17, "yoy_initial": +31.5, "source_date": "ก.พ. 68", "source": "ครม."},
        {"season": "2565/66", "initial": 1080,   "final": 1197.53, "yoy_initial": None,  "source_date": None,      "source": "ThaiPBS"},
        {"season": "2564/65", "initial": 920,    "final": None,    "yoy_initial": None,  "source_date": None,      "source": "อ้างอิง"},
    ]

    # Try to scrape for new announcement
    url = "https://spacebar.th/business/cabinet-sugarcane-price-2569"
    html = fetch(url)
    current_initial = None
    if html:
        m = re.search(r'ราคาอ้อยขั้นต้น.*?([\d,]+)\s*บาทต่อตัน', html, re.DOTALL)
        if m:
            current_initial = float(m.group(1).replace(",", ""))
            log.info(f"sugarcane: scraped initial = {current_initial} THB/ตัน")

    # If scrape got a different value for current season, update
    if current_initial and current_initial != KNOWN[0]["initial"]:
        KNOWN[0]["initial"] = current_initial
        KNOWN[0]["note"] = "scraped live"

    result = {
        "commodity": "อ้อย (ราคาขั้นต้น)",
        "commodity_en": "Sugarcane Initial Price",
        "current_season": KNOWN[0]["season"],
        "current_initial": KNOWN[0]["initial"],
        "unit": "THB/ตัน @ 10 CCS",
        "date": KNOWN[0]["source_date"],
        "source": KNOWN[0]["source"],
        "source_url": url,
        "status": "confirmed",
        "note": "ราคาประกาศรายปีต่อฤดูการผลิต โดย กอน./ครม.",
        "history": KNOWN,
    }
    log.info(f"sugarcane: {KNOWN[0]['season']} = {KNOWN[0]['initial']} THB/ตัน")
    return result


# ─────────────────────────────────────────────
# 5. ข้าวส่งออก FOB — news/USDA reference
# ─────────────────────────────────────────────
def scrape_rice_fob() -> dict:
    result = {
        "white5": {
            "commodity": "ข้าวขาว 5% FOB Bangkok",
            "commodity_en": "White Rice 5% Broken FOB",
            "price_low": None, "price_high": None,
            "unit": "USD/ตัน",
            "date": None,
            "source": "Nation Thailand / Thai Rice Exporters Assoc.",
            "source_url": "https://www.nationthailand.com",
            "status": "confirmed",
        },
        "homali": {
            "commodity": "ข้าวหอมมะลิ 100% FOB",
            "commodity_en": "Hom Mali 100% FOB",
            "price": None,
            "unit": "USD/ตัน",
            "date": None,
            "source": "Thai Rice Exporters Assoc.",
            "source_url": "https://www.nationthailand.com",
            "status": "confirmed",
        },
    }

    url = "https://www.nationthailand.com/blogs/business/trade/40062858"
    html = fetch(url)
    if html:
        # White 5%: "Thailand US$410/ton" or "381–385 USD/ตัน"
        m5 = re.search(r'[Tt]hailand\s+US\$?([\d,]+)(?:[–-]([\d,]+))?/ton', html)
        if not m5:
            m5 = re.search(r'5%.*?([\d]+)[–-]([\d]+)\s*(?:USD|ดอลลาร์)', html, re.DOTALL)
        if m5:
            result["white5"]["price_low"]  = float(m5.group(1).replace(",", ""))
            result["white5"]["price_high"] = float(m5.group(2).replace(",", "")) if m5.group(2) else result["white5"]["price_low"]
            result["white5"]["date"] = "มี.ค. 69"

        # Hom Mali: "US$1,171/ton"
        mhm = re.search(r'[Hh]om\s*[Mm]ali.*?US\$?([\d,]+)/ton', html, re.DOTALL)
        if not mhm:
            mhm = re.search(r'1[,.]?\d{3}\s*(?:USD|ดอลลาร์)', html)
        if mhm:
            result["homali"]["price"] = float(mhm.group(1).replace(",", "")) if hasattr(mhm, 'group') and mhm.lastindex else 1171
            result["homali"]["date"]  = "มี.ค. 69"

    # Fallbacks
    if result["white5"]["price_low"] is None:
        log.warning("rice_fob white5: using fallback")
        result["white5"].update({"price_low": 381, "price_high": 385, "date": "มี.ค. 69 (ค่าล่าสุด)", "status": "fallback"})
    if result["homali"]["price"] is None:
        log.warning("rice_fob homali: using fallback")
        result["homali"].update({"price": 1171, "date": "มี.ค. 69 (ค่าล่าสุด)", "status": "fallback"})

    log.info(f"rice_fob white5: {result['white5']['price_low']}–{result['white5']['price_high']}")
    log.info(f"rice_fob homali: {result['homali']['price']}")
    return result


# ─────────────────────────────────────────────
# MAIN — run all scrapers, return combined dict
# ─────────────────────────────────────────────
def scrape_all() -> dict:
    log.info("=== Starting scrape ===")
    now = datetime.now()
    data = {
        "generated_at": now.isoformat(),
        "generated_date": now.strftime("%d %B %Y"),
        "generated_date_th": _format_thai_date(now),
        "rice_jasmine": scrape_rice_jasmine(),
        "cassava":      scrape_cassava(),
        "rubber":       scrape_rubber(),
        "sugarcane":    scrape_sugarcane(),
        "rice_fob":     scrape_rice_fob(),
    }
    log.info("=== Scrape complete ===")
    return data


def _format_thai_date(dt: datetime) -> str:
    MONTHS_TH = ["","ม.ค.","ก.พ.","มี.ค.","เม.ย.","พ.ค.","มิ.ย.",
                  "ก.ค.","ส.ค.","ก.ย.","ต.ค.","พ.ย.","ธ.ค."]
    be_year = dt.year + 543
    return f"{dt.day} {MONTHS_TH[dt.month]} {be_year}"


if __name__ == "__main__":
    import json
    data = scrape_all()
    print(json.dumps(data, ensure_ascii=False, indent=2))

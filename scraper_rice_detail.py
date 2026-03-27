"""
scraper_rice_detail.py v2
ดึงราคาข้าวละเอียดจาก 2 แหล่งจริง:
  A) TREA (default_eng.htm) — ราคาส่งออก FOB weekly table
  B) สมาคมโรงสีข้าวไทย PDF — ราคาข้าวสาร + ข้าวเปลือกรายจังหวัด
"""

import re, time, random, logging, urllib.request, urllib.error
from datetime import datetime, timedelta
from typing import Optional

log = logging.getLogger("scraper_rice")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

def fetch(url: str, timeout: int = 20) -> Optional[bytes]:
    """Fetch raw bytes with retry."""
    for attempt in range(3):
        try:
            time.sleep(random.uniform(0.8, 2.0))
            req = urllib.request.Request(url, headers={
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "text/html,application/pdf,*/*;q=0.9",
                "Accept-Language": "en-US,en;q=0.9,th;q=0.8",
                "Referer": "https://www.google.com/",
                "Connection": "keep-alive",
            })
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                if r.info().get("Content-Encoding") == "gzip":
                    import gzip; raw = gzip.decompress(raw)
                return raw
        except Exception as e:
            log.warning(f"  attempt {attempt+1} failed [{url[:50]}]: {e}")
            time.sleep(2 ** attempt)
    return None

def fetch_text(url: str, encoding: str = "utf-8") -> Optional[str]:
    raw = fetch(url)
    if raw is None:
        return None
    for enc in [encoding, "tis-620", "cp874", "latin-1"]:
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


# ═══════════════════════════════════════════════════
# A. TREA FOB — default_eng.htm (English version)
# ═══════════════════════════════════════════════════
def scrape_trea_fob() -> dict:
    """
    Thai Rice Exporters Association weekly FOB table.
    English version: http://www.thairiceexporters.or.th/default_eng.htm
    Table format: Item | date1 | date2 | date3 | date4 (latest = rightmost)
    """
    url = "http://www.thairiceexporters.or.th/default_eng.htm"

    # Fallback: last known values (25 Mar 2026 from screenshot)
    FALLBACK = {
        "date": "25 Mar 2026",
        "source_url": url,
        "source": "Thai Rice Exporters Association (TREA)",
        "scraped": False,
        "items": [
            {"name_th": "ข้าวหอมมะลิ Premium (68/69)",    "name_en": "Thai Hom Mali Premium (2025/26)", "price": 1163, "unit": "USD/MT FOB"},
            {"name_th": "ข้าวหอมมะลิ Premium (67/68)",    "name_en": "Thai Hom Mali Premium (2024/25)", "price": 1273, "unit": "USD/MT FOB"},
            {"name_th": "ปลายข้าวหอมมะลิ A.1 Super",      "name_en": "Thai Hom Mali Broken A.1 Super",  "price": 381,  "unit": "USD/MT FOB"},
            {"name_th": "ข้าวหอมไทย (Thai Fragrant Rice)", "name_en": "Thai Jasmine Rice",               "price": 628,  "unit": "USD/MT FOB"},
            {"name_th": "ข้าวขาว 100% ชั้น 2",            "name_en": "White Rice 100% Grade B",         "price": 387,  "unit": "USD/MT FOB"},
            {"name_th": "ข้าวขาว 5%",                      "name_en": "White Rice 5%",                   "price": 372,  "unit": "USD/MT FOB"},
            {"name_th": "ข้าวขาว 25%",                     "name_en": "White Rice 25%",                  "price": 370,  "unit": "USD/MT FOB"},
            {"name_th": "ปลายข้าวขาว A.1 Super",          "name_en": "White Broken A.1 Super",          "price": 359,  "unit": "USD/MT FOB"},
            {"name_th": "ข้าวเหนียวขาว 10%",               "name_en": "White Glutinous Rice 10%",        "price": 774,  "unit": "USD/MT FOB"},
            {"name_th": "ข้าวนึ่ง 100% ชนิดพิเศษ",        "name_en": "Parboiled Rice 100% Premium",     "price": 403,  "unit": "USD/MT FOB"},
            {"name_th": "ข้าวนึ่ง 100%",                   "name_en": "Parboiled Rice 100%",             "price": 393,  "unit": "USD/MT FOB"},
        ],
        # ข้อมูลเปรียบเทียบนานาชาติ
        "comparison": []
    }

    html = fetch_text(url, "utf-8")
    if not html:
        log.warning("TREA: fetch failed, using fallback")
        return FALLBACK

    # ── Extract latest date (rightmost column header) ──
    dates = re.findall(r'(\d+\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})', html)
    latest_date = dates[-1] if dates else FALLBACK["date"]

    # ── Extract FOB table rows ──
    # Pattern: "Item name | $XXX | $XXX | $XXX | $XXX"
    # We want the last price column (most recent week)
    ITEM_MAP = [
        ("Thai Hom Mali Rice - Premium (crop year 2025/26)", "ข้าวหอมมะลิ Premium (68/69)", "Thai Hom Mali Premium (2025/26)"),
        ("Thai Hom Mali Rice - Premium (crop year 2024/25)", "ข้าวหอมมะลิ Premium (67/68)", "Thai Hom Mali Premium (2024/25)"),
        ("Thai Jasmine Rice",          "ข้าวหอมไทย (Thai Fragrant Rice)", "Thai Jasmine Rice"),
        ("White Rice 100% Grade B",    "ข้าวขาว 100% ชั้น 2",            "White Rice 100% Grade B"),
        ("White Rice 5%",              "ข้าวขาว 5%",                     "White Rice 5%"),
        ("White Rice 25%",             "ข้าวขาว 25%",                    "White Rice 25%"),
        ("White Broken Rice A.1 Super","ปลายข้าวขาว A.1 Super",          "White Broken A.1 Super"),
        ("White Glutinous Rice 10%",   "ข้าวเหนียวขาว 10%",              "White Glutinous Rice 10%"),
        ("Parboiled Rice 100% - Premium","ข้าวนึ่ง 100% ชนิดพิเศษ",     "Parboiled Rice 100% Premium"),
        ("Parboiled Rice 100%\n",      "ข้าวนึ่ง 100%",                  "Parboiled Rice 100%"),
    ]

    scraped_items = []
    for eng_name, name_th, name_en in ITEM_MAP:
        pattern = re.escape(eng_name.strip()) + r'.*?\$(\d+)(?:.*?\$(\d+))?(?:.*?\$(\d+))?(?:.*?\$(\d+))?'
        m = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        if m:
            # Take rightmost non-None group
            prices = [g for g in m.groups() if g]
            if prices:
                scraped_items.append({
                    "name_th": name_th,
                    "name_en": name_en,
                    "price": int(prices[-1]),
                    "unit": "USD/MT FOB"
                })

    # Also try simpler pattern: just find all $ amounts in sequence per row
    if not scraped_items:
        log.warning("TREA: table pattern failed, trying alternative")
        rows = re.findall(r'(White Rice 5%|Thai Hom Mali.*?2025/26|Thai Jasmine|Parboiled 100%)[^\d]*\$?(\d{3,4})', html, re.IGNORECASE)
        for name, price in rows:
            scraped_items.append({"name_th": name, "name_en": name, "price": int(price), "unit": "USD/MT FOB"})

    # ── International comparison table ──
    comparison = []
    comp_patterns = [
        (r'Thailand 5% broken[^\d]*(\d{3,4})',  "Thailand 5%",      "White Rice"),
        (r'Vietnam 5% broken[^\d]*([\d-]+)',     "Vietnam 5%",       "White Rice"),
        (r'India 5% broken[^\d]*([\d-]+)',       "India 5%",         "White Rice"),
        (r'Thailand Hommali 100%[^\d]*(\d{3,4})',"Thailand Hommali", "Fragrant Rice"),
        (r'Vietnam Jasmine[^\d]*([\d-]+)',        "Vietnam Jasmine",  "Fragrant Rice"),
    ]
    for pattern, name, category in comp_patterns:
        m = re.search(pattern, html, re.IGNORECASE)
        if m:
            comparison.append({"name": name, "price_str": m.group(1), "category": category, "unit": "USD/MT"})

    result = {
        "date": latest_date,
        "source_url": url,
        "source": "Thai Rice Exporters Association (TREA)",
        "scraped": len(scraped_items) > 0,
        "items": scraped_items if scraped_items else FALLBACK["items"],
        "comparison": comparison,
    }

    log.info(f"TREA: {len(result['items'])} items | date={result['date']} | scraped={result['scraped']}")
    return result


# ═══════════════════════════════════════════════════
# B. สมาคมโรงสีข้าวไทย PDF — auto-find latest
# ═══════════════════════════════════════════════════

MONTHS_TH_TO_NUM = {
    "มกราคม": "01", "กุมภาพันธ์": "02", "มีนาคม": "03",
    "เมษายน": "04", "พฤษภาคม": "05", "มิถุนายน": "06",
    "กรกฎาคม": "07", "สิงหาคม": "08", "กันยายน": "09",
    "ตุลาคม": "10", "พฤศจิกายน": "11", "ธันวาคม": "12",
}
BASE_PDF_URL = "http://www.thairicemillers.org/images/introc_1429264173/Pricerice{DDMMYYYY}.pdf"

def _candidate_pdf_dates() -> list:
    """Generate candidate PDF dates: last 5 Fridays (PDF published weekly on Friday)."""
    today = datetime.now()
    candidates = []
    # Go back up to 35 days, collect all Fridays (weekday=4)
    for delta in range(0, 35):
        d = today - timedelta(days=delta)
        if d.weekday() == 4:  # Friday
            be_year = d.year + 543
            candidates.append(d.strftime(f"%d%m{be_year}"))
        if len(candidates) >= 5:
            break
    return candidates

def _parse_pdf_text(text: str) -> dict:
    """Extract price data from PDF text (handles double-char OCR artifacts)."""
    # Clean double characters: ข้าข้ว → ข้าว, ชั้นชั้ → ชั้น etc.
    def clean(s):
        # Remove repeated syllables from OCR
        s = re.sub(r'(\S{2,})\1', r'\1', s)
        return s

    result = {
        "milled_rice": [],
        "paddy_white": [],
        "paddy_jasmine": [],
        "paddy_sticky": [],
        "paddy_pathum": [],
    }

    # ── ราคาข้าวสารขายส่ง ──
    MILLED_ITEMS = [
        (r"หอมมะลิ 100% ชั้น\s*2\s*\(68/69\)[^0-9]*([\d,]+)\s*-\s*([\d,]+)",
         "ข้าวหอมมะลิ 100% ชั้น 2 (68/69)", "Hom Mali 100% Grade 2 (68/69)"),
        (r"หอมมะลิ 100% ชั้น\s*2\s*\(67/68\)[^0-9-]*(-?)",
         "ข้าวหอมมะลิ 100% ชั้น 2 (67/68)", "Hom Mali 100% Grade 2 (67/68)"),
        (r"ปลายข้าวหอมมะลิ.*?\(68/69\)[^0-9]*([\d,]+)(?:\s*-\s*([\d,]+))?",
         "ปลายข้าวหอมมะลิ (68/69)", "Hom Mali Broken (68/69)"),
        (r"หอมปทุม.*?ยิงสี[^0-9]*([\d,]+)\s*-\s*([\d,]+)",
         "ข้าวหอมปทุมยิงสี", "Hom Pathum Yingsee"),
        (r"ข้าวขาว 5%[^0-9]*([\d,]+)\s*-\s*([\d,]+)",
         "ข้าวขาว 5%", "White Rice 5%"),
        (r"ข้าว กข 79[^0-9]*([\d,]+)\s*-\s*([\d,]+)",
         "ข้าว กข 79", "Rice KKhaw 79"),
        (r"เหนียว.*?กข\.6.*?68/69[^0-9]*([\d,]+)\s*-\s*([\d,]+)",
         "ข้าวเหนียว กข.6 อีสาน (68/69)", "Sticky Rice KKhaw 6 (68/69)"),
        (r"นึ่ง.*?100%.*?สีอ่อน[^0-9]*([\d,]+)\s*-\s*([\d,]+)",
         "ข้าวนึ่ง 100% สีอ่อน", "Parboiled 100% Light Color"),
    ]

    for pattern, name_th, name_en in MILLED_ITEMS:
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if m and m.lastindex and m.group(1) and m.group(1) != '-':
            try:
                lo = int(m.group(1).replace(",", ""))
                hi = int(m.group(2).replace(",", "")) if m.lastindex >= 2 and m.group(2) else lo
                result["milled_rice"].append({
                    "name_th": name_th, "name_en": name_en,
                    "price_low": lo, "price_high": hi, "unit": "THB/100กก."
                })
            except (ValueError, AttributeError):
                pass

    # ── ข้าวเปลือกเจ้า รายจังหวัด (ชื้น 15%) ──
    # Pattern: province name followed by price range
    province_pattern = r'(กรุงเทพ|กาญจนบุรี|ฉะเชิงเทรา|ชัยนาท|นครนายก|นนทบุรี|นครปฐม|ปทุมธานี|เพชรบุรี|ลพบุรี|สิงห์บุรี|สุพรรณบุรี|ราชบุรี|อยุธยา|กำแพงเพชร|พิจิตร|นครสวรรค์|พิษณุโลก|เพชรบูรณ์|อุตรดิตถ์)[^\d]*([\d,]+)-([\d,]+)'
    for m in re.finditer(province_pattern, text, re.IGNORECASE):
        try:
            result["paddy_white"].append({
                "province": m.group(1),
                "price_low":  int(m.group(2).replace(",", "")),
                "price_high": int(m.group(3).replace(",", "")),
            })
        except ValueError:
            pass

    # ── ข้าวเปลือกหอมมะลิ รายจังหวัด (ชื้น 15%) ──
    jasmine_provinces = r'(บุรีรัมย์|นครราชสีมา|ร้อยเอ็ด|ขอนแก่น|ยโสธร|อุดรธานี|อุบลราชธานี|ศรีสะเกษ|สุรินทร์)[^\d]*([\d,]+)-([\d,]+)'
    for m in re.finditer(jasmine_provinces, text, re.IGNORECASE):
        try:
            result["paddy_jasmine"].append({
                "province": m.group(1),
                "price_low":  int(m.group(2).replace(",", "")),
                "price_high": int(m.group(3).replace(",", "")),
            })
        except ValueError:
            pass

    # ── ข้าวเปลือกเหนียว ──
    sticky_pat = r'(ขอนแก่น|อุดรธานี).*?68/69[^\d]*([\d,]+)-([\d,]+)'
    for m in re.finditer(sticky_pat, text, re.IGNORECASE | re.DOTALL):
        try:
            result["paddy_sticky"].append({
                "province": f"{m.group(1)} (68/69)",
                "price_low":  int(m.group(2).replace(",", "")),
                "price_high": int(m.group(3).replace(",", "")),
            })
        except ValueError:
            pass

    # ── Summary stats ──
    def stats(items):
        if not items:
            return {}
        lows  = [i["price_low"]  for i in items]
        highs = [i["price_high"] for i in items]
        return {
            "avg": round((sum(lows)+sum(highs)) / (len(lows)+len(highs))),
            "min": min(lows),
            "max": max(highs),
        }

    result["paddy_white_stats"]   = stats(result["paddy_white"])
    result["paddy_jasmine_stats"] = stats(result["paddy_jasmine"])

    return result


def scrape_thairicemillers() -> dict:
    """
    Auto-find latest PDF from สมาคมโรงสีข้าวไทย and extract prices.
    PDF URL pattern: Pricerice{DDMMYYYY}.pdf  (published every Friday)
    """
    base_result = {
        "date": None,
        "pdf_url": None,
        "source": "สมาคมโรงสีข้าวไทย",
        "source_url": "http://www.thairicemillers.org/index.php?lay=show&ac=article&Ntype=19",
        "scraped": False,
        "milled_rice": [],
        "paddy_white": [],
        "paddy_jasmine": [],
        "paddy_sticky": [],
        "paddy_white_stats": {},
        "paddy_jasmine_stats": {},
    }

    # Try each candidate Friday date
    for date_str in _candidate_pdf_dates():
        pdf_url = BASE_PDF_URL.format(DDMMYYYY=date_str)
        log.info(f"TRM: trying PDF {date_str} → {pdf_url}")
        raw = fetch(pdf_url)
        if raw is None or len(raw) < 1000:
            continue

        # Extract text from PDF
        try:
            import subprocess, tempfile, os
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(raw)
                tmp_path = f.name
            result_proc = subprocess.run(
                ["python3", "-c",
                 f"import pdfminer.high_level; print(pdfminer.high_level.extract_text('{tmp_path}'))"],
                capture_output=True, text=True, timeout=30
            )
            text = result_proc.stdout
            os.unlink(tmp_path)
        except Exception:
            # fallback: decode raw bytes as text
            text = raw.decode("utf-8", errors="replace")

        if not text or len(text) < 100:
            continue

        # Parse the text
        parsed = _parse_pdf_text(text)
        if parsed["milled_rice"] or parsed["paddy_white"]:
            base_result.update(parsed)
            base_result["date"]    = date_str  # DDMMYYYY BE
            base_result["pdf_url"] = pdf_url
            base_result["scraped"] = True
            log.info(f"TRM: scraped {len(parsed['milled_rice'])} milled + {len(parsed['paddy_white'])} paddy_white | {date_str}")
            break

    # If scrape failed, use hardcoded fallback from PDF user uploaded (20 มี.ค. 69)
    if not base_result["scraped"]:
        log.warning("TRM: scrape failed, using fallback from PDF (20 มี.ค. 2569)")
        base_result.update({
            "date": "20 มี.ค. 2569",
            "pdf_url": None,
            "scraped": False,
            "milled_rice": [
                {"name_th":"ข้าวหอมมะลิ 100% ชั้น 2 (68/69)","name_en":"Hom Mali 100% Grade 2 (68/69)","price_low":3250,"price_high":3416,"unit":"THB/100กก."},
                {"name_th":"ปลายข้าวหอมมะลิ (68/69)","name_en":"Hom Mali Broken (68/69)","price_low":1060,"price_high":1060,"unit":"THB/100กก."},
                {"name_th":"ข้าวหอมปทุมยิงสี","name_en":"Hom Pathum Yingsee","price_low":1750,"price_high":1780,"unit":"THB/100กก."},
                {"name_th":"ข้าวขาว 5%","name_en":"White Rice 5%","price_low":1060,"price_high":1080,"unit":"THB/100กก."},
                {"name_th":"ปลายข้าวขาว A1 เลิศ","name_en":"White Broken A.1 Super","price_low":970,"price_high":1000,"unit":"THB/100กก."},
                {"name_th":"ข้าวนึ่ง 100% สีอ่อน","name_en":"Parboiled 100% Light Color","price_low":1110,"price_high":1130,"unit":"THB/100กก."},
                {"name_th":"ข้าวเหนียว กข.6 อีสาน (68/69)","name_en":"Sticky Rice KKhaw 6 (68/69)","price_low":2300,"price_high":2500,"unit":"THB/100กก."},
                {"name_th":"ข้าว กข 79","name_en":"Rice KKhaw 79","price_low":1370,"price_high":1420,"unit":"THB/100กก."},
            ],
            "paddy_white": [
                {"province":"กรุงเทพฯ","price_low":6900,"price_high":7300},
                {"province":"กาญจนบุรี","price_low":7200,"price_high":7600},
                {"province":"ฉะเชิงเทรา","price_low":7100,"price_high":7500},
                {"province":"ชัยนาท","price_low":7000,"price_high":7400},
                {"province":"นครสวรรค์","price_low":7200,"price_high":7600},
                {"province":"อยุธยา","price_low":7100,"price_high":7500},
                {"province":"สุพรรณบุรี","price_low":7100,"price_high":7500},
                {"province":"ลพบุรี","price_low":7100,"price_high":7500},
                {"province":"พิษณุโลก","price_low":7100,"price_high":7500},
                {"province":"เพชรบูรณ์","price_low":7200,"price_high":7600},
            ],
            "paddy_jasmine": [
                {"province":"บุรีรัมย์","price_low":16700,"price_high":17200},
                {"province":"นครราชสีมา","price_low":16500,"price_high":17200},
                {"province":"ร้อยเอ็ด","price_low":16000,"price_high":17000},
                {"province":"ขอนแก่น","price_low":15800,"price_high":17200},
                {"province":"ยโสธร","price_low":16500,"price_high":17500},
                {"province":"อุดรธานี","price_low":15500,"price_high":16700},
                {"province":"อุบลราชธานี","price_low":16500,"price_high":17000},
                {"province":"ศรีสะเกษ","price_low":16500,"price_high":17500},
                {"province":"สุรินทร์","price_low":16500,"price_high":17000},
            ],
            "paddy_sticky": [
                {"province":"ขอนแก่น (68/69)","price_low":11600,"price_high":12100},
                {"province":"อุดรธานี (68/69)","price_low":11500,"price_high":12000},
            ],
            "paddy_white_stats":   {"avg":7300,"min":6900,"max":7600},
            "paddy_jasmine_stats": {"avg":16711,"min":15500,"max":17500},
        })

    return base_result


def scrape_rice_detail() -> dict:
    return {
        "trea_fob":        scrape_trea_fob(),
        "thai_rice_mills": scrape_thairicemillers(),
    }


if __name__ == "__main__":
    import json, logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    data = scrape_rice_detail()
    print(f"\nTREA scraped={data['trea_fob']['scraped']} | {data['trea_fob']['date']}")
    print(f"TRM  scraped={data['thai_rice_mills']['scraped']} | {data['thai_rice_mills']['date']}")
    print(f"TREA items: {len(data['trea_fob']['items'])}")
    print(f"TRM milled: {len(data['thai_rice_mills']['milled_rice'])}")
    print(f"TRM paddy_white: {len(data['thai_rice_mills']['paddy_white'])}")
    print(f"TRM paddy_jasmine: {len(data['thai_rice_mills']['paddy_jasmine'])}")

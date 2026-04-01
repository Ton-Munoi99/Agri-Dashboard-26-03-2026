"""
scraper.py — Thai Agricultural Price Scraper (v2 — anti-bot bypass)
"""

import re
import json
import time
import random
import logging
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("scraper")

# ─── rotate user-agents เพื่อหลีกเลี่ยง block ───────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

def get_headers(referer: str = "https://www.google.com/") -> dict:
    # Referer must be ASCII-safe for urllib (encode Thai chars)
    safe_referer = referer.encode("ascii", errors="ignore").decode("ascii")
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "th-TH,th;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": safe_referer,
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Cache-Control": "max-age=0",
    }

def fetch(url: str, timeout: int = 20, referer: str = "https://www.google.com/") -> Optional[str]:
    """Fetch URL with retry + random delay."""
    for attempt in range(3):
        try:
            # random delay 1-3 วินาที ดูเหมือน human
            time.sleep(random.uniform(1.0, 3.0))
            req = urllib.request.Request(url, headers=get_headers(referer))
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                # handle gzip
                if r.info().get("Content-Encoding") == "gzip":
                    import gzip
                    raw = gzip.decompress(raw)
                enc = r.headers.get_content_charset() or "utf-8"
                text = raw.decode(enc, errors="replace")
                log.info(f"  ✓ fetched {url[:60]}... ({len(text):,} chars)")
                return text
        except urllib.error.HTTPError as e:
            log.warning(f"  HTTP {e.code} on attempt {attempt+1}: {url[:60]}")
            time.sleep(2 ** attempt)  # exponential backoff
        except Exception as e:
            log.warning(f"  Error on attempt {attempt+1}: {e}")
            time.sleep(2 ** attempt)
    log.warning(f"  ✗ all retries failed: {url[:60]}")
    return None


# ─────────────────────────────────────────────
# 1. ข้าวเปลือกหอมมะลิ 105 — rakakaset.com
# ─────────────────────────────────────────────
def scrape_rice_jasmine() -> dict:
    result = {
        "commodity": "ข้าวเปลือกหอมมะลิ 105",
        "commodity_en": "Jasmine Paddy Rice",
        "price": None, "price_low": None, "price_high": None,
        "unit": "THB/ตัน",
        "date": None,
        "source": "สมาคมโรงสีข้าวไทย (PDF รายสัปดาห์)",
        "source_url": "http://www.thairicemillers.org/index.php?lay=show&ac=article&Ntype=19",
        "history_30d": [],
        "status": "confirmed",
    }

    # ── แหล่งที่ 1: สมาคมโรงสีข้าวไทย PDF (ทำงานได้จริง) ──────────────
    # ใช้ฟังก์ชัน scrape_thairicemillers() จาก scraper_rice_detail โดยตรง
    try:
        from scraper_rice_detail import scrape_thairicemillers
        trm = scrape_thairicemillers()
        if trm.get("scraped") and trm.get("paddy_jasmine"):
            stats = trm.get("paddy_jasmine_stats", {})
            avg   = stats.get("avg")
            lo    = stats.get("min")
            hi    = stats.get("max")
            if avg:
                result["price"]      = avg
                result["price_low"]  = lo
                result["price_high"] = hi
                result["date"]       = trm.get("date", "")
                result["source_url"] = trm.get("source_url", result["source_url"])
                log.info(f"rice_jasmine: {avg} THB/ตัน (avg {lo}–{hi}) | date={result['date']} | source=TRM PDF")
                return result
    except Exception as e:
        log.warning(f"rice_jasmine: TRM import/scrape failed: {e}")

    # ── แหล่งที่ 2: rakakaset.com / OAE (backup) ─────────────────────────
    web_sources = [
        (
            "https://rakakaset.com/%E0%B8%82%E0%B9%89%E0%B8%B2%E0%B8%A7/",
            "https://www.google.com/search?q=ราคาข้าวเปลือกหอมมะลิวันนี้",
        ),
        (
            "https://www.oae.go.th/view/1/%E0%B8%A3%E0%B8%B2%E0%B8%84%E0%B8%B2%E0%B8%AA%E0%B8%B4%E0%B8%99%E0%B8%84%E0%B9%89%E0%B8%B2%E0%B9%80%E0%B8%81%E0%B8%A9%E0%B8%95%E0%B8%A3/TH-TH",
            "https://www.oae.go.th/",
        ),
    ]
    html = None
    for url, referer in web_sources:
        html = fetch(url, referer=referer)
        if html:
            result["source_url"] = url
            result["source"] = "rakakaset.com (อ้าง OAE)"
            break

    if html:
        patterns = [
            r'(\d{2},\d{3}\.\d{2})\s*\n\s*บาท/ตัน',
            r'ราคารับซื้อวันนี้[^0-9]*([\d,]+\.?\d*)\s*\n?\s*บาท/ตัน',
            r'ข้าวเปลือกหอมมะลิ\s*105[^0-9]+(1[4-9],\d{3}(?:\.\d{2})?)',
            r'(1[4-9],\d{3}(?:\.\d{2})?)\s*(?:บาท/ตัน|บาท\s*ต่อ\s*ตัน)',
            r'(1[5-8],\d{3}(?:\.\d{2})?)\s*บาท',
        ]
        for p in patterns:
            m = re.search(p, html)
            if m:
                try:
                    result["price"] = float(m.group(1).replace(",", ""))
                    break
                except ValueError:
                    continue
        m_date = re.search(r'(\d{1,2}\s+(?:ม\.ค\.|ก\.พ\.|มี\.ค\.|เม\.ย\.|พ\.ค\.|มิ\.ย\.|ก\.ค\.|ส\.ค\.|ก\.ย\.|ต\.ค\.|พ\.ย\.|ธ\.ค\.)\s*\d{4})', html)
        if m_date:
            result["date"] = m_date.group(1).strip()

    # ── Fallback ──────────────────────────────────────────────────────────
    if result["price"] is None:
        result.update({"price": 16500, "date": "ค่าล่าสุดที่ทราบ", "status": "fallback"})

    log.info(f"rice_jasmine: {result['price']} THB/ตัน | status={result['status']}")
    return result


# ─────────────────────────────────────────────
# 2. มันสำปะหลัง — nettathai.org
# ─────────────────────────────────────────────
def scrape_cassava() -> dict:
    url = "https://www.nettathai.org/2012-02-06-06-49-09.html"
    result = {
        "cassava_fresh": {
            "commodity": "หัวมันสด เชื้อแป้ง 30% (นครราชสีมา)",
            "commodity_en": "Fresh Cassava 30% Starch",
            "price_low": None, "price_high": None,
            "unit": "THB/กก.", "date": None,
            "source": "สมาคมโรงงานมันสำปะหลัง ภาคอีสาน",
            "source_url": url, "status": "confirmed",
        },
        "cassava_chips": {
            "commodity": "มันเส้น (โกดังผู้ส่งออก อยุธยา)",
            "commodity_en": "Cassava Chips Ayutthaya",
            "price_low": None, "price_high": None,
            "unit": "THB/กก.", "date": None,
            "source": "สมาคมโรงงานมันสำปะหลัง ภาคอีสาน",
            "source_url": url, "status": "confirmed",
        },
    }

    html = fetch(url, referer="https://www.google.com/search?q=ราคามันสำปะหลังวันนี้")
    if not html:
        # fallback values
        result["cassava_fresh"].update({"price_low": 2.85, "price_high": 3.50, "date": "ค่าล่าสุดที่ทราบ", "status": "fallback"})
        result["cassava_chips"].update({"price_low": 7.30, "price_high": 7.50, "date": "ค่าล่าสุดที่ทราบ", "status": "fallback"})
        return result

    # วันที่จาก heading ล่าสุด
    m_date = re.search(r'วันที่\s+(\d+\s+\S+\s+\d+)', html)
    if m_date:
        d = m_date.group(1).strip()
        result["cassava_fresh"]["date"] = d
        result["cassava_chips"]["date"] = d

    # หัวมันสด: หา row เมือง (หรือ row แรกที่มีราคา)
    # รูปแบบ: เมือง | 2.85 - 3.05 | 2.45 - 2.65
    patterns_fresh = [
        r'เมือง\s*\|\s*([\d.]+)\s*[-–]\s*([\d.]+)',
        r'\|\s*([\d.]+)\s*[-–]\s*([\d.]+)\s*\|\s*[\d.]+\s*[-–]',
        r'(2\.[5-9]\d)\s*[-–]\s*(3\.[0-9]\d)',
    ]
    for p in patterns_fresh:
        m = re.search(p, html)
        if m:
            try:
                result["cassava_fresh"]["price_low"]  = float(m.group(1))
                result["cassava_fresh"]["price_high"] = float(m.group(2))
                break
            except (ValueError, IndexError):
                continue

    # มันเส้น อยุธยา
    patterns_chips = [
        r'อยุธยา.*?([\d.]+)\s*[-–]\s*([\d.]+)',
        r'นครหลวง.*?([\d.]+)\s*[-–]\s*([\d.]+)',
        r'(7\.[0-9]\d)\s*[-–]\s*(7\.[0-9]\d)',
    ]
    for p in patterns_chips:
        m = re.search(p, html, re.DOTALL)
        if m:
            try:
                result["cassava_chips"]["price_low"]  = float(m.group(1))
                result["cassava_chips"]["price_high"] = float(m.group(2))
                break
            except (ValueError, IndexError):
                continue

    # fallback ถ้ายังไม่ได้
    if result["cassava_fresh"]["price_low"] is None:
        result["cassava_fresh"].update({"price_low": 2.85, "price_high": 3.50, "date": "ค่าล่าสุดที่ทราบ", "status": "fallback"})
    if result["cassava_chips"]["price_low"] is None:
        result["cassava_chips"].update({"price_low": 7.30, "price_high": 7.50, "date": "ค่าล่าสุดที่ทราบ", "status": "fallback"})

    log.info(f"cassava_fresh: {result['cassava_fresh']['price_low']}–{result['cassava_fresh']['price_high']} | status={result['cassava_fresh']['status']}")
    log.info(f"cassava_chips: {result['cassava_chips']['price_low']}–{result['cassava_chips']['price_high']} | status={result['cassava_chips']['status']}")
    return result


# ─────────────────────────────────────────────
# 3. ยางพารา RSS3
# ─────────────────────────────────────────────
def _scrape_rubber_from_json(url: str, referer: str) -> Optional[dict]:
    """ลอง fetch JSON API สำหรับราคายาง (data.go.th CKAN หรือ API อื่นๆ)."""
    raw_bytes = None
    for attempt in range(2):
        try:
            time.sleep(random.uniform(0.5, 1.5))
            req = urllib.request.Request(url, headers={
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "application/json, */*",
                "Referer": referer,
            })
            with urllib.request.urlopen(req, timeout=15) as r:
                raw_bytes = r.read()
            break
        except Exception as e:
            log.warning(f"  rubber JSON attempt {attempt+1}: {e}")
            time.sleep(2 ** attempt)
    if not raw_bytes:
        return None
    try:
        data = json.loads(raw_bytes)
        records = (data.get("result", {}).get("records") or
                   data.get("records") or
                   data.get("data") or [])
        if not records:
            return None
        latest = records[-1]
        # ลองชื่อ field หลากหลาย
        for k in ("rss3", "RSS3", "price", "Price", "ราคา"):
            if k in latest:
                val = float(str(latest[k]).replace(",", ""))
                if 40 < val < 200:
                    date_val = (latest.get("date") or latest.get("Date") or
                                latest.get("วันที่") or "")
                    return {"price": val, "date": str(date_val)}
    except Exception as e:
        log.warning(f"  rubber JSON parse error: {e}")
    return None


def scrape_rubber() -> dict:
    result = {
        "commodity": "ยางแผ่นรมควัน RSS3",
        "commodity_en": "Rubber RSS3 Domestic",
        "price_low": None, "price_high": None,
        "unit": "THB/กก.", "date": None,
        "source": "กยท. / ราคายางดอทคอม",
        "source_url": "https://www.raot.co.th",
        "status": "confirmed",
    }

    # ── แหล่งที่ 1: data.go.th CKAN API (open government data) ──────────
    # resource_id สำหรับ "ราคายางพาราในประเทศ รายวัน" จาก กยท./OAE
    CKAN_RESOURCES = [
        "https://data.go.th/api/3/action/datastore_search?resource_id=88674e0e-c327-4d8b-8b69-f05696af4de8&limit=5&sort=_id+desc",
        "https://opendata.data.go.th/api/3/action/datastore_search?resource_id=88674e0e-c327-4d8b-8b69-f05696af4de8&limit=5&sort=_id+desc",
    ]
    for api_url in CKAN_RESOURCES:
        r = _scrape_rubber_from_json(api_url, "https://data.go.th/")
        if r:
            result["price_low"]  = r["price"]
            result["price_high"] = r["price"]
            result["date"]       = r["date"]
            result["source"]     = "data.go.th (กยท.)"
            result["source_url"] = "https://data.go.th/"
            log.info(f"rubber: {r['price']} THB/กก. | source=data.go.th")
            return result

    # ── แหล่งที่ 2: rakayang.net — เว็บราคายางอันดับ 1 ─────────────────
    # หน้า index1.php = "ราคายางตลาดจริงในประเทศ" (ไม่ต้อง login)
    html_sources = [
        (
            "http://www.rakayang.net/index1.php",
            "https://www.rakayang.net/",
        ),
        (
            "https://www.rakayang.net/MorningPrice.php",
            "https://www.rakayang.net/",
        ),
        # RAOT official — ยังลองเพราะ GitHub Actions อาจเข้าถึงได้
        (
            "https://www.raot.co.th/ewtadmin/ewt/rubber_eng/rubber2012/menu5_eng.php",
            "https://www.raot.co.th/",
        ),
        (
            "https://www.thainr.com/en/?detail=pr-local",
            "https://www.google.com/search?q=Thailand+rubber+RSS3+price",
        ),
    ]

    for url, referer in html_sources:
        html = fetch(url, referer=referer)
        if not html:
            continue

        patterns = [
            # rakayang.net: "RSS3 XX.XX" หรือ "แผ่นรมควัน 3 XX.XX"
            r'RSS\s*3\s*(?:ชั้น|Grade)?\s*[:\s]*([\d]{2,3}\.[\d]{2})',
            r'แผ่นรมควัน\s*(?:ชั้น|No\.|Grade)?\s*3[^0-9]*([\d]{2,3}\.[\d]{2})',
            # range format
            r'RSS\s*3[^0-9]*([\d]{2,3}\.[\d]{2})[–\-\s]*([\d]{2,3}\.[\d]{2})',
            r'ยางแผ่นรมควัน[^0-9]*([\d]{2,3}\.[\d]{2})',
            r'(?:Ribbed Smoked Sheet|RSS\s*3)[^\d]*([\d]{2,3}\.[\d]{2})(?:[^\d]*([\d]{2,3}\.[\d]{2}))?',
            r'([\d]{2,3}\.[\d]{2})\s*(?:Baht|THB|บาท)/(?:kg|กก|kilogram)',
            r'(6[0-9]\.\d{2}|7[0-9]\.\d{2}|8[0-9]\.\d{2})\s*(?:บาท|Baht)',
        ]
        for p in patterns:
            m = re.search(p, html, re.IGNORECASE | re.DOTALL)
            if m:
                try:
                    result["price_low"]  = float(m.group(1))
                    result["price_high"] = float(m.group(2)) if m.lastindex >= 2 and m.group(2) else float(m.group(1))
                    result["source_url"] = url
                    result["source"]     = "ราคายางดอทคอม / กยท."
                    md = re.search(r'(\d+\s+(?:ม\.ค\.|ก\.พ\.|มี\.ค\.|เม\.ย\.|พ\.ค\.|มิ\.ย\.|ก\.ค\.|ส\.ค\.|ก\.ย\.|ต\.ค\.|พ\.ย\.|ธ\.ค\.)\s*\d+)', html)
                    if not md:
                        md = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', html)
                    if md:
                        result["date"] = md.group(1)
                    break
                except (ValueError, IndexError):
                    continue
        if result["price_low"]:
            break

    if result["price_low"] is None:
        log.warning("rubber: all sources failed, using fallback")
        result.update({"price_low": 70.0, "price_high": 75.0, "date": "ค่าล่าสุดที่ทราบ", "status": "fallback"})

    log.info(f"rubber: {result['price_low']}–{result['price_high']} | status={result['status']}")
    return result


# ─────────────────────────────────────────────
# 4. ราคาอ้อย (annual/cached)
# ─────────────────────────────────────────────
def scrape_sugarcane() -> dict:
    KNOWN = [
        {"season": "2568/69", "initial": 890,    "final": None,    "yoy_initial": -23.3, "source_date": "พ.ย. 68", "source": "กอน./ครม."},
        {"season": "2567/68", "initial": 1160,   "final": 1152.62, "yoy_initial": -18.3, "source_date": "ม.ค. 68", "source": "ครม."},
        {"season": "2566/67", "initial": 1420,   "final": 1404.17, "yoy_initial": +31.5, "source_date": "ก.พ. 68", "source": "ครม."},
        {"season": "2565/66", "initial": 1080,   "final": 1197.53, "yoy_initial": None,  "source_date": None,      "source": "ThaiPBS"},
        {"season": "2564/65", "initial": 920,    "final": None,    "yoy_initial": None,  "source_date": None,      "source": "อ้างอิง"},
    ]

    # ลอง scrape ใหม่ถ้ามีประกาศ
    urls = [
        ("https://spacebar.th/business/cabinet-sugarcane-price-2569", "https://www.google.com/"),
        ("https://www.thaipbs.or.th/news/content/501549", "https://www.thaipbs.or.th"),
    ]
    for url, referer in urls:
        html = fetch(url, referer=referer)
        if html:
            m = re.search(r'ราคาอ้อยขั้นต้น.*?([\d,]+)\s*บาทต่อตัน', html, re.DOTALL)
            if m:
                val = float(m.group(1).replace(",", ""))
                if val != KNOWN[0]["initial"]:
                    KNOWN[0]["initial"] = val
                    log.info(f"sugarcane: updated to {val} THB/ตัน")
                break

    result = {
        "commodity": "อ้อย (ราคาขั้นต้น)",
        "commodity_en": "Sugarcane Initial Price",
        "current_season": KNOWN[0]["season"],
        "current_initial": KNOWN[0]["initial"],
        "unit": "THB/ตัน @ 10 CCS",
        "date": KNOWN[0]["source_date"],
        "source": KNOWN[0]["source"],
        "source_url": "https://spacebar.th/business/cabinet-sugarcane-price-2569",
        "status": "confirmed",
        "note": "ราคาประกาศรายปีต่อฤดูการผลิต โดย กอน./ครม.",
        "history": KNOWN,
    }
    log.info(f"sugarcane: {KNOWN[0]['season']} = {KNOWN[0]['initial']} THB/ตัน")
    return result


# ─────────────────────────────────────────────
# 5. ข้าวส่งออก FOB
# ─────────────────────────────────────────────
def scrape_rice_fob() -> dict:
    result = {
        "white5": {
            "commodity": "ข้าวขาว 5% FOB Bangkok",
            "commodity_en": "White Rice 5% Broken FOB",
            "price_low": None, "price_high": None,
            "unit": "USD/ตัน", "date": None,
            "source": "Nation Thailand / Thai Rice Exporters Assoc.",
            "source_url": "https://www.nationthailand.com",
            "status": "confirmed",
        },
        "homali": {
            "commodity": "ข้าวหอมมะลิ 100% FOB",
            "commodity_en": "Hom Mali 100% FOB",
            "price": None,
            "unit": "USD/ตัน", "date": None,
            "source": "Thai Rice Exporters Assoc.",
            "source_url": "https://www.nationthailand.com",
            "status": "confirmed",
        },
    }

    sources = [
        ("https://www.nationthailand.com/blogs/business/trade/40062858",
         "https://www.google.com/search?q=Thai+rice+export+price+FOB+Bangkok+2026"),
        ("https://ricenewstoday.com/thai-rice-export-prices-soften-amid-stronger-baht-weak-seasonal-demand/",
         "https://www.google.com/"),
    ]

    for url, referer in sources:
        html = fetch(url, referer=referer)
        if not html:
            continue

        # White 5%
        patterns_w5 = [
            r'[Tt]hailand.*?US\$?\s*([\d,]+)(?:[–\-]([\d,]+))?/(?:ton|MT)',
            r'5%.*?(3[5-9]\d|4[0-2]\d)[–\-]?(3[5-9]\d|4[0-2]\d)?\s*(?:USD|US\$)',
            r'(3[6-9]\d|4[0-1]\d)\s*(?:USD|US\$|ดอลลาร์)/(?:ton|ตัน|MT)',
        ]
        for p in patterns_w5:
            m = re.search(p, html, re.IGNORECASE)
            if m:
                try:
                    result["white5"]["price_low"]  = float(m.group(1).replace(",", ""))
                    result["white5"]["price_high"] = float(m.group(2).replace(",", "")) if m.lastindex >= 2 and m.group(2) else result["white5"]["price_low"]
                    result["white5"]["date"] = _extract_date(html) or "มี.ค. 69"
                    break
                except (ValueError, IndexError):
                    continue

        # Hom Mali
        m_hm = re.search(r'[Hh]om\s*[Mm]ali.*?US\$?\s*(1[,.]?\d{3})/(?:ton|MT)', html, re.DOTALL)
        if m_hm:
            result["homali"]["price"] = float(m_hm.group(1).replace(",", ""))
            result["homali"]["date"]  = "มี.ค. 69"

        if result["white5"]["price_low"]:
            break

    # fallback
    if result["white5"]["price_low"] is None:
        result["white5"].update({"price_low": 381, "price_high": 385, "date": "ค่าล่าสุดที่ทราบ", "status": "fallback"})
    if result["homali"]["price"] is None:
        result["homali"].update({"price": 1171, "date": "ค่าล่าสุดที่ทราบ", "status": "fallback"})

    log.info(f"rice_fob white5: {result['white5']['price_low']}–{result['white5']['price_high']} | status={result['white5']['status']}")
    log.info(f"rice_fob homali: {result['homali']['price']} | status={result['homali']['status']}")
    return result


def _extract_date(html: str) -> Optional[str]:
    m = re.search(
        r'(\d{1,2}\s+(?:ม\.ค\.|ก\.พ\.|มี\.ค\.|เม\.ย\.|พ\.ค\.|มิ\.ย\.|ก\.ค\.|ส\.ค\.|ก\.ย\.|ต\.ค\.|พ\.ย\.|ธ\.ค\.)\s*\d{4})',
        html
    )
    return m.group(1) if m else None


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def scrape_all() -> dict:
    log.info("=== Starting scrape v2 ===")
    now = datetime.now()
    data = {
        "generated_at":      now.isoformat(),
        "generated_date":    now.strftime("%d %B %Y"),
        "generated_date_th": _format_thai_date(now),
        "rice_jasmine":      scrape_rice_jasmine(),
        "cassava":           scrape_cassava(),
        "rubber":            scrape_rubber(),
        "sugarcane":         scrape_sugarcane(),
        "rice_fob":          scrape_rice_fob(),
    }
    log.info("=== Scrape complete ===")
    return data


def _format_thai_date(dt: datetime) -> str:
    MONTHS = ["","ม.ค.","ก.พ.","มี.ค.","เม.ย.","พ.ค.","มิ.ย.",
              "ก.ค.","ส.ค.","ก.ย.","ต.ค.","พ.ย.","ธ.ค."]
    return f"{dt.day} {MONTHS[dt.month]} {dt.year + 543}"


if __name__ == "__main__":
    data = scrape_all()
    print(json.dumps(data, ensure_ascii=False, indent=2))

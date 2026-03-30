# 🌾 Agri Price Dashboard

ราคาพืชเศรษฐกิจไทยแบบ real-time — อัปเดตอัตโนมัติทุกวัน 08:00 ICT

**ข้าว · มันสำปะหลัง · ยางพารา · อ้อย**

---

## วิธี deploy (ทำครั้งเดียว ~10 นาที)

### 1. สร้าง GitHub repo

```bash
# สร้าง repo ใหม่บน github.com แล้ว push โค้ดนี้
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/YOUR_USERNAME/agri-price-dashboard.git
git push -u origin main
```

### 2. เปิด GitHub Pages หรือ Netlify

**วิธี A — Netlify (แนะนำ)**
1. ไป https://netlify.com → "Add new site" → "Import from GitHub"
2. เลือก repo นี้
3. ตั้ง **Publish directory** = `docs`
4. กด Deploy — ได้ URL ทันที เช่น `https://agri-prices-xxx.netlify.app`

**วิธี B — GitHub Pages**
1. Settings → Pages → Source = "Deploy from a branch"
2. Branch = `main`, Folder = `/docs`
3. URL จะเป็น `https://USERNAME.github.io/agri-price-dashboard`

**วิธี C — Vercel**
1. ไป https://vercel.com → "Add New Project" → import repo
2. Framework = "Other", Output Directory = `docs`
3. Deploy

### 3. ตรวจสอบ GitHub Actions

- ไปที่ tab **Actions** ใน repo
- จะเห็น workflow "Daily Agri Price Update"
- กด **Run workflow** เพื่อทดสอบครั้งแรก
- หลังจากนั้นจะรันอัตโนมัติทุกวัน 08:00 ICT

---

## โครงสร้างไฟล์

```
agri-price-dashboard/
├── scraper.py          ← ดึงราคาจาก rakakaset, nettathai, ฯลฯ
├── generate_html.py    ← แปลงข้อมูลเป็น HTML dashboard
├── requirements.txt    ← Python dependencies (pdfminer.six สำหรับ scraper_rice_detail.py)
├── .github/
│   └── workflows/
│       └── daily.yml   ← GitHub Actions: รันทุกวัน 08:00 ICT
└── docs/
    ├── index.html      ← ไฟล์ที่ Netlify/Vercel serve (auto-generated)
    └── data.json       ← ข้อมูลดิบล่าสุด (auto-generated)
```

---

## แหล่งข้อมูล

| สินค้า | แหล่ง | ความถี่ |
|---|---|---|
| ข้าวเปลือกหอมมะลิ | rakakaset.com (อ้าง OAE) | รายวัน |
| หัวมันสด + มันเส้น | nettathai.org (สมาคมโรงงานมันฯ ภาคอีสาน) | ทุก 2-3 วัน |
| ยางแผ่นรมควัน RSS3 | ฐานเศรษฐกิจ / กยท. (news) | รายวัน |
| ราคาอ้อย | กอน./สอน./ครม. | รายปีต่อฤดูการผลิต |
| ข้าวส่งออก FOB | Nation Thailand / USDA | รายสัปดาห์ |

---

## อัปเดตราคาอ้อยด้วยตัวเอง

เมื่อ ครม. ประกาศราคาอ้อยฤดูใหม่ ให้แก้ `scraper.py` ที่ `KNOWN` list ใน `scrape_sugarcane()`:

```python
KNOWN = [
    {"season": "2569/70", "initial": XXX, "final": None, ...},  # ← เพิ่มบรรทัดใหม่
    ...
]
```

แล้ว commit ขึ้น GitHub — Actions จะ deploy ให้อัตโนมัติ

---

## รัน manual (local)

```bash
pip install -r requirements.txt   # ติดตั้ง pdfminer.six (ใช้โดย scraper_rice_detail.py)
python generate_html.py         # scrape + generate docs/index.html
python generate_html.py --data docs/data.json  # ใช้ข้อมูลเก่า (ไม่ scrape)
open docs/index.html
```

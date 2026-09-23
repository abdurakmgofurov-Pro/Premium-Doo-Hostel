# -*- coding: utf-8 -*-
"""
Exely Moliyaviy Tizim — ko'p foydalanuvchili veb-ilova (rasmiy API asosida)
==============================================================================
Brauzer avtomatlashtirish yoki fayl yuklab olishsiz — to'g'ridan-to'g'ri
Exely'ning rasmiy Public API (Read Reservation API)'siga ulanadi.

Bo'limlar:
  /            Dashboard (jonli tushum tahlili)
  /bookings    Bronlar ro'yxati
  /transactions  Xarajatlar / kompaniyalar bilan hisob-kitob
  /users       Foydalanuvchilarni boshqarish (faqat Super Admin)
  /settings    API sozlamalari (faqat Super Admin)

Har bir foydalanuvchi login/parol bilan kiradi; huquqlari roliga
(super_admin / admin / custom) qarab belgilanadi.

Ishga tushirish:   py -3 app.py
Ochish:            http://127.0.0.1:5000
"""
import json
import secrets
import sqlite3
import threading
import time
import traceback
from datetime import datetime, date, timedelta
from pathlib import Path

from flask import Flask, jsonify, request, send_file, redirect, url_for, render_template, session, flash, abort, g

import db
from aggregate import aggregate_bookings, flatten as flatten_booking, payment_method_name
from auth import (
    authenticate, current_user, login_required, permission_required, super_admin_required,
    get_csrf_token, csrf_valid,
)
from exely_api import ExelyApiClient
from exely_expense_import import parse_expense_xlsx
from forma1 import build_forma1
from forma2 import build_forma2
from i18n import (
    LANGS, LANG_LABELS, DEFAULT_LANG, t, t_all, t_group, t_cat,
    t_cash_section, t_cash_cat, t_month,
)
from report_excel import build_excel_report, build_cash_excel_report

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
LOG_PATH = BASE_DIR / "run_log.txt"
SECRET_KEY_PATH = BASE_DIR / "secret_key.txt"

app = Flask(__name__)


def format_money(value):
    """Summalarni o'qish oson bo'lishi uchun mingliklarni bo'sh joy bilan
    ajratadi: 200000 -> '200 000.00' (masalan, foydalanuvchi so'ragani kabi)."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return value
    return f"{value:,.2f}".replace(",", " ")


def format_qty(value):
    """Miqdor (dona/litr va h.k.) uchun: butun son bo'lsa kasrsiz, aks holda
    2 xonagacha, mingliklar bo'sh joy bilan ajratilgan holda."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return value
    s = f"{int(value):,}" if value == int(value) else f"{value:,.2f}"
    return s.replace(",", " ")


app.jinja_env.filters["money"] = format_money
app.jinja_env.filters["qty"] = format_qty


def parse_amount(s):
    """Summa maydonlaridan keladigan qiymatni o'qiydi — JS mingliklarni
    bo'sh joy bilan formatlaydi va yuborishdan oldin olib tashlaydi, lekin
    JS ishlamagan holat uchun ham bo'sh joylarni bardosh bilan olib tashlaydi."""
    return float(str(s).replace(" ", "").replace("\xa0", ""))


def rate_missing_for(date_str):
    """Berilgan sanada (yoki undan oldin) valyuta kursi kiritilmagan
    bo'lsa True qaytaradi — pul operatsiyasi kiritishdan oldin kurs
    majburiy ekanini tekshirish uchun."""
    return db.get_exchange_rate_on(date_str) is None
app.jinja_env.filters["t_cat"] = lambda name: t_cat(name, g.lang)
app.jinja_env.filters["t_group"] = lambda key: t_group(key, g.lang)
app.jinja_env.filters["t_cash_section"] = lambda key: t_cash_section(key, g.lang)
app.jinja_env.filters["t_cash_cat"] = lambda name: t_cash_cat(name, g.lang)
app.jinja_env.filters["t_month"] = lambda n: t_month(n, g.lang)
if not SECRET_KEY_PATH.exists():
    SECRET_KEY_PATH.write_text(secrets.token_hex(32), encoding="utf-8")
app.secret_key = SECRET_KEY_PATH.read_text(encoding="utf-8").strip()

STATE_LOCK = threading.Lock()
STATE = {
    "status": "loading",   # loading | ok | error
    "error": None,
    "data": None,           # aggregate_bookings() natijasi
    "excel_path": None,
    "last_attempt": None,
    "last_success": None,
    "progress": None,
}

IMPORT_STASH_LOCK = threading.Lock()
IMPORT_STASH = {}          # upload_id -> {"rows":..., "unique_categories":..., "ts": time.time()}
IMPORT_STASH_TTL = 1800    # 30 daqiqa


def log(msg):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_config():
    with open(CONFIG_PATH, encoding="utf-8-sig") as f:
        cfg = json.load(f)
    if cfg.get("api_client_id", "").startswith("SIZNING") or not cfg.get("api_client_secret"):
        raise RuntimeError(
            "config.json faylida API kalitlari (api_client_id / api_client_secret) "
            "hali to'ldirilmagan. Exely Extranet -> Property settings -> API "
            "connections bo'limidan oling, yoki /settings sahifasidan kiriting."
        )
    return cfg


def refresh_once():
    cfg = load_config()
    with STATE_LOCK:
        STATE["last_attempt"] = datetime.now().isoformat(timespec="seconds")
        STATE["progress"] = {"done": 0, "total": 0}
    try:
        client = ExelyApiClient(cfg["api_client_id"], cfg["api_client_secret"], cfg["property_id"])

        def progress_cb(done, total):
            with STATE_LOCK:
                STATE["progress"] = {"done": done, "total": total}

        # MUHIM: Exely API'ning "modifiedFrom" parametri sinovda hech qanday
        # server-tomon filtrlash ta'sirini bermadi (to'g'ridan-to'g'ri so'rov
        # bilan tekshirildi) — shuning uchun bron RO'YXATI har doim BARCHA
        # bronlarni qaytaradi, lekin bu javob arzon (sahifalab, 1000 tadan) va
        # har bir bron uchun `modifiedDateTime`ni o'zida olib keladi. Qimmat
        # qism — har bir bronning TO'LIQ tafsilotini alohida so'rash — shuning
        # uchun faqat mahalliy keshdagi modifiedDateTime bilan MOS KELMAGAN
        # (yangi yoki o'zgargan) bronlar uchungina tafsilot so'raladi.
        log("Bronlar ro'yxati tekshirilmoqda...")
        summaries = client.list_booking_summaries()
        summary_modified = {s["number"]: s.get("modifiedDateTime") for s in summaries if s.get("number")}
        cached_modified = db.get_cached_modified_map()
        to_fetch = [
            num for num, mod in summary_modified.items()
            if cached_modified.get(num) != mod
        ]

        if to_fetch:
            log(f"{len(to_fetch)} ta yangi/o'zgargan bron topildi, tafsilotlari yuklanmoqda...")
        else:
            log("Yangi/o'zgargan bron topilmadi — kesh dolzarb.")

        updated = client.fetch_bookings_by_number(to_fetch, progress_cb=progress_cb, max_workers=8)
        errors = [b for b in updated if b.get("_error")]
        ok_updated = [b for b in updated if not b.get("_error")]
        if errors:
            log(f"{len(errors)} ta bronni yuklashda xatolik bo'ldi (o'tkazib yuborildi, keyingi "
                f"sinxronizatsiyada modifiedDateTime hali ham mos kelmagani uchun avtomatik qayta uriniladi)")

        db.upsert_bookings(ok_updated, summary_modified)

        bookings = db.load_all_bookings()
        log(f"{len(ok_updated)} ta bron yangilandi/qo'shildi, jami keshda: {len(bookings)} ta")

        agg = aggregate_bookings(bookings)

        output_dir = BASE_DIR / cfg.get("output_dir", "reports")
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"Moliyaviy_hisobot_{datetime.now():%Y-%m-%d_%H%M}.xlsx"
        manual = db.summarize_transactions()
        build_excel_report(agg, manual, out_path)

        with STATE_LOCK:
            STATE["status"] = "ok"
            STATE["error"] = None
            STATE["data"] = agg
            STATE["excel_path"] = str(out_path)
            STATE["last_success"] = datetime.now().isoformat(timespec="seconds")
            STATE["progress"] = None
        log(f"Yangilandi: {agg['total_bookings']} bron, Excel: {out_path.name}")
    except Exception:
        err = traceback.format_exc()
        log("YANGILASH XATOSI:\n" + err)
        with STATE_LOCK:
            STATE["status"] = "error"
            STATE["error"] = err.strip().splitlines()[-1]
            STATE["progress"] = None


def ensure_today_cbu_rate():
    """Bugungi kun uchun Markaziy bank kursi (USD va EUR) hali kiritilmagan
    bo'lsa, avtomatik ravishda cbu.uz'dan olib saqlaydi. Tarmoq xatosida
    indamay o'tkazib yuboriladi — keyingi urinishda (yoki qo'lda) qayta
    olinadi."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    rates = db.list_exchange_rates()
    today_row = rates[0] if rates and rates[0]["date"] == today_str else None
    if not today_row or not today_row["uzs_per_usd"]:
        try:
            rate = db.fetch_cbu_rate(today_str, "USD")
            db.set_exchange_rate(today_str, rate, "USD")
        except Exception:
            pass
    if not today_row or not today_row["uzs_per_eur"]:
        try:
            rate = db.fetch_cbu_rate(today_str, "EUR")
            db.set_exchange_rate(today_str, rate, "EUR")
        except Exception:
            pass


def background_loop():
    while True:
        try:
            cfg = load_config()
            interval = int(cfg.get("refresh_minutes", 20)) * 60
        except Exception:
            interval = 20 * 60
        refresh_once()
        ensure_today_cbu_rate()
        time.sleep(interval)


# ---- Til (i18n) ----

@app.before_request
def set_lang():
    lang = session.get("lang")
    if lang not in LANGS:
        lang = DEFAULT_LANG
        session["lang"] = lang
    g.lang = lang
    cur = session.get("display_currency")
    if cur not in ("UZS", "USD"):
        cur = "UZS"
        session["display_currency"] = cur
    g.display_currency = cur


@app.before_request
def check_csrf():
    """Har bir holat o'zgartiruvchi (POST) so'rov uchun CSRF tokenini
    tekshiradi — formalar orqali kelgan token `base.html`dagi umumiy JS
    tomonidan avtomatik qo'shiladi, `fetch()` orqali yuborilgan so'rovlar
    esa `X-CSRFToken` headerini o'zi qo'shishi kerak (masalan
    dashboard.html'dagi "Yangilash" tugmasi)."""
    if request.method == "POST" and not csrf_valid(request):
        abort(400)


@app.route("/set_language/<lang>")
def set_language(lang):
    if lang in LANGS:
        session["lang"] = lang
    return redirect(request.referrer or url_for("index"))


@app.route("/set_display_currency/<cur>")
def set_display_currency(cur):
    if cur in ("UZS", "USD"):
        session["display_currency"] = cur
    return redirect(request.referrer or url_for("index"))


def to_display_amount(uzs, usd, rate):
    """Ikkala valyutadagi summani foydalanuvchi tanlagan YAGONA ko'rsatish
    valyutasiga aylantiradi (joriy kunlik kursga asosan). Kurs bo'lmasa,
    boshqa valyutadagi qism e'tiborga olinmaydi (0 deb hisoblanadi) —
    xato chiqarish o'rniga xavfsiz fallback (chaqiruvchi sahifalar
    `rate` bo'sh bo'lsa alohida ogohlantirish ko'rsatadi)."""
    cur = getattr(g, "display_currency", "UZS")
    uzs = uzs or 0
    usd = usd or 0
    if cur == "USD":
        return usd + (uzs / rate if rate else 0)
    return uzs + (usd * rate if rate else 0)


# ---- Autentifikatsiya ----

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = authenticate(request.form.get("username", ""), request.form.get("password", ""))
        if user:
            session["user_id"] = user["id"]
            return redirect(request.args.get("next") or url_for("index"))
        flash(t("flash.login_failed", g.lang), "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.context_processor
def inject_user():
    u = current_user()
    role_name = None
    if u and u["role"] != "super_admin" and u.get("role_id"):
        role = db.get_role(u["role_id"])
        role_name = role["name"] if role else None
    return {
        "current_user": u,
        "current_user_role_name": role_name,
        "has_perm": lambda module, action: db.has_permission(u, module, action),
        "t": lambda key: t(key, g.lang),
        "t_group": lambda key: t_group(key, g.lang),
        "t_cat": lambda name: t_cat(name, g.lang),
        "t_cash_section": lambda key: t_cash_section(key, g.lang),
        "t_cash_cat": lambda name: t_cash_cat(name, g.lang),
        "t_month": lambda n: t_month(n, g.lang),
        "LANG": g.lang,
        "LANGS": LANGS,
        "LANG_LABELS": LANG_LABELS,
        "T_JSON": json.dumps(t_all(g.lang), ensure_ascii=False),
        "is_date_locked": db.is_date_locked,
        "csrf_token": get_csrf_token,
        "display_currency": g.display_currency,
        "to_display": lambda uzs, usd, rate: to_display_amount(uzs, usd, rate),
        "counterparty_options": [
            (f"{cp['name']} {cp['inn']}".strip() if cp["inn"] else cp["name"])
            for cp in db.list_counterparties()
        ],
    }


# ---- Davr (oy/yil) filtri — bir necha sahifada umumiy ----

def get_period():
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    return year, month


def available_years():
    months = db.list_relevant_months()
    years = sorted({int(m[:4]) for m in months}, reverse=True)
    return years or [datetime.now().year]


def bookings_for_period(year, month):
    raw = [b for b in db.load_all_bookings() if not b.get("_error")]
    if not (year and month):
        return raw
    prefix = f"{int(year):04d}-{int(month):02d}"
    result = []
    for b in raw:
        flat = flatten_booking(b)
        if flat.get("arrival") and flat["arrival"][:7] == prefix:
            result.append(b)
    return result


def bookings_recognized_upto_today():
    """Forma 1/2'ning "Barcha vaqt" (davr tanlanmagan) ko'rinishi uchun:
    kelish sanasi hali kelmagan (mehmon hali kelmagan) bronlar bu yerga
    KIRMAYDI — cumulative_net_profit()/booking_receivables() bilan bir xil
    IFRS 15 sababiga ko'ra (mehmon kelmaguncha daromad tan olinmaydi).
    Bronlar ro'yxati (/bookings) va Dashboard'ning boshqa ko'rsatkichlari
    (kanal, oy bo'yicha grafik) uchun bu cheklov qo'llanilmaydi — ular
    "kelajakda nechta bron bor" ma'lumotini ko'rsatishi kerak, faqat
    moliyaviy hisobotlarda tan olingan daromad chegaralanadi."""
    today = date.today().strftime("%Y-%m-%d")
    raw = [b for b in db.load_all_bookings() if not b.get("_error")]
    return [b for b in raw if flatten_booking(b).get("arrival", "")[:10] <= today]


def cumulative_net_profit(upto_date):
    """Forma 1'dagi "Taqsimlanmagan foyda" qatori uchun: davr boshidan
    (barcha ma'lumot mavjud bo'lgan eng birinchi kundan) berilgan sanagacha
    JAMLANGAN sof foyda — bitta oyning emas, balki BUGUNGI holatning
    balansini ko'rsatishi kerak.

    `upto_date=None` — "bugungi holat" degani, "cheksiz" degani emas: kelish
    sanasi hali kelmagan (mehmon hali kelmagan) bronlarning daromadi bu yerda
    ERTA tan olinmasligi kerak (IFRS 15/ASC 606 — mehmon kelmaguncha bu pul
    daromad emas, avans/majburiyat). Shu sabab `upto_date` bo'lmasa,
    kesim sifatida BUGUNGI sana ishlatiladi, cheksiz emas."""
    raw = [b for b in db.load_all_bookings() if not b.get("_error")]
    cutoff = upto_date or date.today().strftime("%Y-%m-%d")
    filtered = [b for b in raw if flatten_booking(b).get("arrival", "")[:10] <= cutoff]
    agg = aggregate_bookings(filtered)
    manual = db.summarize_transactions_upto(upto_date)
    f2 = build_forma2(agg, manual)
    uzs = next((r["uzs"] for r in f2 if r["key"] == "f2.100"), 0.0)
    usd = next((r["usd"] for r in f2 if r["key"] == "f2.100"), 0.0)
    return uzs, usd


OTA_PAYMENT_METHOD = payment_method_name("ExternalSystem")


def _booking_owed_parts(flat):
    """Bitta bron uchun ikkita alohida qarz manbaini ajratadi:
    - guest_owed: mehmon o'zi hali to'lamagan qism (revenue - prepaid);
    - platform_owed: mehmon OTA (Booking.com/Airbnb va h.k.) orqali
      "to'lagan" deb Exely'da belgilangan, lekin bu pul hali bizning
      Kassa/Bank'ga kirim qilinmagan qism (prepaid, agar to'lov usuli
      "Tashqi tizim (OTA/onlayn to'lov)" bo'lsa) — chunki bu pulni
      OTA platformasi hali bizga o'tkazib bermagan bo'lishi mumkin."""
    revenue = flat.get("revenue") or 0.0
    prepaid = flat.get("prepaid") or 0.0
    guest_owed = revenue - prepaid
    platform_owed = prepaid if (flat.get("payment_method") == OTA_PAYMENT_METHOD and prepaid > 0) else 0.0
    return max(guest_owed, 0.0), platform_owed


def booking_receivables(upto_date):
    """Forma 1'dagi "Дебиторская задолженность" uchun: Exely'dan kelgan
    Active bronlarning mehmon hali to'lamagan qismi (revenue - prepaid).

    Eslatma: OTA orqali "to'landi" deb belgilangan (platform_owed) qismi
    ATAYLAB bu yerga QO'SHILMAYDI — chunki amalda bu pulning katta qismi
    keyinchalik Kassa/Bank'ga umumiy (bron bilan bog'lanmagan) kirim
    sifatida allaqachon kiritilgan bo'ladi; buni Forma 1'ga qo'shib
    ko'rish real tekshiruvda balansni tuzatish o'rniga yana ham battar
    buzganini ko'rsatdi (haqiqiy bank ko'chirmasi bilan solishtirmasdan
    qay bir OTA to'lovi "hali kelmagan"ligini ishonchli ajratib
    bo'lmaydi). Shu sabab platform_owed faqat Дт/Кт'da (channel_platform_debts)
    KO'RISH uchun ko'rsatiladi, Forma 1 balansiga ta'sir qilmaydi.

    `upto_date=None` — "bugungi holat" (cheksiz emas): kelish sanasi hali
    kelmagan bronlar uchun ham daromad tan olinmaydi (cumulative_net_profit
    bilan bir xil sabab), demak ularga "qarz" ham hisoblanmasligi kerak —
    aks holda aktiv (debitorlik) hisoblanib, unga mos passiv (daromad)
    hisoblanmay qolib, balansni yanada buzardi."""
    raw = [b for b in db.load_all_bookings() if not b.get("_error")]
    cutoff = upto_date or date.today().strftime("%Y-%m-%d")
    raw = [b for b in raw if flatten_booking(b).get("arrival", "")[:10] <= cutoff]
    uzs = usd = 0.0
    skipped = 0
    for b in raw:
        flat = flatten_booking(b)
        if flat.get("status") != "Active":
            continue
        guest_owed, _ = _booking_owed_parts(flat)
        if guest_owed <= 0:
            continue
        cur = flat.get("currency") or "UZS"
        if cur not in ("UZS", "USD"):
            # Kurs hech qachon topilmagani uchun UZS'ga aylantirilmagan
            # xom valyutadagi (masalan EUR) bron — Forma 1'ga qo'shib
            # bo'lmaydi, lekin jim yo'qotib yuborish o'rniga sanab,
            # shablonda ogohlantirish ko'rsatish uchun qaytariladi.
            skipped += 1
            continue
        if cur == "USD":
            usd += guest_owed
        else:
            uzs += guest_owed
    return uzs, usd, skipped


def customer_advances(upto_date):
    """Forma 1'dagi "Mijozlardan olingan avanslar" (majburiyat/Kt) uchun —
    IFRS 15 qoidasi: mehmon oldindan to'lagan, lekin xizmat (turar joy)
    hali ko'rsatilmagan (kelish sanasi hali kelmagan) pul — bu DAROMAD
    emas, MAJBURIYAT. `cumulative_net_profit()`/`booking_receivables()`
    bunday bronlarni ATAYLAB daromaddan/debitorlikdan chiqarib tashlaydi
    (chunki xizmat hali ko'rsatilmagan) — lekin shu pulning o'zi (agar
    HAQIQIY Kassa to'lovi tasdiqlangan bo'lsa, `booking_real_settlement`
    orqali) baribir bizning Kassa/Bank'imizda yotibdi. Shu funksiya o'sha
    summani aynan shu — majburiyat — sifatida qaytaradi, aks holda u
    aktivda (pul) bor-u, passivda hech qanday izsiz qolib, balansni
    buzardi. Faqat ISBOTLANGAN (haqiqiy to'lov) bronlar hisoblanadi —
    Exely'ning o'z ishonchsiz "prepaid" taxminiga tayanilmaydi."""
    cutoff = upto_date or date.today().strftime("%Y-%m-%d")
    settlements = db.get_booking_real_settlements()
    raw = [b for b in db.load_all_bookings() if not b.get("_error")]
    uzs = usd = 0.0
    for b in raw:
        number = b.get("number")
        settled = settlements.get(number)
        if not settled:
            continue
        flat = flatten_booking(b)
        if flat.get("status") != "Active":
            continue
        arrival = (flat.get("arrival") or "")[:10]
        if not arrival or arrival <= cutoff:
            continue
        uzs += settled.get("UZS", 0.0)
        usd += settled.get("USD", 0.0)
    return uzs, usd


def daily_reconciliation():
    """"Night audit" tamoyili (xalqaro mehmonxona amaliyoti): har bir kun
    uchun Exely tan olingan daromadni (kelish sanasi bo'yicha, haqiqiy
    to'lov bilan tuzatilgan) haqiqiy Kassa+Bank kirimi bilan solishtiradi.
    Ikkalasi mustaqil manba — mos kelishi shart emas (Exely — qachon
    xizmat ko'rsatilgani, Kassa/Bank — qachon pul kelgani), lekin katta
    va doimiy farq bo'lsa, buni sezish uchun.

    Faqat BUGUNGI kungacha bo'lgan kunlar solishtiriladi — hali sodir
    bo'lmagan (kelajakdagi) kelish sanalari uchun "farq" tabiiy va
    ma'nosiz shovqin bo'lardi (mehmon hali kelmagan, pul ham hali
    kelmagan — ikkalasi ham nolga yaqin bo'lishi kerak emas)."""
    today = date.today().strftime("%Y-%m-%d")
    raw = [b for b in db.load_all_bookings() if not b.get("_error")]
    exely_by_day = {}
    for b in raw:
        flat = flatten_booking(b)
        if flat.get("status") != "Active":
            continue
        arrival = (flat.get("arrival") or "")[:10]
        cur = flat.get("currency") or "UZS"
        if not arrival or arrival > today or cur not in ("UZS", "USD"):
            continue
        bucket = exely_by_day.setdefault(arrival, {"UZS": 0.0, "USD": 0.0})
        bucket[cur] += flat.get("revenue") or 0.0

    cash_by_day = {}
    for r in db.list_cash_transactions():
        bucket = cash_by_day.setdefault(r["date"], {"income": 0.0, "expense": 0.0})
        bucket[r["type"]] += r["amount"]

    rows = []
    for d in sorted(set(exely_by_day) | set(cash_by_day), reverse=True):
        ex = exely_by_day.get(d, {"UZS": 0.0, "USD": 0.0})
        rate = db.get_exchange_rate_on(d) or db.get_exchange_rate_on(None) or 0
        exely_uzs_equiv = ex["UZS"] + ex["USD"] * rate
        cash = cash_by_day.get(d, {"income": 0.0, "expense": 0.0})
        rows.append({
            "date": d, "exely_uzs": ex["UZS"], "exely_usd": ex["USD"],
            "exely_uzs_equiv": exely_uzs_equiv,
            "cash_income": cash["income"], "cash_expense": cash["expense"],
            "diff": exely_uzs_equiv - cash["income"],
        })
    return rows


def booking_debtors(year, month, currency):
    """Дт/Кт sahifasi uchun: Форма 1'dagi umumiy Debitorlik summasini
    tashkil qiluvchi har bir Exely bronni alohida-alohida ko'rsatadi
    (kontragent jadvalidagi "Shodibek aka" kabi qatorlardan farqli —
    bular mehmon-darajasidagi, hali to'lanmagan bron qoldiqlari;
    OTA orqali to'langan-lekin-bizga-tushmagan qism bu yerga kirmaydi —
    u channel_platform_debts()da kanal bo'yicha alohida ko'rsatiladi.

    `booking_receivables()` (Forma 1) bilan bir xil IFRS 15 chegarasi:
    kelish sanasi hali kelmagan (xizmat ko'rsatilmagan) bronlar bu yerga
    ham kirmaydi — aks holda bu sahifa Forma 1'dagi Debitorlik summasidan
    farq qilib qolardi (aynan shu ikkisi mos kelishi kerak)."""
    cutoff = (db.month_end_date(f"{year:04d}-{month:02d}") if (year and month) else None) \
        or date.today().strftime("%Y-%m-%d")
    rows = []
    for b in bookings_for_period(year, month):
        flat = flatten_booking(b)
        if flat.get("status") != "Active":
            continue
        if (flat.get("currency") or "UZS") != currency:
            continue
        if (flat.get("arrival") or "")[:10] > cutoff:
            continue
        guest_owed, _ = _booking_owed_parts(flat)
        if guest_owed <= 0:
            continue
        rows.append({
            "number": flat.get("number"),
            "guest": flat.get("guest") or "-",
            "arrival": flat.get("arrival"),
            "revenue": flat.get("revenue") or 0.0,
            "prepaid": flat.get("prepaid") or 0.0,
            "owed": guest_owed,
        })
    rows.sort(key=lambda r: r["arrival"] or "", reverse=True)
    return rows


def channel_platform_debts(currency):
    """Дт/Кт sahifasi uchun: OTA orqali (Booking.com, Airbnb va h.k.)
    "to'landi" deb belgilangan summalar — har bir kanal (platforma)
    bo'yicha JAMLANGAN (barcha vaqt, davr filtriga bog'liq emas — bu
    "hozirgi qarz qoldig'i" ko'rsatkichi). Platforma haqiqatda pul
    o'tkazganda, xodim Kassa/Bank'ga oddiy kirim kiritadi va kontragent
    maydoniga platforma nomini yozadi (masalan "Booking.com") — o'sha
    summa shu yerda avtomatik AYIRILADI (db.cash_income_by_counterparty
    orqali), ya'ni qarz real ravishda kamayib boradi.

    Xuddi booking_debtors()/booking_receivables() kabi: kelish sanasi
    hali kelmagan bronlar hisobga olinmaydi (IFRS 15 — xizmat hali
    ko'rsatilmagan)."""
    from collections import defaultdict
    today = date.today().strftime("%Y-%m-%d")
    totals = defaultdict(float)
    counts = defaultdict(int)
    for b in bookings_for_period(None, None):
        flat = flatten_booking(b)
        if flat.get("status") != "Active":
            continue
        if (flat.get("currency") or "UZS") != currency:
            continue
        if (flat.get("arrival") or "")[:10] > today:
            continue
        _, platform_owed = _booking_owed_parts(flat)
        if platform_owed <= 0:
            continue
        ch = flat.get("channel_name") or "-"
        totals[ch] += platform_owed
        counts[ch] += 1
    paid_by_cp = db.cash_income_by_counterparty(currency)
    rows = []
    for k, v in totals.items():
        paid = paid_by_cp.get(k, 0.0)
        remaining = v - paid
        if remaining <= 0.01:
            continue
        rows.append({"channel": k, "count": counts[k], "amount": v, "paid": paid, "owed": remaining})
    rows.sort(key=lambda r: -r["owed"])
    return rows


def real_cash_totals(year, month):
    """Dashboard KPI kartasi uchun HAQIQIY Kassa+Bank kirim/chiqim (Forma 3
    bilan bir xil manba — `db.cash_flow_by_category`), Exely accrual
    tushumidan farqli o'laroq: qo'lda kiritilgan/import qilingan haqiqiy
    pul harakati."""
    data = db.cash_flow_by_category(year, month)
    income = {"UZS": 0.0, "USD": 0.0}
    expense = {"UZS": 0.0, "USD": 0.0}
    for bucket in data.values():
        for source in ("bank", "kassa"):
            for cur in ("UZS", "USD"):
                income[cur] += bucket[source]["income"][cur]
                expense[cur] += bucket[source]["expense"][cur]
    return {"income": income, "expense": expense}


# ---- Dashboard ----

@app.route("/")
@permission_required("dashboard", "view")
def index():
    u = current_user()
    can_reports = db.has_permission(u, "reports", "export")
    year, month = get_period()
    period_end = db.month_end_date(f"{year:04d}-{month:02d}") if (year and month) else None
    return render_template(
        "dashboard.html", active_page="dashboard", can_view_reports=can_reports,
        year=year, month=month, years=available_years(),
        exchange_rate=db.get_exchange_rate_on(period_end),
    )


@app.route("/api/data")
@permission_required("dashboard", "view")
def api_data():
    year, month = get_period()
    with STATE_LOCK:
        status, error, last_attempt, last_success, progress = (
            STATE["status"], STATE["error"], STATE["last_attempt"], STATE["last_success"], STATE["progress"],
        )
    if year and month:
        data = aggregate_bookings(bookings_for_period(year, month))
    else:
        with STATE_LOCK:
            data = STATE["data"]
    return jsonify({
        "status": status,
        "error": error,
        "last_attempt": last_attempt,
        "last_success": last_success,
        "progress": progress,
        "data": data,
        "manual": db.summarize_transactions(year, month),
        "real_cash": real_cash_totals(year, month),
    })


@app.route("/api/refresh", methods=["POST"])
@permission_required("dashboard", "view")
def api_refresh():
    threading.Thread(target=refresh_once, daemon=True).start()
    return jsonify({"started": True})


@app.route("/download/excel")
@permission_required("reports", "export")
def download_excel():
    with STATE_LOCK:
        path = STATE["excel_path"]
    if not path:
        return jsonify({"error": "Hali hisobot tayyor emas"}), 404
    return send_file(path, as_attachment=True)


# ---- Bronlar ----

@app.route("/bookings")
@permission_required("bookings", "view")
def bookings_page():
    year, month = get_period()
    if year and month:
        rows = [flatten_booking(b) for b in bookings_for_period(year, month)]
    else:
        with STATE_LOCK:
            data = STATE["data"]
        rows = data["rows"] if data else []

    currency = request.args.get("currency") or None
    if currency:
        rows = [r for r in rows if r.get("currency") == currency]

    rows = sorted(rows, key=lambda r: r.get("arrival") or "", reverse=True)

    sum_revenue = sum(r.get("revenue") or 0.0 for r in rows)
    sum_prepaid = sum(r.get("prepaid") or 0.0 for r in rows)

    per_page = 50
    total_rows = len(rows)
    total_pages = max((total_rows + per_page - 1) // per_page, 1)
    page = max(request.args.get("page", 1, type=int) or 1, 1)
    page = min(page, total_pages)
    offset = (page - 1) * per_page
    page_rows = rows[offset:offset + per_page]

    return render_template(
        "bookings.html", active_page="bookings", rows=page_rows,
        year=year, month=month, years=available_years(),
        page=page, total_pages=total_pages, total_rows=total_rows, per_page=per_page,
        currency=currency, sum_revenue=sum_revenue, sum_prepaid=sum_prepaid,
    )


# ---- Xarajatlar ----

@app.route("/transactions", methods=["GET"])
@permission_required("transactions", "view")
def transactions_page():
    u = current_user()
    year, month = get_period()
    category = request.args.get("category") or None
    return render_template(
        "transactions.html",
        active_page="transactions",
        transactions=db.list_transactions(year, month, category=category),
        categories=db.all_categories(),
        income_categories=db.INCOME_CATEGORIES,
        forma2_groups=db.FORMA2_GROUPS,
        today=datetime.now().strftime("%Y-%m-%d"),
        can_create=db.has_permission(u, "transactions", "create"),
        can_delete=db.has_permission(u, "transactions", "delete"),
        year=year, month=month, years=available_years(), category=category,
    )


@app.route("/transactions/add", methods=["POST"])
@permission_required("transactions", "create")
def transactions_add():
    f = request.form
    if db.is_date_locked(f["date"]):
        flash(t("close.locked_error", g.lang), "error")
        return redirect(url_for("transactions_page"))
    if rate_missing_for(f["date"]):
        flash(t("flash.rate_required", g.lang), "error")
        return redirect(url_for("transactions_page"))
    db.add_transaction(
        date=f["date"], ttype=f["type"], category=f["category"],
        counterparty=f.get("counterparty", ""), description=f.get("description", ""),
        amount=parse_amount(f["amount"]), currency=f["currency"], status=f["status"],
    )
    return redirect(url_for("transactions_page"))


@app.route("/transactions/<int:tx_id>/delete", methods=["POST"])
@permission_required("transactions", "delete")
def transactions_delete(tx_id):
    rows = [r for r in db.list_transactions() if r["id"] == tx_id]
    if rows and db.is_date_locked(rows[0]["date"]):
        flash(t("close.locked_error", g.lang), "error")
        return redirect(url_for("transactions_page"))
    db.delete_transaction(tx_id)
    return redirect(url_for("transactions_page"))


def _prune_import_stash():
    now = time.time()
    with IMPORT_STASH_LOCK:
        expired = [k for k, v in IMPORT_STASH.items() if now - v["ts"] > IMPORT_STASH_TTL]
        for k in expired:
            del IMPORT_STASH[k]


@app.route("/transactions/import", methods=["GET"])
@permission_required("transactions", "create")
def transactions_import_page():
    return render_template("transactions_import.html", active_page="transactions")


@app.route("/transactions/import/preview", methods=["POST"])
@permission_required("transactions", "create")
def transactions_import_preview():
    _prune_import_stash()
    file = request.files.get("file")
    if not file or not file.filename:
        flash(t("tx.import_no_file", g.lang), "error")
        return redirect(url_for("transactions_import_page"))
    try:
        rows, error = parse_expense_xlsx(file.read())
    except Exception:
        log("EXCEL IMPORT PARSE XATOSI:\n" + traceback.format_exc())
        rows, error = [], "col_not_found"
    if error or not rows:
        flash(t("tx.import_parse_error", g.lang), "error")
        return redirect(url_for("transactions_import_page"))

    for r in rows:
        r["fingerprint"] = db.exely_import_fingerprint(
            r["date"], r["amount"], r["currency"], r["name"], r["counterparty"],
            r["category_raw"], r["payment_method"])
        legacy_fp = db.exely_import_fingerprint_legacy(
            r["date"], r["amount"], r["currency"], r["name"], r["counterparty"])
        r["already_imported"] = db.exely_import_exists(r["fingerprint"]) or db.exely_import_exists(legacy_fp)

    seen = []
    for r in rows:
        if r["category_raw"] not in seen:
            seen.append(r["category_raw"])

    upload_id = secrets.token_hex(16)
    with IMPORT_STASH_LOCK:
        IMPORT_STASH[upload_id] = {"rows": rows, "unique_categories": seen, "ts": time.time()}

    new_count = sum(1 for r in rows if not r["already_imported"])
    dup_count = len(rows) - new_count
    return render_template(
        "transactions_import_preview.html", active_page="transactions",
        upload_id=upload_id, rows=rows, unique_categories=seen,
        categories=db.all_categories(), forma2_groups=db.FORMA2_GROUPS,
        new_count=new_count, dup_count=dup_count,
    )


@app.route("/transactions/import/commit", methods=["POST"])
@permission_required("transactions", "create")
def transactions_import_commit():
    upload_id = request.form.get("upload_id", "")
    with IMPORT_STASH_LOCK:
        stash = IMPORT_STASH.pop(upload_id, None)
    if not stash:
        flash(t("tx.import_expired", g.lang), "error")
        return redirect(url_for("transactions_import_page"))

    catmap = {}
    for i, raw_cat in enumerate(stash["unique_categories"]):
        chosen = request.form.get(f"catmap__{i}")
        catmap[raw_cat] = chosen or "Boshqa operatsion xarajat"

    imported = duplicate = locked = rate_missing = 0
    for r in stash["rows"]:
        if r["already_imported"] or db.exely_import_exists(r["fingerprint"]):
            duplicate += 1
            continue
        if db.is_date_locked(r["date"]):
            locked += 1
            continue
        if rate_missing_for(r["date"]):
            rate_missing += 1
            continue
        category = catmap.get(r["category_raw"], "Boshqa operatsion xarajat")
        description = r["name"] + (f" ({r['payment_method']})" if r["payment_method"] else "")
        db.exely_import_commit_row(
            r["fingerprint"], r["date"], category, r["counterparty"], description,
            r["amount"], r["currency"],
        )
        imported += 1

    msg = (t("tx.import_summary", g.lang)
           .replace("{imported}", str(imported)).replace("{duplicate}", str(duplicate))
           .replace("{locked}", str(locked)).replace("{rate_missing}", str(rate_missing)))
    flash(msg, "success" if imported else "error")
    return redirect(url_for("transactions_page"))


# ---- Hisobotlar (Forma 1/2/3) ----

@app.route("/reports")
@permission_required("reports", "view")
def reports_page():
    year, month = get_period()
    tab = request.args.get("tab", "f2")

    if year and month:
        data = aggregate_bookings(bookings_for_period(year, month))
        period_end = db.month_end_date(f"{year:04d}-{month:02d}")
        prev_day = (date(year, month, 1) - timedelta(days=1)).strftime("%Y-%m-%d")
        opening_uzs = db.get_cash_balance("UZS", upto_date=prev_day)
        opening_usd = db.get_cash_balance("USD", upto_date=prev_day)
        opening_bank_uzs = db.get_cash_balance("UZS", upto_date=prev_day, source="bank")
        opening_bank_usd = db.get_cash_balance("USD", upto_date=prev_day, source="bank")
        opening_kassa_uzs = db.get_cash_balance("UZS", upto_date=prev_day, source="kassa")
        opening_kassa_usd = db.get_cash_balance("USD", upto_date=prev_day, source="kassa")
    else:
        data = aggregate_bookings(bookings_recognized_upto_today())
        period_end = None
        opening_uzs = db.get_cash_opening("UZS")
        opening_usd = db.get_cash_opening("USD")
        opening_bank_uzs = db.get_cash_opening("UZS", source="bank")
        opening_bank_usd = db.get_cash_opening("USD", source="bank")
        opening_kassa_uzs = db.get_cash_opening("UZS", source="kassa")
        opening_kassa_usd = db.get_cash_opening("USD", source="kassa")

    manual = db.summarize_transactions(year, month)
    f2 = build_forma2(data, manual)

    # 010-qatorning tarkibi: Хостел (Exely bronlari) / Xizmatlar (Услуги
    # sahifasidan ko'rsatilgan xizmatlar) / Bar (mini-bar sotuvi).
    hostel_rev = (data.get("revenue_by_currency", {}) if data else {}) or {}
    hostel_rev_uzs, hostel_rev_usd = hostel_rev.get("UZS", 0.0), hostel_rev.get("USD", 0.0)
    extra_rev = manual.get("revenue_extra", {})
    services_rev = manual.get("by_category", {}).get(db.SERVICE_REVENUE_CATEGORY, {})
    services_rev_uzs, services_rev_usd = services_rev.get("UZS", 0.0), services_rev.get("USD", 0.0)
    bar_rev_uzs = extra_rev.get("UZS", 0.0) - services_rev_uzs
    bar_rev_usd = extra_rev.get("USD", 0.0) - services_rev_usd

    tannarx_breakdown = db.category_breakdown(year, month, "tannarx")
    sotish_breakdown = db.category_breakdown(year, month, "sotish")
    mamuriy_breakdown = db.category_breakdown(year, month, "mamuriy")
    boshqa_op_breakdown = db.category_breakdown(year, month, "boshqa_operatsion")
    moliyaviy_breakdown = db.category_breakdown(year, month, "moliyaviy")
    soliq_breakdown = db.category_breakdown(year, month, "soliq")

    cash_uzs = db.get_cash_balance("UZS", upto_date=period_end)
    cash_usd = db.get_cash_balance("USD", upto_date=period_end)
    cash_bank_uzs = db.get_cash_balance("UZS", upto_date=period_end, source="bank")
    cash_bank_usd = db.get_cash_balance("USD", upto_date=period_end, source="bank")
    cash_kassa_uzs = db.get_cash_balance("UZS", upto_date=period_end, source="kassa")
    cash_kassa_usd = db.get_cash_balance("USD", upto_date=period_end, source="kassa")

    cp_recv_uzs, pay_uzs = db.outstanding_balance("UZS", upto_date=period_end)
    cp_recv_usd, pay_usd = db.outstanding_balance("USD", upto_date=period_end)

    booking_recv_uzs, booking_recv_usd, booking_recv_skipped = booking_receivables(period_end)
    recv_uzs = cp_recv_uzs + booking_recv_uzs
    recv_usd = cp_recv_usd + booking_recv_usd

    inv = db.bar_stock_value()

    fa_uzs = db.total_fixed_assets_value("UZS", upto_date=period_end)
    fa_usd = db.total_fixed_assets_value("USD", upto_date=period_end)

    charter_uzs = float(db.get_setting("charter_capital_uzs", "0") or 0)
    charter_usd = float(db.get_setting("charter_capital_usd", "0") or 0)

    retained_uzs, retained_usd = cumulative_net_profit(period_end)
    adv_uzs, adv_usd = customer_advances(period_end)

    f1 = build_forma1(
        cash={"UZS": cash_uzs, "USD": cash_usd},
        receivables={"UZS": recv_uzs, "USD": recv_usd},
        inventory={"UZS": inv["UZS"], "USD": inv["USD"]},
        fixed_assets={"UZS": fa_uzs, "USD": fa_usd},
        payables={"UZS": pay_uzs, "USD": pay_usd},
        advances={"UZS": adv_uzs, "USD": adv_usd},
        charter={"UZS": charter_uzs, "USD": charter_usd},
        retained={"UZS": retained_uzs, "USD": retained_usd},
    )

    rate = db.get_exchange_rate_on(period_end)

    # Cash Flow (Forma 3) batafsil jadvali — har bir Cash Flow kodi bo'yicha
    # Bank/Kassa alohida kirim/chiqim (foydalanuvchi ko'rsatgan namunaviy
    # "ДВИЖЕНИЕ ДЕНЕЖНЫХ СРЕДСТВ" hisobotiga o'xshash tuzilma).
    cash_by_cat = db.cash_flow_by_category(year, month)
    cash_flow_rows = []
    cf_bank_in = cf_bank_out = cf_kassa_in = cf_kassa_out = 0.0
    for c in db.all_cash_categories():
        d = cash_by_cat.get(c["name"])
        if not d:
            continue
        bank_in = to_display_amount(d["bank"]["income"]["UZS"], d["bank"]["income"]["USD"], rate)
        bank_out = to_display_amount(d["bank"]["expense"]["UZS"], d["bank"]["expense"]["USD"], rate)
        kassa_in = to_display_amount(d["kassa"]["income"]["UZS"], d["kassa"]["income"]["USD"], rate)
        kassa_out = to_display_amount(d["kassa"]["expense"]["UZS"], d["kassa"]["expense"]["USD"], rate)
        if not (bank_in or bank_out or kassa_in or kassa_out):
            continue
        cf_bank_in += bank_in
        cf_bank_out += bank_out
        cf_kassa_in += kassa_in
        cf_kassa_out += kassa_out
        cash_flow_rows.append({
            "code": c["code"], "name": c["name"],
            "bank_in": bank_in, "bank_out": bank_out,
            "kassa_in": kassa_in, "kassa_out": kassa_out,
            "total_in": bank_in + kassa_in, "total_out": bank_out + kassa_out,
        })
    cash_flow_totals = {
        "bank_in": cf_bank_in, "bank_out": cf_bank_out,
        "kassa_in": cf_kassa_in, "kassa_out": cf_kassa_out,
        "total_in": cf_bank_in + cf_kassa_in, "total_out": cf_bank_out + cf_kassa_out,
    }
    cash_flow_opening = {
        "bank": to_display_amount(opening_bank_uzs, opening_bank_usd, rate),
        "kassa": to_display_amount(opening_kassa_uzs, opening_kassa_usd, rate),
        "total": to_display_amount(opening_uzs, opening_usd, rate),
    }
    cash_flow_closing = {
        "bank": cash_flow_opening["bank"] + cash_flow_totals["bank_in"] - cash_flow_totals["bank_out"],
        "kassa": cash_flow_opening["kassa"] + cash_flow_totals["kassa_in"] - cash_flow_totals["kassa_out"],
        "total": cash_flow_opening["total"] + cash_flow_totals["total_in"] - cash_flow_totals["total_out"],
    }
    row_010 = next((r for r in f2 if r["key"] == "f2.010"), {"uzs": 0.0, "usd": 0.0})
    row_100 = next((r for r in f2 if r["key"] == "f2.100"), {"uzs": 0.0, "usd": 0.0})
    row_030 = next((r for r in f2 if r["key"] == "f2.030"), {"uzs": 0.0, "usd": 0.0})
    kpi_revenue = to_display_amount(row_010["uzs"], row_010["usd"], rate)
    kpi_net_profit = to_display_amount(row_100["uzs"], row_100["usd"], rate)
    kpi_gross_profit = to_display_amount(row_030["uzs"], row_030["usd"], rate)
    gross_margin = round(kpi_gross_profit / kpi_revenue * 100, 1) if kpi_revenue else 0.0
    net_margin = round(kpi_net_profit / kpi_revenue * 100, 1) if kpi_revenue else 0.0

    # Segment bo'yicha foyda: Bar/mini-bar — o'zining savdosi va tovar
    # tannarxidan hisoblangan sof (yalpi) foyda; Hostel — qolgan hammasi
    # (umumiy "Sof foyda"dan Bar ulushi ayirilgan holda, shu bilan
    # Hostel + Bar = Jami har doim aniq mos keladi).
    bar_seg = db.summarize_bar_segment(year, month)
    bar_revenue = to_display_amount(bar_seg["revenue"]["UZS"], bar_seg["revenue"]["USD"], rate)
    bar_cost = to_display_amount(bar_seg["cost"]["UZS"], bar_seg["cost"]["USD"], rate)
    bar_profit = bar_revenue - bar_cost
    hostel_revenue = kpi_revenue - bar_revenue
    hostel_profit = kpi_net_profit - bar_profit
    hostel_cost = hostel_revenue - hostel_profit

    # "Bar" tabi uchun mahsulot bo'yicha batafsil hisobot
    bar_products_report = []
    for r in db.bar_product_report(year, month):
        sold_amount = to_display_amount(r["sold"]["UZS"], r["sold"]["USD"], rate)
        purchased_amount = to_display_amount(r["purchased"]["UZS"], r["purchased"]["USD"], rate)
        bar_products_report.append({
            "name": r["name"], "unit": r["unit"],
            "sold_qty": r["sold_qty"], "sold_amount": sold_amount,
            "purchased_qty": r["purchased_qty"], "purchased_amount": purchased_amount,
            "net": sold_amount - purchased_amount,
            "stock_qty": r["stock_qty"],
        })
    bar_stock = db.bar_stock_value()
    bar_stock_value = to_display_amount(bar_stock["UZS"], bar_stock["USD"], rate)

    recon_rows = daily_reconciliation() if tab == "recon" else []

    return render_template(
        "reports.html", active_page="reports", tab=tab, f1=f1, f2=f2, recon_rows=recon_rows,
        cash_flow_rows=cash_flow_rows, cash_flow_totals=cash_flow_totals,
        cash_flow_opening=cash_flow_opening, cash_flow_closing=cash_flow_closing,
        bar_products_report=bar_products_report, bar_stock_value=bar_stock_value,
        bar_revenue=bar_revenue, bar_cost=bar_cost, bar_profit=bar_profit,
        hostel_revenue=hostel_revenue, hostel_cost=hostel_cost, hostel_profit=hostel_profit,
        today=datetime.now().strftime("%d.%m.%Y"),
        year=year, month=month, years=available_years(),
        kpi_revenue=kpi_revenue, kpi_net_profit=kpi_net_profit, kpi_gross_profit=kpi_gross_profit,
        kpi_gross_margin=gross_margin, kpi_net_margin=net_margin,
        rate=rate,
        cash_bank_uzs=cash_bank_uzs, cash_bank_usd=cash_bank_usd,
        cash_kassa_uzs=cash_kassa_uzs, cash_kassa_usd=cash_kassa_usd,
        cp_recv_uzs=cp_recv_uzs, cp_recv_usd=cp_recv_usd,
        booking_recv_uzs=booking_recv_uzs, booking_recv_usd=booking_recv_usd,
        booking_recv_skipped=booking_recv_skipped,
        hostel_rev_uzs=hostel_rev_uzs, hostel_rev_usd=hostel_rev_usd,
        services_rev_uzs=services_rev_uzs, services_rev_usd=services_rev_usd,
        bar_rev_uzs=bar_rev_uzs, bar_rev_usd=bar_rev_usd,
        tannarx_breakdown=tannarx_breakdown, sotish_breakdown=sotish_breakdown,
        mamuriy_breakdown=mamuriy_breakdown, boshqa_op_breakdown=boshqa_op_breakdown,
        moliyaviy_breakdown=moliyaviy_breakdown, soliq_breakdown=soliq_breakdown,
    )


# ---- Kassa / Bank ----

@app.route("/cash")
@permission_required("cash", "view")
def cash_page():
    u = current_user()
    year, month = get_period()
    ttype = request.args.get("type") or None
    source = request.args.get("source") or None
    category = request.args.get("category") or None
    counterparty = request.args.get("counterparty") or None
    search = request.args.get("q", "").strip() or None
    per_page_raw = request.args.get("per_page", "50")
    if per_page_raw == "all":
        per_page = None
    else:
        try:
            per_page = max(int(per_page_raw), 1)
        except ValueError:
            per_page_raw, per_page = "50", 50
    page = max(request.args.get("page", 1, type=int) or 1, 1)
    total_rows = db.count_cash_transactions(
        year=year, month=month, source=source, ttype=ttype, category=category, counterparty=counterparty, search=search)
    total_pages = 1 if not per_page else max((total_rows + per_page - 1) // per_page, 1)
    page = min(page, total_pages)
    offset = (page - 1) * per_page if per_page else 0
    rows = db.list_cash_transactions(
        year=year, month=month, source=source, ttype=ttype, category=category, counterparty=counterparty, search=search,
        limit=per_page, offset=offset,
    )
    period_end = db.month_end_date(f"{year:04d}-{month:02d}") if (year and month) else None
    rate = db.get_exchange_rate_on(period_end)
    return render_template(
        "cash.html", active_page="cash", rows=rows,
        sources=db.CASH_SOURCES, sections=db.CASH_SECTIONS, categories=db.all_cash_categories(),
        forma2_expense_categories=db.all_categories(), forma2_groups=db.FORMA2_GROUPS,
        forma2_income_categories=db.INCOME_CATEGORIES,
        counterparties=db.list_cash_counterparties(),
        today=datetime.now().strftime("%Y-%m-%d"),
        can_create=db.has_permission(u, "cash", "create"),
        can_delete=db.has_permission(u, "cash", "delete"),
        year=year, month=month, years=available_years(), ttype=ttype, source=source, category=category, counterparty=counterparty,
        page=page, per_page=per_page_raw, total_pages=total_pages, total_rows=total_rows, search=search or "",
        bal_kassa_uzs=db.get_cash_balance("UZS", upto_date=period_end, source="kassa"),
        bal_kassa_usd=db.get_cash_balance("USD", upto_date=period_end, source="kassa"),
        bal_bank_uzs=db.get_cash_balance("UZS", upto_date=period_end, source="bank"),
        bal_bank_usd=db.get_cash_balance("USD", upto_date=period_end, source="bank"),
        rate=rate,
    )


@app.route("/cash/add", methods=["POST"])
@permission_required("cash", "create")
def cash_add():
    f = request.form
    if db.is_date_locked(f["date"]):
        flash(t("close.locked_error", g.lang), "error")
        return redirect(url_for("cash_page"))
    if rate_missing_for(f["date"]):
        flash(t("flash.rate_required", g.lang), "error")
        return redirect(url_for("cash_page"))
    cat = db.all_cash_category_map().get(f["category"])
    if not cat:
        abort(400)
    db.add_cash_transaction(
        date=f["date"], source=f["source"], ttype=cat["type"], section=cat["section"],
        category=f["category"], counterparty=f.get("counterparty", ""),
        description=f.get("description", ""), amount=parse_amount(f["amount"]), currency=f["currency"],
        note_label=f.get("note_label", ""), forma2_category=f.get("forma2_category") or None,
    )
    return redirect(url_for("cash_page"))


@app.route("/cash/<int:cash_id>/delete", methods=["POST"])
@permission_required("cash", "delete")
def cash_delete(cash_id):
    row = db.get_cash_transaction(cash_id)
    if row and db.is_date_locked(row["date"]):
        flash(t("close.locked_error", g.lang), "error")
        return redirect(url_for("cash_page"))
    db.delete_cash_transaction(cash_id)
    return redirect(url_for("cash_page"))


@app.route("/cash/<int:cash_id>/edit", methods=["POST"])
@permission_required("cash", "create")
def cash_edit(cash_id):
    row = db.get_cash_transaction(cash_id)
    if not row:
        abort(404)
    f = request.form
    if db.is_date_locked(row["date"]) or db.is_date_locked(f["date"]):
        flash(t("close.locked_error", g.lang), "error")
        return redirect(url_for("cash_page"))
    db.update_cash_transaction(
        cash_id, date=f["date"], source=f["source"], counterparty=f.get("counterparty", ""),
        description=f.get("description", ""), amount=parse_amount(f["amount"]), currency=f["currency"],
        note_label=f.get("note_label", ""),
    )
    return redirect(url_for("cash_page"))


@app.route("/cash/export")
@permission_required("cash", "view")
def cash_export():
    year, month = get_period()
    ttype = request.args.get("type") or None
    source = request.args.get("source") or None
    category = request.args.get("category") or None
    counterparty = request.args.get("counterparty") or None
    search = request.args.get("q", "").strip() or None
    rows = db.list_cash_transactions(
        year=year, month=month, source=source, ttype=ttype, category=category, counterparty=counterparty, search=search)
    out_dir = BASE_DIR / "reports"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"Kassa_Bank_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    build_cash_excel_report(rows, str(path))
    return send_file(str(path), as_attachment=True, download_name="Kassa_Bank.xlsx")


@app.route("/cash/import", methods=["GET"])
@permission_required("cash", "create")
def cash_import_page():
    return render_template("cash_import.html", active_page="cash")


@app.route("/cash/import/preview", methods=["POST"])
@permission_required("cash", "create")
def cash_import_preview():
    _prune_import_stash()
    file = request.files.get("file")
    if not file or not file.filename:
        flash(t("tx.import_no_file", g.lang), "error")
        return redirect(url_for("cash_import_page"))
    try:
        rows, error = parse_expense_xlsx(file.read())
    except Exception:
        log("EXCEL IMPORT PARSE XATOSI:\n" + traceback.format_exc())
        rows, error = [], "col_not_found"
    if error or not rows:
        flash(t("tx.import_parse_error", g.lang), "error")
        return redirect(url_for("cash_import_page"))

    for r in rows:
        r["fingerprint"] = db.exely_import_fingerprint(
            r["date"], r["amount"], r["currency"], r["name"], r["counterparty"],
            r["category_raw"], r["payment_method"])
        legacy_fp = db.exely_import_fingerprint_legacy(
            r["date"], r["amount"], r["currency"], r["name"], r["counterparty"])
        r["already_imported"] = db.exely_cash_import_exists(r["fingerprint"]) or db.exely_cash_import_exists(legacy_fp)

    upload_id = secrets.token_hex(16)
    with IMPORT_STASH_LOCK:
        IMPORT_STASH[upload_id] = {"rows": rows, "ts": time.time()}

    new_count = sum(1 for r in rows if not r["already_imported"])
    dup_count = len(rows) - new_count
    return render_template(
        "cash_import_preview.html", active_page="cash",
        upload_id=upload_id, rows=rows, categories=db.all_cash_categories(), sections=db.CASH_SECTIONS,
        new_count=new_count, dup_count=dup_count,
    )


@app.route("/cash/import/commit", methods=["POST"])
@permission_required("cash", "create")
def cash_import_commit():
    upload_id = request.form.get("upload_id")
    with IMPORT_STASH_LOCK:
        stash = IMPORT_STASH.pop(upload_id, None)
    if not stash:
        flash(t("tx.import_expired", g.lang), "error")
        return redirect(url_for("cash_import_page"))

    source = request.form.get("source", "kassa")
    category = request.form.get("category", "")
    cat = db.all_cash_category_map().get(category)
    if not cat:
        abort(400)

    imported = duplicate = locked = rate_missing = 0
    for r in stash["rows"]:
        if db.exely_cash_import_exists(r["fingerprint"]):
            duplicate += 1
            continue
        if db.is_date_locked(r["date"]):
            locked += 1
            continue
        if rate_missing_for(r["date"]):
            rate_missing += 1
            continue
        cash_id = db.add_cash_transaction(
            date=r["date"], source=source, ttype=cat["type"], section=cat["section"],
            category=category, counterparty=r["counterparty"], description=r["name"],
            amount=r["amount"], currency=r["currency"], note_label=r["category_raw"],
        )
        db.exely_cash_import_commit(r["fingerprint"], cash_id)
        imported += 1

    msg = (t("tx.import_summary", g.lang)
           .replace("{imported}", str(imported)).replace("{duplicate}", str(duplicate))
           .replace("{locked}", str(locked)).replace("{rate_missing}", str(rate_missing)))
    flash(msg, "success" if imported else "error")
    return redirect(url_for("cash_page"))


# ---- Bar / mini-bar ----

@app.route("/bar")
@permission_required("bar", "view")
def bar_page():
    u = current_user()
    year, month = get_period()
    product_id = request.args.get("product_id", type=int)
    rows = [r for r in db.list_bar_transactions(year, month, product_id=product_id) if r["ttype"] == "sale"]
    return render_template(
        "bar.html", active_page="bar",
        products=db.list_bar_products(),
        rows=rows,
        today=datetime.now().strftime("%Y-%m-%d"),
        can_create=db.has_permission(u, "bar", "create"),
        can_delete=db.has_permission(u, "bar", "delete"),
        year=year, month=month, years=available_years(), product_id=product_id,
    )


@app.route("/sklad")
@permission_required("bar", "view")
def sklad_page():
    u = current_user()
    year, month = get_period()
    product_id = request.args.get("product_id", type=int)
    rows = [r for r in db.list_bar_transactions(year, month, product_id=product_id) if r["ttype"] == "restock"]
    period_end = db.month_end_date(f"{year:04d}-{month:02d}") if (year and month) else None
    return render_template(
        "sklad.html", active_page="sklad",
        products=db.list_bar_products(),
        rows=rows,
        stock_value=db.bar_stock_value(),
        today=datetime.now().strftime("%Y-%m-%d"),
        can_create=db.has_permission(u, "bar", "create"),
        can_edit=db.has_permission(u, "bar", "edit"),
        can_delete=db.has_permission(u, "bar", "delete"),
        year=year, month=month, years=available_years(), product_id=product_id,
        rate=db.get_exchange_rate_on(period_end),
    )


@app.route("/bar/product/add", methods=["POST"])
@permission_required("bar", "create")
def bar_product_add():
    f = request.form
    db.add_bar_product(
        name=f["name"], unit=f.get("unit") or "dona",
        cost_price=parse_amount(f["cost_price"]), sale_price=parse_amount(f["sale_price"]),
        currency=f["currency"],
    )
    return redirect(url_for("sklad_page"))


@app.route("/bar/product/<int:product_id>/edit", methods=["POST"])
@permission_required("bar", "edit")
def bar_product_edit(product_id):
    f = request.form
    db.update_bar_product(
        product_id, name=f["name"], unit=f.get("unit") or "dona",
        cost_price=parse_amount(f["cost_price"]), sale_price=parse_amount(f["sale_price"]),
        currency=f["currency"],
    )
    return redirect(url_for("sklad_page"))


@app.route("/bar/product/<int:product_id>/delete", methods=["POST"])
@permission_required("bar", "delete")
def bar_product_delete(product_id):
    try:
        db.delete_bar_product(product_id)
    except ValueError:
        flash(t("bar.product_delete_error", g.lang), "error")
    return redirect(url_for("sklad_page"))


@app.route("/bar/restock", methods=["POST"])
@permission_required("bar", "create")
def bar_restock():
    f = request.form
    date_str = f.get("date") or datetime.now().strftime("%Y-%m-%d")
    if db.is_date_locked(date_str):
        flash(t("close.locked_error", g.lang), "error")
        return redirect(url_for("sklad_page"))
    if rate_missing_for(date_str):
        flash(t("flash.rate_required", g.lang), "error")
        return redirect(url_for("sklad_page"))
    source = f.get("source", "kassa")
    counterparty = f.get("counterparty", "")
    status = f.get("status", "paid")
    if status == "unpaid" and not counterparty.strip():
        flash(t("sklad.unpaid_needs_supplier", g.lang), "error")
        return redirect(url_for("sklad_page"))
    product_ids = request.form.getlist("product_id[]")
    qtys = request.form.getlist("qty[]")
    lines = []
    for pid, qty in zip(product_ids, qtys):
        if not pid or not qty:
            continue
        try:
            pid_i, qty_f = int(pid), float(qty)
        except ValueError:
            flash(t("flash.error_prefix", g.lang) + "invalid_qty", "error")
            return redirect(url_for("sklad_page"))
        if qty_f <= 0 or not db.get_bar_product(pid_i):
            flash(t("flash.error_prefix", g.lang) + "invalid_line", "error")
            return redirect(url_for("sklad_page"))
        lines.append((pid_i, qty_f))
    # Avval BARCHA qatorlar tekshirilib bo'lingandan keyingina saqlanadi —
    # aks holda savatdagi 3-qator xato bersa, 1- va 2-qator allaqachon
    # bazaga yozilib, zaxira/kassa qisman o'zgargan holda qolib ketardi.
    for pid_i, qty_f in lines:
        try:
            db.add_bar_transaction(
                date=date_str, product_id=pid_i, ttype="restock",
                qty=qty_f, source=source,
                counterparty=counterparty, description="", status=status,
            )
        except ValueError as e:
            flash(t("flash.error_prefix", g.lang) + str(e), "error")
            break
    return redirect(url_for("sklad_page"))


@app.route("/bar/sell", methods=["POST"])
@permission_required("bar", "create")
def bar_sell():
    date_str = datetime.now().strftime("%Y-%m-%d")
    if db.is_date_locked(date_str):
        flash(t("close.locked_error", g.lang), "error")
        return redirect(url_for("bar_page"))
    if rate_missing_for(date_str):
        flash(t("flash.rate_required", g.lang), "error")
        return redirect(url_for("bar_page"))
    source = request.form.get("source", "kassa")
    product_ids = request.form.getlist("product_id[]")
    qtys = request.form.getlist("qty[]")
    lines = []
    for pid, qty in zip(product_ids, qtys):
        if not pid or not qty:
            continue
        try:
            pid_i, qty_f = int(pid), float(qty)
        except ValueError:
            flash(t("flash.error_prefix", g.lang) + "invalid_qty", "error")
            return redirect(url_for("bar_page"))
        product = db.get_bar_product(pid_i)
        if qty_f <= 0 or not product:
            flash(t("flash.error_prefix", g.lang) + "invalid_line", "error")
            return redirect(url_for("bar_page"))
        lines.append((pid_i, qty_f))
    # Bitta savatda bir xil mahsulot bir necha marta bo'lishi mumkin —
    # zaxira YETARLILIGI qatorlar YIG'INDISI bo'yicha OLDINDAN tekshiriladi,
    # keyingina hech biri saqlanadi. Aks holda savatdagi keyingi qator
    # yetishmovchilik bilan rad etilganda, oldingi qatorlar allaqachon
    # saqlanib, zaxira/kassa qisman o'zgargan holda qolib ketardi.
    requested_by_product = {}
    for pid_i, qty_f in lines:
        requested_by_product[pid_i] = requested_by_product.get(pid_i, 0.0) + qty_f
    for pid_i, total_qty in requested_by_product.items():
        product = db.get_bar_product(pid_i)
        if product["stock_qty"] + 1e-9 < total_qty:
            flash(t("bar.insufficient_stock_error", g.lang), "error")
            return redirect(url_for("bar_page"))
    for pid_i, qty_f in lines:
        db.add_bar_transaction(
            date=date_str, product_id=pid_i, ttype="sale",
            qty=qty_f, source=source,
            counterparty="", description="",
        )
    return redirect(url_for("bar_page"))


@app.route("/bar/<int:bt_id>/delete", methods=["POST"])
@permission_required("bar", "delete")
def bar_delete(bt_id):
    row = db.get_bar_transaction(bt_id)
    dest = "sklad_page" if row and row["ttype"] == "restock" else "bar_page"
    if row and db.is_date_locked(row["date"]):
        flash(t("close.locked_error", g.lang), "error")
        return redirect(url_for(dest))
    db.delete_bar_transaction(bt_id)
    return redirect(url_for(dest))


@app.route("/bar/<int:bt_id>/edit", methods=["POST"])
@permission_required("bar", "create")
def bar_edit(bt_id):
    row = db.get_bar_transaction(bt_id)
    if not row:
        abort(404)
    dest = "sklad_page" if row["ttype"] == "restock" else "bar_page"
    f = request.form
    if db.is_date_locked(row["date"]) or db.is_date_locked(f["date"]):
        flash(t("close.locked_error", g.lang), "error")
        return redirect(url_for(dest))
    try:
        db.update_bar_transaction(
            bt_id, date=f["date"], qty=float(parse_amount(f["qty"])), source=f["source"],
            counterparty=f.get("counterparty", ""), description=f.get("description", ""),
        )
    except ValueError as e:
        if str(e) == "insufficient_stock":
            flash(t("bar.insufficient_stock_error", g.lang), "error")
        else:
            flash(t("flash.error_prefix", g.lang) + str(e), "error")
    return redirect(url_for(dest))


# ---- Дт/Кт (kontragentlar bilan hisob-kitob) ----

@app.route("/ledger")
@permission_required("ledger", "view")
def ledger_page():
    year, month = get_period()
    currency = request.args.get("currency", "UZS")
    rows = db.counterparty_ledger(year, month, currency)
    totals = {
        k: sum(r[k] for r in rows)
        for k in ("open_dt", "open_kt", "turn_dt", "turn_kt", "close_dt", "close_kt")
    }
    booking_rows = booking_debtors(year, month, currency)
    booking_total = sum(r["owed"] for r in booking_rows)
    channel_rows = channel_platform_debts(currency)
    channel_total = sum(r["owed"] for r in channel_rows)
    return render_template(
        "ledger.html", active_page="ledger", rows=rows, totals=totals, currency=currency,
        year=year, month=month, years=available_years(),
        booking_rows=booking_rows, booking_total=booking_total,
        channel_rows=channel_rows, channel_total=channel_total,
    )


@app.route("/ledger/detail")
@permission_required("ledger", "view")
def ledger_detail_page():
    name = request.args.get("name", "")
    currency = request.args.get("currency", "UZS")
    entries = db.counterparty_entries(name, currency)
    for e in entries:
        e["payments"] = db.list_payments_for(e["source_type"], e["source_id"])
    return render_template(
        "ledger_detail.html", active_page="ledger", counterparty=name, currency=currency,
        entries=entries, today=datetime.now().strftime("%Y-%m-%d"),
        can_create=db.has_permission(current_user(), "ledger", "create"),
        can_delete=db.has_permission(current_user(), "ledger", "delete"),
    )


@app.route("/ledger/payment/add", methods=["POST"])
@permission_required("ledger", "create")
def ledger_payment_add():
    f = request.form
    source_type = f["source_type"]
    source_id = int(f["source_id"])
    if source_type == "transaction":
        src = db.get_transaction(source_id)
    elif source_type == "bar_transaction":
        src = db.get_bar_transaction(source_id)
    elif source_type == "cash_transaction":
        src = db.get_cash_transaction(source_id)
    else:
        src = None
    if not src:
        abort(404)
    back = redirect(url_for("ledger_detail_page", name=f["counterparty"], currency=f["currency"]))
    if db.is_date_locked(f["date"]) or db.is_date_locked(src["date"]):
        flash(t("close.locked_error", g.lang), "error")
        return back
    cash_source = f.get("cash_source") or None
    if cash_source and f["currency"] == "USD" and rate_missing_for(f["date"]):
        flash(t("flash.rate_required", g.lang), "error")
        return back
    db.add_payment(
        source_type, source_id, f["date"], parse_amount(f["amount"]), f["currency"], f.get("note", ""),
        cash_source=cash_source,
    )
    return back


@app.route("/ledger/payment/<int:payment_id>/delete", methods=["POST"])
@permission_required("ledger", "delete")
def ledger_payment_delete(payment_id):
    p = db.get_payment(payment_id)
    if not p:
        abort(404)
    back = redirect(url_for(
        "ledger_detail_page",
        name=request.form.get("counterparty", ""), currency=request.form.get("currency", "UZS"),
    ))
    if db.is_date_locked(p["date"]):
        flash(t("close.locked_error", g.lang), "error")
        return back
    db.delete_payment(payment_id)
    return back


# ---- Hamkorlar (kontragentlar ma'lumotnomasi) ----

@app.route("/ledger/counterparties")
@permission_required("ledger", "view")
def counterparties_page():
    u = current_user()
    return render_template(
        "counterparties.html", active_page="ledger", rows=db.list_counterparties(),
        can_create=db.has_permission(u, "ledger", "create"),
        can_delete=db.has_permission(u, "ledger", "delete"),
    )


@app.route("/ledger/counterparties/import", methods=["POST"])
@permission_required("ledger", "create")
def counterparties_import():
    added = db.import_existing_counterparties()
    flash(t("cp.import_done", g.lang).replace("{n}", str(added)), "success")
    return redirect(url_for("counterparties_page"))


@app.route("/ledger/counterparties/add", methods=["POST"])
@permission_required("ledger", "create")
def counterparties_add():
    f = request.form
    name = (f.get("name") or "").strip()
    if name:
        db.add_counterparty(name, f.get("inn", ""))
    return redirect(url_for("counterparties_page"))


@app.route("/ledger/counterparties/<int:cp_id>/edit", methods=["POST"])
@permission_required("ledger", "create")
def counterparties_edit(cp_id):
    f = request.form
    name = (f.get("name") or "").strip()
    if name:
        db.update_counterparty(cp_id, name, f.get("inn", ""))
    return redirect(url_for("counterparties_page"))


@app.route("/ledger/counterparties/<int:cp_id>/delete", methods=["POST"])
@permission_required("ledger", "delete")
def counterparties_delete(cp_id):
    db.delete_counterparty(cp_id)
    return redirect(url_for("counterparties_page"))


# ---- Xizmatlar (Услуги) — QQS bilan olingan/ko'rsatilgan xizmatlar ----

@app.route("/services")
@permission_required("services", "view")
def services_page():
    u = current_user()
    year, month = get_period()
    direction = request.args.get("direction") or None
    counterparty = request.args.get("counterparty") or None
    service_type = request.args.get("service_type") or None
    rows = db.list_services(year, month, direction=direction, counterparty=counterparty, service_type=service_type)
    return render_template(
        "services.html", active_page="services", rows=rows, direction=direction,
        counterparty=counterparty, service_type=service_type,
        counterparties=db.list_service_counterparties(), service_types=db.list_service_types(),
        today=datetime.now().strftime("%Y-%m-%d"),
        can_create=db.has_permission(u, "services", "create"),
        can_delete=db.has_permission(u, "services", "delete"),
        year=year, month=month, years=available_years(), vat_rate=db.VAT_RATE,
    )


@app.route("/services/add", methods=["POST"])
@permission_required("services", "create")
def services_add():
    f = request.form
    if db.is_date_locked(f["date"]):
        flash(t("close.locked_error", g.lang), "error")
        return redirect(url_for("services_page"))
    if rate_missing_for(f["date"]):
        flash(t("flash.rate_required", g.lang), "error")
        return redirect(url_for("services_page"))
    db.add_service(
        date=f["date"], direction=f["direction"], counterparty=f["counterparty"],
        service_type=f["service_type"], amount_no_vat=parse_amount(f["amount_no_vat"]),
        currency=f["currency"], status=f["status"], description=f.get("description", ""),
    )
    return redirect(url_for("services_page"))


@app.route("/services/<int:service_id>/delete", methods=["POST"])
@permission_required("services", "delete")
def services_delete(service_id):
    row = db.get_service(service_id)
    if row and db.is_date_locked(row["date"]):
        flash(t("close.locked_error", g.lang), "error")
        return redirect(url_for("services_page"))
    db.delete_service(service_id)
    return redirect(url_for("services_page"))


@app.route("/services/<int:service_id>/edit", methods=["POST"])
@permission_required("services", "create")
def services_edit(service_id):
    row = db.get_service(service_id)
    if not row:
        abort(404)
    f = request.form
    if db.is_date_locked(row["date"]) or db.is_date_locked(f["date"]):
        flash(t("close.locked_error", g.lang), "error")
        return redirect(url_for("services_page"))
    db.update_service(
        service_id, date=f["date"], counterparty=f["counterparty"], service_type=f["service_type"],
        amount_no_vat=parse_amount(f["amount_no_vat"]), currency=f["currency"], status=f["status"],
        description=f.get("description", ""),
    )
    return redirect(url_for("services_page"))


# ---- Nalog (soliqlar) ----

@app.route("/taxes")
@permission_required("taxes", "view")
def taxes_page():
    year, month = get_period()
    if not year or not month:
        now = datetime.now()
        year, month = now.year, now.month
    u = current_user()
    rows = db.list_taxes(year, month)
    totals = {
        k: sum(r[k] for r in rows) for k in ("opening", "accrued", "paid", "closing", "debt", "overpayment")
    }
    locked = db.is_month_closed(f"{year:04d}-{month:02d}")
    return render_template(
        "taxes.html", active_page="taxes", rows=rows, totals=totals,
        tax_types=db.TAX_TYPES, existing_names=[r["tax_name"] for r in rows if r["accrued"] or r["paid"]],
        can_create=db.has_permission(u, "taxes", "create"),
        can_delete=db.has_permission(u, "taxes", "delete"),
        year=year, month=month, years=available_years(), locked=locked,
    )


@app.route("/taxes/save", methods=["POST"])
@permission_required("taxes", "create")
def taxes_save():
    f = request.form
    year, month = int(f["year"]), int(f["month"])
    if db.is_month_closed(f"{year:04d}-{month:02d}"):
        flash(t("close.locked_error", g.lang), "error")
        return redirect(url_for("taxes_page", year=year, month=month))
    db.upsert_tax(
        year=year, month=month, tax_name=f["tax_name"],
        accrued=parse_amount(f.get("accrued") or "0"), paid=parse_amount(f.get("paid") or "0"),
    )
    return redirect(url_for("taxes_page", year=year, month=month))


@app.route("/taxes/delete", methods=["POST"])
@permission_required("taxes", "delete")
def taxes_delete():
    f = request.form
    year, month = int(f["year"]), int(f["month"])
    if db.is_month_closed(f"{year:04d}-{month:02d}"):
        flash(t("close.locked_error", g.lang), "error")
        return redirect(url_for("taxes_page", year=year, month=month))
    db.delete_tax(year=year, month=month, tax_name=f["tax_name"])
    return redirect(url_for("taxes_page", year=year, month=month))


# ---- Oy yopish ----

@app.route("/period-close")
@super_admin_required
def period_close_page():
    months = list(reversed(db.list_relevant_months()))
    selected = request.args.get("ym") or (months[0] if months else None)
    checks, bal_uzs, bal_usd = ([], 0.0, 0.0) if not selected else db.month_checklist(selected)
    return render_template(
        "period_close.html", active_page="period_close",
        months=[(m, db.month_close_status(m)) for m in months],
        selected=selected, checks=checks, bal_uzs=bal_uzs, bal_usd=bal_usd,
        is_super_admin=current_user()["role"] == "super_admin",
    )


@app.route("/period-close/<ym>/close", methods=["POST"])
@super_admin_required
def period_close_close(ym):
    try:
        db.close_month(ym, current_user()["id"])
        flash(t("close.closed_success", g.lang), "success")
    except ValueError:
        flash(t("close.error", g.lang), "error")
    return redirect(url_for("period_close_page", ym=ym))


@app.route("/period-close/<ym>/reopen", methods=["POST"])
@super_admin_required
def period_close_reopen(ym):
    try:
        db.reopen_month(ym)
        flash(t("close.reopened_success", g.lang), "success")
    except ValueError:
        flash(t("close.reopen_order_error", g.lang), "error")
    return redirect(url_for("period_close_page", ym=ym))


# ---- Foydalanuvchilar (faqat Super Admin) ----

@app.route("/users")
@super_admin_required
def users_page():
    roles = db.list_roles()
    role_names = {r["id"]: r["name"] for r in roles}
    users = db.list_users()
    for u in users:
        u["role_name"] = role_names.get(u["role_id"])
    return render_template("users.html", active_page="users", users=users, roles=roles)


@app.route("/users/add", methods=["POST"])
@super_admin_required
def users_add():
    f = request.form
    try:
        db.add_user(f["username"], f["password"], f.get("full_name", ""), int(f["role_id"]))
        flash(t("flash.user_added", g.lang).format(u=f["username"]), "success")
    except sqlite3.IntegrityError:
        flash(t("flash.username_taken", g.lang).format(u=f["username"]), "error")
    except Exception as e:
        flash(t("flash.error_prefix", g.lang) + str(e), "error")
    return redirect(url_for("users_page"))


@app.route("/users/<int:user_id>/edit", methods=["POST"])
@super_admin_required
def users_edit(user_id):
    target = db.get_user_by_id(user_id)
    if not target or target["role"] == "super_admin":
        abort(404)
    f = request.form
    db.update_user(
        user_id, f.get("full_name", ""), int(f["role_id"]),
        is_active=bool(f.get("is_active")), password=f.get("password") or None,
    )
    return redirect(url_for("users_page"))


@app.route("/users/<int:user_id>/delete", methods=["POST"])
@super_admin_required
def users_delete(user_id):
    target = db.get_user_by_id(user_id)
    if target and target["role"] == "super_admin":
        flash(t("flash.cannot_delete_super", g.lang), "error")
    else:
        db.delete_user(user_id)
    return redirect(url_for("users_page"))


# ---- Rollar va huquqlar (faqat Super Admin) ----

def _parse_role_permissions(form):
    perms = {}
    for m in db.ROLE_MODULES:
        mod_perms = {a: True for a in m["actions"] if form.get(f"perm__{m['key']}__{a}")}
        if mod_perms:
            perms[m["key"]] = mod_perms
    return perms


@app.route("/roles")
@super_admin_required
def roles_page():
    roles = db.list_roles()
    for r in roles:
        r["perm_count"] = sum(len(v) for v in r["permissions"].values())
    return render_template(
        "roles.html", active_page="roles", roles=roles,
        modules=db.ROLE_MODULES, actions=db.ROLE_ACTIONS,
    )


@app.route("/roles/add", methods=["POST"])
@super_admin_required
def roles_add():
    f = request.form
    try:
        db.add_role(f["name"], f.get("description", ""), _parse_role_permissions(f))
        flash(t("flash.role_added", g.lang), "success")
    except Exception as e:
        flash(t("flash.error_prefix", g.lang) + str(e), "error")
    return redirect(url_for("roles_page"))


@app.route("/roles/<int:role_id>/edit", methods=["POST"])
@super_admin_required
def roles_edit(role_id):
    f = request.form
    db.update_role(role_id, f["name"], f.get("description", ""), _parse_role_permissions(f))
    return redirect(url_for("roles_page"))


@app.route("/roles/<int:role_id>/delete", methods=["POST"])
@super_admin_required
def roles_delete(role_id):
    try:
        db.delete_role(role_id)
    except ValueError as e:
        key = "flash.role_is_system" if str(e) == "system_role" else "flash.role_in_use"
        flash(t(key, g.lang), "error")
    return redirect(url_for("roles_page"))


# ---- Sozlamalar (faqat Super Admin) ----

@app.route("/settings")
@super_admin_required
def settings_page():
    with open(CONFIG_PATH, encoding="utf-8-sig") as f:
        cfg = json.load(f)
    return render_template(
        "settings.html", active_page="settings", cfg=cfg,
        opening_kassa_uzs=db.get_cash_opening("UZS", "kassa"),
        opening_kassa_usd=db.get_cash_opening("USD", "kassa"),
        opening_bank_uzs=db.get_cash_opening("UZS", "bank"),
        opening_bank_usd=db.get_cash_opening("USD", "bank"),
        opening_date=db.get_cash_opening_date() or datetime.now().strftime("%Y-%m-%d"),
        charter_uzs=db.get_setting("charter_capital_uzs", "0"),
        charter_usd=db.get_setting("charter_capital_usd", "0"),
        fixed_assets=db.list_fixed_assets(),
        today=datetime.now().strftime("%Y-%m-%d"),
        custom_categories=db.list_custom_categories(), forma2_groups=db.FORMA2_GROUPS,
        custom_cash_categories=db.list_custom_cash_categories(),
        cash_sections=db.CASH_SECTIONS,
    )


@app.route("/settings/save", methods=["POST"])
@super_admin_required
def settings_save():
    with open(CONFIG_PATH, encoding="utf-8-sig") as f:
        cfg = json.load(f)
    f = request.form
    cfg["api_client_id"] = f["api_client_id"]
    cfg["api_client_secret"] = f["api_client_secret"]
    cfg["property_id"] = f["property_id"]
    cfg["refresh_minutes"] = int(f["refresh_minutes"])
    with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2, ensure_ascii=False)
    flash(t("flash.settings_saved", g.lang), "success")
    return redirect(url_for("settings_page"))


@app.route("/settings/opening-balance", methods=["POST"])
@super_admin_required
def settings_opening_balance():
    f = request.form
    db.set_setting("cash_opening_kassa_uzs", parse_amount(f.get("opening_kassa_uzs") or 0))
    db.set_setting("cash_opening_kassa_usd", parse_amount(f.get("opening_kassa_usd") or 0))
    db.set_setting("cash_opening_bank_uzs", parse_amount(f.get("opening_bank_uzs") or 0))
    db.set_setting("cash_opening_bank_usd", parse_amount(f.get("opening_bank_usd") or 0))
    db.set_setting("cash_opening_date", f.get("opening_date") or "")
    flash(t("flash.settings_saved", g.lang), "success")
    return redirect(url_for("settings_page"))


# ---- Valyuta kursi (kunlik) — faqat Super Admin ----

@app.route("/exchange-rate")
@super_admin_required
def exchange_rate_page():
    rates = db.list_exchange_rates()
    return render_template(
        "exchange_rate.html", active_page="exchange_rate", rates=rates,
        latest_usd=rates[0]["uzs_per_usd"] if rates else None,
        latest_eur=next((r["uzs_per_eur"] for r in rates if r["uzs_per_eur"]), None),
        today=datetime.now().strftime("%Y-%m-%d"),
    )


@app.route("/exchange-rate/add", methods=["POST"])
@super_admin_required
def exchange_rate_add():
    f = request.form
    currency = f.get("currency") or "USD"
    db.set_exchange_rate(f["date"], parse_amount(f["rate"]), currency)
    flash(t("flash.settings_saved", g.lang), "success")
    return redirect(url_for("exchange_rate_page"))


@app.route("/exchange-rate/<date_str>/delete", methods=["POST"])
@super_admin_required
def exchange_rate_delete(date_str):
    currency = request.form.get("currency") or "USD"
    db.delete_exchange_rate(date_str, currency)
    return redirect(url_for("exchange_rate_page"))


@app.route("/exchange-rate/fetch-cbu", methods=["POST"])
@super_admin_required
def exchange_rate_fetch_cbu():
    date_str = request.form.get("date") or datetime.now().strftime("%Y-%m-%d")
    currency = request.form.get("currency") or "USD"
    try:
        rate = db.fetch_cbu_rate(date_str, currency)
        db.set_exchange_rate(date_str, rate, currency)
        flash(t("rate.cbu_fetch_success", g.lang).format(rate=format_money(rate)), "success")
    except Exception:
        flash(t("rate.cbu_fetch_error", g.lang), "error")
    return redirect(url_for("exchange_rate_page"))


@app.route("/settings/charter-capital", methods=["POST"])
@super_admin_required
def settings_charter_capital():
    f = request.form
    db.set_setting("charter_capital_uzs", parse_amount(f.get("charter_uzs") or 0))
    db.set_setting("charter_capital_usd", parse_amount(f.get("charter_usd") or 0))
    flash(t("flash.settings_saved", g.lang), "success")
    return redirect(url_for("settings_page"))


@app.route("/settings/fixed-asset/add", methods=["POST"])
@super_admin_required
def settings_fixed_asset_add():
    f = request.form
    db.add_fixed_asset(f["name"], parse_amount(f["value"]), f["currency"], f["purchase_date"])
    flash(t("flash.settings_saved", g.lang), "success")
    return redirect(url_for("settings_page"))


@app.route("/settings/fixed-asset/<int:asset_id>/delete", methods=["POST"])
@super_admin_required
def settings_fixed_asset_delete(asset_id):
    db.delete_fixed_asset(asset_id)
    return redirect(url_for("settings_page"))


@app.route("/settings/category/add", methods=["POST"])
@super_admin_required
def settings_category_add():
    f = request.form
    name = (f.get("name") or "").strip()
    if name:
        try:
            db.add_custom_category(name, f["group_key"])
            flash(t("flash.settings_saved", g.lang), "success")
        except ValueError:
            flash(t("flash.error_prefix", g.lang) + "invalid_group", "error")
    return redirect(url_for("settings_page"))


@app.route("/settings/category/<int:cat_id>/delete", methods=["POST"])
@super_admin_required
def settings_category_delete(cat_id):
    db.delete_custom_category(cat_id)
    return redirect(url_for("settings_page"))


@app.route("/settings/cash-category/add", methods=["POST"])
@super_admin_required
def settings_cash_category_add():
    f = request.form
    name = (f.get("name") or "").strip()
    if name:
        try:
            db.add_custom_cash_category(name, f["section"], f["type"])
            flash(t("flash.settings_saved", g.lang), "success")
        except ValueError:
            flash(t("flash.error_prefix", g.lang) + "invalid_section_or_type", "error")
    return redirect(url_for("settings_page"))


@app.route("/settings/cash-category/<int:cat_id>/delete", methods=["POST"])
@super_admin_required
def settings_cash_category_delete(cat_id):
    db.delete_custom_cash_category(cat_id)
    return redirect(url_for("settings_page"))


if __name__ == "__main__":
    initial_password = db.init_db()
    if initial_password:
        # Parol atayin log() (run_log.txt, doimiy saqlanadigan fayl) ga
        # yozilmaydi — faqat konsolda bir martalik ko'rsatiladi, aks holda
        # log fayliga kirish huquqi bo'lgan har kim uni istalgan vaqt
        # o'qib olishi mumkin bo'lardi.
        log("BIRINCHI MARTA ISHGA TUSHIRILDI. Super Admin hisobi yaratildi (parol konsolda ko'rsatildi).")
        print(f"\n{'='*60}\nSUPER ADMIN HISOBI YARATILDI:\n  Login: admin\n  Parol: {initial_password}\n"
              f"Bu parolni saqlab qo'ying, keyin uni /users orqali xohlagan\nfoydalanuvchiga bering.\n{'='*60}\n")
    threading.Thread(target=background_loop, daemon=True).start()
    app.run(host="127.0.0.1", port=5000, debug=False)

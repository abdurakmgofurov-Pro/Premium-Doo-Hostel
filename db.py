# -*- coding: utf-8 -*-
"""SQLite baza: qo'lda kiritiladigan xarajatlar + foydalanuvchilar/huquqlar."""
import calendar
import json
import re
import secrets
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from werkzeug.security import generate_password_hash

DB_PATH = Path(__file__).resolve().parent / "data.db"

# Xarajat turkumlari — Forma 2 (Moliyaviy natijalar to'g'risidagi hisobot)
# tuzilmasiga mos guruhlarga bo'lingan, buxgalteriya amaliyotidagi kabi.
FORMA2_GROUPS = [
    ("tannarx", "Sotilgan xizmatlar tannarxi (asosiy operatsion xarajatlar)"),
    ("sotish", "Sotish xarajatlari"),
    ("mamuriy", "Ma'muriy (boshqaruv) xarajatlari"),
    ("boshqa_operatsion", "Boshqa operatsion xarajatlar"),
    ("moliyaviy", "Moliyaviy xarajatlar"),
    ("soliq", "Soliqlar va majburiy to'lovlar"),
]
FORMA2_GROUP_LABELS = dict(FORMA2_GROUPS)

CATEGORIES = [
    {"name": "Xodimlar ish haqi (operatsion)", "group": "tannarx"},
    {"name": "Ijtimoiy sug'urta ajratmalari", "group": "tannarx"},
    {"name": "Kommunal xizmatlar", "group": "tannarx"},
    {"name": "Xona ta'minoti (anjom, tozalash, oziq-ovqat)", "group": "tannarx"},
    {"name": "Texnik xizmat / ta'mirlash", "group": "tannarx"},
    {"name": "OTA komissiyasi (booking.com, Agoda va h.k.)", "group": "sotish"},
    {"name": "Marketing / reklama", "group": "sotish"},
    {"name": "Ma'muriy xodimlar ish haqi", "group": "mamuriy"},
    {"name": "Ijara haqi", "group": "mamuriy"},
    {"name": "Aloqa / internet", "group": "mamuriy"},
    {"name": "Transport", "group": "mamuriy"},
    {"name": "Buxgalteriya / yuridik xizmatlar", "group": "mamuriy"},
    {"name": "Ofis xarajatlari", "group": "mamuriy"},
    {"name": "Kompaniya bilan boshqa hisob-kitob", "group": "boshqa_operatsion"},
    {"name": "Boshqa operatsion xarajat", "group": "boshqa_operatsion"},
    {"name": "Bank xizmat haqi", "group": "moliyaviy"},
    {"name": "Kredit foizlari", "group": "moliyaviy"},
    {"name": "Foyda solig'i", "group": "soliq"},
    {"name": "Mulk solig'i", "group": "soliq"},
    {"name": "Boshqa soliq va yig'imlar", "group": "soliq"},
    {"name": "Xizmat/tovar sotib olish (Xizmatlar orqali)", "group": "tannarx"},
]
CATEGORY_GROUP = {c["name"]: c["group"] for c in CATEGORIES}

# Xizmatlar (Услуги) sahifasi — QQS (NDS) standart stavkasi.
VAT_RATE = 0.12
SERVICE_PURCHASE_CATEGORY = "Xizmat/tovar sotib olish (Xizmatlar orqali)"

TAX_TYPES = ["NDS", "Foyda solig'i", "NDFL", "INPS", "Ijtimoiy soliq (ESP)", "Yer solig'i", "Boshqa soliqlar"]

# "Daromad" turidagi tranzaksiyalar uchun turkumlar. Bittasi alohida ma'no
# tashiydi: mehmonga xizmat sotish — bu oddiy daromad emas, balki Forma 2'ning
# 010-qatoriga (asosiy tushum, Exely tushumi ustiga) qo'shiladigan realizatsiya
# daromadi (eski, endi bekor qilingan "Xizmatlar" sahifasining o'rnini bosadi).
SERVICE_REVENUE_CATEGORY = "Mehmonga xizmat sotish (asosiy tushum)"
INCOME_CATEGORIES = [SERVICE_REVENUE_CATEGORY, "Boshqa (operatsion bo'lmagan) daromad"]

# Kassa/bank prixod-rasxodi — Forma 3 (Pul oqimlari to'g'risidagi hisobot)
# uch bo'limiga (operatsion/investitsion/moliyaviy) mos guruhlangan.
CASH_SOURCES = [("kassa", "Kassa"), ("bank", "Bank")]
CASH_SECTIONS = [
    ("operatsion", "Operatsion faoliyat"),
    ("investitsion", "Investitsion faoliyat"),
    ("moliyaviy", "Moliyaviy faoliyat"),
]
CASH_SECTION_LABELS = dict(CASH_SECTIONS)

CASH_CATEGORIES = [
    {"code": "1001", "name": "Mehmonlardan naqd/bank tushumi", "section": "operatsion", "type": "income"},
    {"code": "1002", "name": "Boshqa operatsion tushum", "section": "operatsion", "type": "income"},
    {"code": "2001", "name": "Yetkazib beruvchilarga to'lov", "section": "operatsion", "type": "expense"},
    {"code": "2002", "name": "Ish haqi to'lovi", "section": "operatsion", "type": "expense"},
    {"code": "2003", "name": "Kommunal to'lovlar", "section": "operatsion", "type": "expense"},
    {"code": "2004", "name": "Soliq va majburiy to'lovlar", "section": "operatsion", "type": "expense"},
    {"code": "2005", "name": "Boshqa operatsion chiqim", "section": "operatsion", "type": "expense"},
    {"code": "3001", "name": "Asosiy vosita sotish", "section": "investitsion", "type": "income"},
    {"code": "3501", "name": "Asosiy vosita sotib olish", "section": "investitsion", "type": "expense"},
    {"code": "4001", "name": "Kredit / qarz olish", "section": "moliyaviy", "type": "income"},
    {"code": "4002", "name": "Egalar tomonidan mablag' kiritish", "section": "moliyaviy", "type": "income"},
    {"code": "4501", "name": "Kredit / qarz qaytarish", "section": "moliyaviy", "type": "expense"},
    {"code": "4502", "name": "Dividend / mablag' chiqarish", "section": "moliyaviy", "type": "expense"},
    {"code": "1003", "name": "Bar/mini-bar savdosi", "section": "operatsion", "type": "income"},
    {"code": "2006", "name": "Bar/mini-bar tovar xaridi", "section": "operatsion", "type": "expense"},
    {"code": "2007", "name": "Xodimlar/kontragentlarga avans", "section": "operatsion", "type": "expense"},
]
CASH_CATEGORY_MAP = {c["name"]: c for c in CASH_CATEGORIES}

# Bar/mini-bar modulida yaratiladigan avtomatik kassa yozuvlari shu ikki
# turkumdan foydalanadi (yuqoridagi CASH_CATEGORIES'ga ro'yxatga olingan,
# aks holda oy yopish tekshiruvidagi "codes" bandi buzilardi).
BAR_SALE_CATEGORY = "Bar/mini-bar savdosi"
BAR_RESTOCK_CATEGORY = "Bar/mini-bar tovar xaridi"

# Rollar tizimi: har bir "custom" foydalanuvchi bitta qayta ishlatiladigan
# Rolga (roles jadvali) biriktiriladi, Rolning o'zida modul x amal
# matritsasi saqlanadi. super_admin har doim hammasiga ega (shu jumladan
# quyidagi ro'yxatga kirmaydigan Foydalanuvchilar/Sozlamalar/Dollar kursi/
# Oy yopish bo'limlariga ham) — bu bo'limlar ATAYLAB matritsaga kiritilmagan,
# faqat super_admin uchun qoladi.
ROLE_ACTIONS = ("view", "create", "edit", "delete", "export")
ROLE_MODULES = [
    {"key": "dashboard", "name": "Dashboard", "actions": ("view",)},
    {"key": "bookings", "name": "Bronlar", "actions": ("view",)},
    {"key": "transactions", "name": "Xarajatlar", "actions": ("view", "create", "delete")},
    {"key": "reports", "name": "Hisobotlar", "actions": ("view", "export")},
    {"key": "cash", "name": "Kassa/Bank", "actions": ("view", "create", "delete")},
    {"key": "bar", "name": "Bar/Sklad", "actions": ("view", "create", "edit", "delete")},
    {"key": "ledger", "name": "Дт/Кт", "actions": ("view", "create", "delete")},
    {"key": "services", "name": "Xizmatlar", "actions": ("view", "create", "delete")},
    {"key": "taxes", "name": "Nalog", "actions": ("view", "create", "delete")},
]
ROLE_MODULE_KEYS = [m["key"] for m in ROLE_MODULES]

DEFAULT_ROLE_SEEDS = [
    {
        "name": "Administrator", "is_system": 1,
        "description": "Barcha oddiy bo'limlarga to'liq huquq.",
        "permissions": {
            "dashboard": {"view": True},
            "bookings": {"view": True},
            "transactions": {"view": True, "create": True, "delete": True},
            "reports": {"view": True, "export": True},
            "cash": {"view": True, "create": True, "delete": True},
            "bar": {"view": True, "create": True, "edit": True, "delete": True},
            "ledger": {"view": True, "create": True, "delete": True},
            "services": {"view": True, "create": True, "delete": True},
            "taxes": {"view": True, "create": True, "delete": True},
        },
    },
    {
        "name": "Buxgalter", "is_system": 0,
        "description": "Moliyaviy operatsiyalar va hisobotlar.",
        "permissions": {
            "dashboard": {"view": True},
            "bookings": {"view": True},
            "transactions": {"view": True, "create": True, "delete": True},
            "reports": {"view": True, "export": True},
            "cash": {"view": True, "create": True, "delete": True},
            "ledger": {"view": True, "create": True, "delete": True},
            "services": {"view": True, "create": True, "delete": True},
            "taxes": {"view": True, "create": True, "delete": True},
        },
    },
    {
        "name": "Bar/Sklad menejeri", "is_system": 0,
        "description": "Faqat Bar/Sklad operatsiyalari.",
        "permissions": {
            "dashboard": {"view": True},
            "bookings": {"view": True},
            "bar": {"view": True, "create": True, "edit": True, "delete": True},
        },
    },
    {
        "name": "Kuzatuvchi", "is_system": 0,
        "description": "Faqat ko'rish, hech narsa o'zgartira olmaydi.",
        "permissions": {m["key"]: {"view": True} for m in ROLE_MODULES},
    },
    {
        "name": "Huquqsiz", "is_system": 1,
        "description": "Hech qanday huquq yo'q (yangi foydalanuvchi uchun standart).",
        "permissions": {},
    },
]


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('expense', 'income')),
            category TEXT NOT NULL,
            counterparty TEXT,
            description TEXT,
            amount REAL NOT NULL,
            currency TEXT NOT NULL CHECK(currency IN ('UZS', 'USD')),
            status TEXT NOT NULL CHECK(status IN ('paid', 'unpaid')) DEFAULT 'paid',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            role TEXT NOT NULL CHECK(role IN ('super_admin', 'admin', 'custom')),
            permissions TEXT NOT NULL DEFAULT '[]',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    users_cols = [r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
    if "role_id" not in users_cols:
        conn.execute("ALTER TABLE users ADD COLUMN role_id INTEGER")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            permissions TEXT NOT NULL DEFAULT '{}',
            is_system INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    if conn.execute("SELECT COUNT(*) c FROM roles").fetchone()["c"] == 0:
        for seed in DEFAULT_ROLE_SEEDS:
            conn.execute(
                "INSERT INTO roles (name, description, permissions, is_system) VALUES (?,?,?,?)",
                (seed["name"], seed["description"], json.dumps(seed["permissions"]), seed["is_system"]),
            )
        conn.commit()

    # Eski qattiq kodlangan role='admin' foydalanuvchilarni yangi Rollar
    # tizimiga o'tkazish — "Administrator" rolini biriktiramiz (bir martalik,
    # xavfsiz: faqat role_id hali bo'sh bo'lgan 'admin' qatorlarga tegadi).
    admin_role = conn.execute("SELECT id FROM roles WHERE name='Administrator'").fetchone()
    if admin_role:
        conn.execute(
            "UPDATE users SET role='custom', role_id=? WHERE role='admin' AND role_id IS NULL",
            (admin_role["id"],),
        )
        conn.commit()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bookings_cache (
            number TEXT PRIMARY KEY,
            raw_json TEXT NOT NULL,
            modified_at TEXT,
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    existing_cols = [r["name"] for r in conn.execute("PRAGMA table_info(bookings_cache)").fetchall()]
    if "modified_at" not in existing_cols:
        conn.execute("ALTER TABLE bookings_cache ADD COLUMN modified_at TEXT")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS exely_expense_imports (
            fingerprint TEXT PRIMARY KEY,
            transaction_id INTEGER,
            imported_at TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS cash_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            source TEXT NOT NULL CHECK(source IN ('kassa', 'bank')),
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            section TEXT NOT NULL CHECK(section IN ('operatsion', 'investitsion', 'moliyaviy')),
            category TEXT NOT NULL,
            counterparty TEXT,
            description TEXT,
            amount REAL NOT NULL,
            currency TEXT NOT NULL CHECK(currency IN ('UZS', 'USD')),
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    cash_tx_cols = [r["name"] for r in conn.execute("PRAGMA table_info(cash_transactions)").fetchall()]
    if "note_label" not in cash_tx_cols:
        conn.execute("ALTER TABLE cash_transactions ADD COLUMN note_label TEXT")
    if "transaction_id" not in cash_tx_cols:
        conn.execute("ALTER TABLE cash_transactions ADD COLUMN transaction_id INTEGER")

    # Sozlamalar orqali qo'shiladigan qo'shimcha turkumlar — o'rnatilgan
    # CATEGORIES/CASH_CATEGORIES ro'yxatlariga qo'shimcha (ularni
    # o'chirmaydi/almashtirmaydi), mavjud guruh/bo'lim tuzilmasi ichida.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS custom_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            group_key TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS custom_cash_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL UNIQUE,
            section TEXT NOT NULL CHECK(section IN ('operatsion', 'investitsion', 'moliyaviy')),
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Hamkorlar (kontragentlar) ma'lumotnomasi — nomi/INN bo'yicha oldindan
    # kiritilgan kompaniyalar ro'yxati, "counterparty" matn maydonlari
    # bo'lgan barcha formalarda (Xarajatlar, Kassa/Bank, Bar/Sklad,
    # Xizmatlar) avtomatik taklif (datalist) sifatida ishlatiladi.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS counterparties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            inn TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(name, inn)
        )
    """)

    # Xizmatlar (Услуги) — QQS (NDS) hisob-kitobi bilan olingan/ko'rsatilgan
    # xizmatlar reestri. Har bir yozuv `transactions`da mos xarajat/daromad
    # yozuvini avtomatik yaratadi (transaction_id orqali bog'lanadi).
    conn.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            direction TEXT NOT NULL CHECK(direction IN ('received', 'rendered')),
            counterparty TEXT NOT NULL,
            service_type TEXT NOT NULL,
            amount_no_vat REAL NOT NULL,
            vat_amount REAL NOT NULL,
            total REAL NOT NULL,
            currency TEXT NOT NULL CHECK(currency IN ('UZS', 'USD')) DEFAULT 'UZS',
            status TEXT NOT NULL CHECK(status IN ('paid', 'unpaid')) DEFAULT 'paid',
            description TEXT,
            transaction_id INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS taxes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            tax_name TEXT NOT NULL,
            accrued REAL NOT NULL DEFAULT 0,
            paid REAL NOT NULL DEFAULT 0,
            currency TEXT NOT NULL CHECK(currency IN ('UZS', 'USD')) DEFAULT 'UZS',
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(year, month, tax_name, currency)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS exely_cash_imports (
            fingerprint TEXT PRIMARY KEY,
            cash_id INTEGER,
            imported_at TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS bar_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            unit TEXT NOT NULL DEFAULT 'dona',
            cost_price REAL NOT NULL DEFAULT 0,
            sale_price REAL NOT NULL DEFAULT 0,
            currency TEXT NOT NULL CHECK(currency IN ('UZS', 'USD')) DEFAULT 'UZS',
            stock_qty REAL NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    old_bar_tx_cols = [r["name"] for r in conn.execute("PRAGMA table_info(bar_transactions)").fetchall()]
    if old_bar_tx_cols and "status" not in old_bar_tx_cols:
        conn.execute("ALTER TABLE bar_transactions RENAME TO bar_transactions_old_nostatus")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bar_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            ttype TEXT NOT NULL CHECK(ttype IN ('restock', 'sale')),
            qty REAL NOT NULL,
            unit_price REAL NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL CHECK(currency IN ('UZS', 'USD')),
            source TEXT NOT NULL CHECK(source IN ('kassa', 'bank')) DEFAULT 'kassa',
            counterparty TEXT,
            description TEXT,
            cash_transaction_id INTEGER,
            status TEXT NOT NULL CHECK(status IN ('paid', 'unpaid')) DEFAULT 'paid',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    if old_bar_tx_cols and "status" not in old_bar_tx_cols:
        conn.execute("""
            INSERT INTO bar_transactions (id, date, product_id, product_name, ttype, qty, unit_price,
                amount, currency, source, counterparty, description, cash_transaction_id, status, created_at)
            SELECT id, date, product_id, product_name, ttype, qty, unit_price,
                amount, currency, source, counterparty, description, cash_transaction_id, 'paid', created_at
            FROM bar_transactions_old_nostatus
        """)
        conn.execute("DROP TABLE bar_transactions_old_nostatus")

    old_payments_sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='payments'"
    ).fetchone()
    if old_payments_sql and "'cash_transaction'" not in old_payments_sql["sql"]:
        conn.execute("ALTER TABLE payments RENAME TO payments_old_srctype")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL CHECK(source_type IN ('transaction', 'service', 'bar_transaction', 'cash_transaction')),
            source_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL CHECK(currency IN ('UZS', 'USD')),
            note TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    if old_payments_sql and "'cash_transaction'" not in old_payments_sql["sql"]:
        conn.execute("""
            INSERT INTO payments (id, source_type, source_id, date, amount, currency, note, created_at)
            SELECT id, source_type, source_id, date, amount, currency, note, created_at
            FROM payments_old_srctype
        """)
        conn.execute("DROP TABLE payments_old_srctype")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fixed_assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            value REAL NOT NULL,
            currency TEXT NOT NULL CHECK(currency IN ('UZS', 'USD')),
            purchase_date TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS closed_months (
            year_month TEXT PRIMARY KEY,
            closed_by INTEGER,
            closed_at TEXT DEFAULT (datetime('now')),
            snapshot_json TEXT
        )
    """)
    # Kurs jadvali avval oylik (year_month) edi, endi KUNLIK (date) — eski
    # o'rnatishlarda mavjud oylik yozuvlarni yo'qotmaslik uchun ko'chiriladi
    # (har oy oxirgi kuniga qo'yiladi).
    old_cols = [r["name"] for r in conn.execute("PRAGMA table_info(exchange_rates)").fetchall()]
    if old_cols and "year_month" in old_cols:
        conn.execute("ALTER TABLE exchange_rates RENAME TO exchange_rates_old_ym")
        conn.execute("""
            CREATE TABLE exchange_rates (
                date TEXT PRIMARY KEY,
                uzs_per_usd REAL NOT NULL,
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        for r in conn.execute("SELECT * FROM exchange_rates_old_ym").fetchall():
            y, m = (int(x) for x in r["year_month"].split("-"))
            last_day = calendar.monthrange(y, m)[1]
            conn.execute(
                "INSERT OR REPLACE INTO exchange_rates (date, uzs_per_usd, updated_at) VALUES (?,?,?)",
                (f"{y:04d}-{m:02d}-{last_day:02d}", r["uzs_per_usd"], r["updated_at"]),
            )
        conn.execute("DROP TABLE exchange_rates_old_ym")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS exchange_rates (
            date TEXT PRIMARY KEY,
            uzs_per_usd REAL NOT NULL,
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    rate_cols = [r["name"] for r in conn.execute("PRAGMA table_info(exchange_rates)").fetchall()]
    if "uzs_per_eur" not in rate_cols:
        conn.execute("ALTER TABLE exchange_rates ADD COLUMN uzs_per_eur REAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()

    row = conn.execute("SELECT COUNT(*) c FROM users WHERE role='super_admin'").fetchone()
    initial_password = None
    if row["c"] == 0:
        initial_password = secrets.token_urlsafe(9)
        conn.execute(
            "INSERT INTO users (username, password_hash, full_name, role, permissions) VALUES (?,?,?,?,?)",
            ("admin", generate_password_hash(initial_password), "Super Admin", "super_admin", "[]"),
        )
        conn.commit()
    conn.close()
    _backfill_payments_for_paid()
    return initial_password


def _backfill_payments_for_paid():
    """"To'langan" deb belgilangan xarajat/xizmatlar uchun to'lov yozuvi
    yo'q bo'lsa, avtomatik to'liq to'lov yozuvi qo'shadi — shu orqali
    Дт/Кт registri (payments jadvaliga asoslangan) eski ma'lumotlar bilan
    ham to'g'ri ishlaydi. Har ishga tushirishda xavfsiz (idempotent):
    faqat hali to'lov yozuvi yo'q manbalarga qo'shadi."""
    conn = get_conn()
    existing = {
        (r["source_type"], r["source_id"])
        for r in conn.execute("SELECT DISTINCT source_type, source_id FROM payments").fetchall()
    }
    to_insert = []
    for r in conn.execute("SELECT id, date, amount, currency FROM transactions WHERE status='paid'").fetchall():
        if ("transaction", r["id"]) not in existing:
            to_insert.append(("transaction", r["id"], r["date"], r["amount"], r["currency"], "Avtomatik (holat: to'langan)"))
    for r in conn.execute(
        "SELECT id, date, amount, currency FROM bar_transactions WHERE ttype='restock' AND status='paid'"
    ).fetchall():
        if ("bar_transaction", r["id"]) not in existing:
            to_insert.append(("bar_transaction", r["id"], r["date"], r["amount"], r["currency"], "Avtomatik (holat: to'langan)"))
    if to_insert:
        conn.executemany(
            "INSERT INTO payments (source_type, source_id, date, amount, currency, note) VALUES (?,?,?,?,?,?)",
            to_insert,
        )
        conn.commit()
    conn.close()


def add_transaction(date, ttype, category, counterparty, description, amount, currency, status):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO transactions (date, type, category, counterparty, description, amount, currency, status)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (date, ttype, category, counterparty, description, amount, currency, status),
    )
    if status == "paid":
        conn.execute(
            "INSERT INTO payments (source_type, source_id, date, amount, currency, note) VALUES ('transaction',?,?,?,?,?)",
            (cur.lastrowid, date, amount, currency, ""),
        )
    conn.commit()
    tx_id = cur.lastrowid
    conn.close()
    return tx_id


def add_service(date, direction, counterparty, service_type, amount_no_vat, currency, status, description=""):
    """Xizmatlar (Услуги): olingan (received) yoki ko'rsatilgan (rendered)
    xizmat. QQS 12% avtomatik hisoblanadi, so'ng mos `transactions` yozuvi
    (xarajat yoki daromad) avtomatik yaratiladi — shu orqali Forma 2 va
    (kontragent + status='unpaid' bo'lsa) Дт/Кт'ga ham avtomatik bog'lanadi."""
    amount_no_vat = float(amount_no_vat)
    vat_amount = round(amount_no_vat * VAT_RATE, 2)
    total = round(amount_no_vat + vat_amount, 2)
    ttype = "expense" if direction == "received" else "income"
    category = SERVICE_PURCHASE_CATEGORY if direction == "received" else SERVICE_REVENUE_CATEGORY

    tx_id = add_transaction(
        date=date, ttype=ttype, category=category, counterparty=counterparty,
        description=description or service_type, amount=total, currency=currency, status=status,
    )

    conn = get_conn()
    conn.execute(
        "INSERT INTO services (date, direction, counterparty, service_type, amount_no_vat, vat_amount, total,"
        " currency, status, description, transaction_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (date, direction, counterparty, service_type, amount_no_vat, vat_amount, total,
         currency, status, description, tx_id),
    )
    conn.commit()
    conn.close()
    return tx_id


def update_service(service_id, date, counterparty, service_type, amount_no_vat, currency, status, description=""):
    """Yo'nalish (received/rendered) tahrirlanmaydi — u xarajat/daromad va
    Forma2 turkumini belgilaydi; boshqasi (sana, kontragent, summa, holati,
    izoh) tahrirlanadi, bog'langan `transactions` yozuvi va uning to'lovi
    (holat o'zgarsa — qo'shiladi yoki o'chiriladi) sinxron yangilanadi."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM services WHERE id=?", (service_id,)).fetchone()
    if not row:
        conn.close()
        return
    amount_no_vat = float(amount_no_vat)
    vat_amount = round(amount_no_vat * VAT_RATE, 2)
    total = round(amount_no_vat + vat_amount, 2)
    ttype = "expense" if row["direction"] == "received" else "income"

    conn.execute(
        "UPDATE services SET date=?, counterparty=?, service_type=?, amount_no_vat=?, vat_amount=?, total=?,"
        " currency=?, status=?, description=? WHERE id=?",
        (date, counterparty, service_type, amount_no_vat, vat_amount, total, currency, status, description,
         service_id),
    )
    tx_id = row["transaction_id"]
    if tx_id:
        conn.execute(
            "UPDATE transactions SET date=?, counterparty=?, description=?, amount=?, currency=?, status=?"
            " WHERE id=?",
            (date, counterparty, description or service_type, total, currency, status, tx_id),
        )
        existing_payment = conn.execute(
            "SELECT id FROM payments WHERE source_type='transaction' AND source_id=?", (tx_id,)
        ).fetchone()
        if status == "paid":
            if existing_payment:
                conn.execute(
                    "UPDATE payments SET date=?, amount=?, currency=? WHERE id=?",
                    (date, total, currency, existing_payment["id"]),
                )
            else:
                conn.execute(
                    "INSERT INTO payments (source_type, source_id, date, amount, currency, note)"
                    " VALUES ('transaction',?,?,?,?,?)",
                    (tx_id, date, total, currency, ""),
                )
        elif existing_payment:
            conn.execute("DELETE FROM payments WHERE id=?", (existing_payment["id"],))
        # Agar shu transactionga Kassa/Bank tarafidan bog'langan cash
        # yozuvi bo'lsa (mas. bank-import orqali kelgan xizmat to'lovi),
        # uni ham sinxron yangilaymiz — aks holda Kassa/Bank sahifasi
        # eskirgan summani ko'rsatib qoladi.
        conn.execute(
            "UPDATE cash_transactions SET date=?, counterparty=?, description=?, amount=?, currency=?"
            " WHERE transaction_id=?",
            (date, counterparty, description or service_type, total, currency, tx_id),
        )
    conn.commit()
    conn.close()


def delete_service(service_id):
    conn = get_conn()
    row = conn.execute("SELECT transaction_id FROM services WHERE id=?", (service_id,)).fetchone()
    conn.close()
    if row and row["transaction_id"]:
        delete_transaction(row["transaction_id"])
    conn = get_conn()
    conn.execute("DELETE FROM services WHERE id=?", (service_id,))
    conn.commit()
    conn.close()


def list_services(year=None, month=None, direction=None, counterparty=None, service_type=None):
    conn = get_conn()
    q = "SELECT * FROM services WHERE 1=1"
    params = []
    if year and month:
        q += " AND substr(date,1,7)=?"
        params.append(f"{int(year):04d}-{int(month):02d}")
    if direction:
        q += " AND direction=?"
        params.append(direction)
    if counterparty:
        q += " AND counterparty=?"
        params.append(counterparty)
    if service_type:
        q += " AND service_type=?"
        params.append(service_type)
    q += " ORDER BY date DESC, id DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_service_counterparties():
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT counterparty FROM services WHERE counterparty IS NOT NULL AND trim(counterparty)<>'' ORDER BY counterparty"
    ).fetchall()
    conn.close()
    return [r["counterparty"] for r in rows]


def list_service_types():
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT service_type FROM services WHERE service_type IS NOT NULL AND trim(service_type)<>'' ORDER BY service_type"
    ).fetchall()
    conn.close()
    return [r["service_type"] for r in rows]


def get_service(service_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM services WHERE id=?", (service_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ---- Nalog (soliqlar) — davr bo'yicha qo'lda kiritiladigan hisob ----

def _period_key(year, month):
    return int(year) * 100 + int(month)


def get_tax_opening(year, month, tax_name, currency="UZS"):
    """Berilgan davrdan OLDINGI barcha yozuvlar bo'yicha kumulyativ
    qoldiq (Долг на начало) — qo'lda kiritilmaydi, oldingi accrued/paid'dan
    avtomatik hisoblanadi."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT year, month, accrued, paid FROM taxes WHERE tax_name=? AND currency=?",
        (tax_name, currency),
    ).fetchall()
    conn.close()
    key = _period_key(year, month)
    total = 0.0
    for r in rows:
        if _period_key(r["year"], r["month"]) < key:
            total += r["accrued"] - r["paid"]
    return round(total, 2)


def list_taxes(year, month, currency="UZS"):
    conn = get_conn()
    rows = {
        r["tax_name"]: dict(r)
        for r in conn.execute(
            "SELECT * FROM taxes WHERE year=? AND month=? AND currency=?", (year, month, currency)
        ).fetchall()
    }
    conn.close()
    result = []
    for name in TAX_TYPES:
        r = rows.get(name, {"accrued": 0.0, "paid": 0.0})
        opening = get_tax_opening(year, month, name, currency)
        closing = round(opening + r["accrued"] - r["paid"], 2)
        result.append({
            "tax_name": name, "accrued": r["accrued"], "paid": r["paid"],
            "opening": opening, "closing": closing,
            "debt": max(closing, 0.0), "overpayment": max(-closing, 0.0),
        })
    return result


def upsert_tax(year, month, tax_name, accrued, paid, currency="UZS"):
    conn = get_conn()
    conn.execute(
        "INSERT INTO taxes (year, month, tax_name, accrued, paid, currency) VALUES (?,?,?,?,?,?)"
        " ON CONFLICT(year, month, tax_name, currency) DO UPDATE SET accrued=excluded.accrued, paid=excluded.paid",
        (year, month, tax_name, accrued, paid, currency),
    )
    conn.commit()
    conn.close()


def delete_tax(year, month, tax_name, currency="UZS"):
    conn = get_conn()
    conn.execute(
        "DELETE FROM taxes WHERE year=? AND month=? AND tax_name=? AND currency=?",
        (year, month, tax_name, currency),
    )
    conn.commit()
    conn.close()


def exely_import_fingerprint(date_str, amount, currency, description, counterparty):
    import hashlib
    raw = f"{date_str}|{amount}|{currency}|{description}|{counterparty}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def exely_import_exists(fingerprint):
    conn = get_conn()
    row = conn.execute("SELECT 1 FROM exely_expense_imports WHERE fingerprint=?", (fingerprint,)).fetchone()
    conn.close()
    return row is not None


def exely_cash_import_exists(fingerprint):
    conn = get_conn()
    row = conn.execute("SELECT 1 FROM exely_cash_imports WHERE fingerprint=?", (fingerprint,)).fetchone()
    conn.close()
    return row is not None


def exely_cash_import_commit(fingerprint, cash_id=None):
    conn = get_conn()
    conn.execute("INSERT INTO exely_cash_imports (fingerprint, cash_id) VALUES (?,?)", (fingerprint, cash_id))
    conn.commit()
    conn.close()


def exely_import_commit_row(fingerprint, date, category, counterparty, description, amount, currency):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO transactions (date, type, category, counterparty, description, amount, currency, status)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (date, "expense", category, counterparty, description, amount, currency, "paid"),
    )
    tx_id = cur.lastrowid
    conn.execute(
        "INSERT INTO payments (source_type, source_id, date, amount, currency, note) VALUES ('transaction',?,?,?,?,?)",
        (tx_id, date, amount, currency, "Exely import"),
    )
    conn.execute(
        "INSERT INTO exely_expense_imports (fingerprint, transaction_id) VALUES (?,?)",
        (fingerprint, tx_id),
    )
    conn.commit()
    conn.close()
    return tx_id


def get_transaction(tx_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM transactions WHERE id=?", (tx_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_transaction(tx_id):
    conn = get_conn()
    conn.execute("DELETE FROM payments WHERE source_type='transaction' AND source_id=?", (tx_id,))
    conn.execute("DELETE FROM transactions WHERE id=?", (tx_id,))
    conn.commit()
    conn.close()


def list_transactions(year=None, month=None, category=None):
    conn = get_conn()
    q = "SELECT * FROM transactions WHERE 1=1"
    params = []
    if year and month:
        q += " AND substr(date,1,7)=?"
        params.append(f"{int(year):04d}-{int(month):02d}")
    if category:
        q += " AND category=?"
        params.append(category)
    q += " ORDER BY date DESC, id DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def summarize_transactions(year=None, month=None):
    rows = list_transactions(year, month)
    cat_group_map = all_category_group_map()
    summary = {
        "income": {"UZS": 0.0, "USD": 0.0},
        "expense": {"UZS": 0.0, "USD": 0.0},
        "unpaid_expense": {"UZS": 0.0, "USD": 0.0},
        "unpaid_income": {"UZS": 0.0, "USD": 0.0},
        # "Sotilgan xizmat/tovar"dan haqiqiy realizatsiya daromadi — Forma 2'ning
        # 010-qatoriga (Exely tushumi ustiga) qo'shiladi. Oddiy qo'lda kiritilgan
        # "daromad" turidagi tranzaksiyalar bu yerga kirmaydi (ular operatsion
        # bo'lmasligi mumkin), faqat xizmat/bar SOTUVI kiradi.
        "revenue_extra": {"UZS": 0.0, "USD": 0.0},
        "by_category": {},
        "by_group": {g: {"UZS": 0.0, "USD": 0.0} for g, _ in FORMA2_GROUPS},
    }
    for r in rows:
        bucket = summary[r["type"]]
        bucket[r["currency"]] += r["amount"]
        if r["status"] == "unpaid":
            key = "unpaid_expense" if r["type"] == "expense" else "unpaid_income"
            summary[key][r["currency"]] += r["amount"]
        cat = summary["by_category"].setdefault(r["category"], {"UZS": 0.0, "USD": 0.0})
        sign = 1 if r["type"] == "income" else -1
        cat[r["currency"]] += sign * r["amount"]
        if r["type"] == "expense":
            group = cat_group_map.get(r["category"], "boshqa_operatsion")
            summary["by_group"].setdefault(group, {"UZS": 0.0, "USD": 0.0})
            summary["by_group"][group][r["currency"]] += r["amount"]
        elif r["category"] == SERVICE_REVENUE_CATEGORY:
            summary["revenue_extra"][r["currency"]] += r["amount"]

    # Bar/mini-bar: tovar sotib olish (kirim) — tannarx sifatida, mehmonlarga
    # sotish (chiqim) — realizatsiya daromadi sifatida Forma 2'ga qo'shiladi.
    for bt in list_bar_transactions(year, month):
        if bt["ttype"] == "sale":
            summary["income"][bt["currency"]] += bt["amount"]
            summary["revenue_extra"][bt["currency"]] += bt["amount"]
        else:
            summary["expense"][bt["currency"]] += bt["amount"]
            summary["by_group"]["tannarx"][bt["currency"]] += bt["amount"]
    return summary


def category_breakdown(year, month, group_key):
    """Berilgan Forma 2 xarajat guruhi (masalan 'tannarx', 'mamuriy') qanday
    turkumlardan tarkib topganini ko'rsatadi — hisobotda qatorni bosganda
    tafsilotini chiqarish uchun."""
    cat_group_map = all_category_group_map()
    totals = {}
    for r in list_transactions(year, month):
        if r["type"] != "expense":
            continue
        group = cat_group_map.get(r["category"], "boshqa_operatsion")
        if group != group_key:
            continue
        t = totals.setdefault(r["category"], {"UZS": 0.0, "USD": 0.0})
        t[r["currency"]] += r["amount"]
    if group_key == "tannarx":
        for bt in list_bar_transactions(year, month):
            if bt["ttype"] != "sale":
                t = totals.setdefault("Bar mahsulotlari xaridi (tannarx)", {"UZS": 0.0, "USD": 0.0})
                t[bt["currency"]] += bt["amount"]
    rows = [{"category": k, "uzs": v["UZS"], "usd": v["USD"]} for k, v in totals.items()]
    rows.sort(key=lambda r: -(r["uzs"] + r["usd"]))
    return rows


def summarize_transactions_upto(upto_date=None):
    """`summarize_transactions`ga o'xshaydi, lekin bitta oy emas — berilgan
    sanagacha JAMLANGAN (kumulyativ) natijani qaytaradi. Forma 1'dagi
    "Taqsimlanmagan foyda" (jamg'arilgan sof foyda) qatorini hisoblash
    uchun kerak — balans muayyan SANAGA nisbatan JAMI holatni ko'rsatishi
    kerak, faqat tanlangan oy emas."""
    conn = get_conn()
    q = "SELECT * FROM transactions"
    params = []
    if upto_date:
        q += " WHERE date<=?"
        params.append(upto_date)
    rows = [dict(r) for r in conn.execute(q, params).fetchall()]
    conn.close()
    cat_group_map = all_category_group_map()

    summary = {
        "income": {"UZS": 0.0, "USD": 0.0},
        "expense": {"UZS": 0.0, "USD": 0.0},
        "unpaid_expense": {"UZS": 0.0, "USD": 0.0},
        "unpaid_income": {"UZS": 0.0, "USD": 0.0},
        "revenue_extra": {"UZS": 0.0, "USD": 0.0},
        "by_category": {},
        "by_group": {g: {"UZS": 0.0, "USD": 0.0} for g, _ in FORMA2_GROUPS},
    }
    for r in rows:
        bucket = summary[r["type"]]
        bucket[r["currency"]] += r["amount"]
        if r["status"] == "unpaid":
            key = "unpaid_expense" if r["type"] == "expense" else "unpaid_income"
            summary[key][r["currency"]] += r["amount"]
        cat = summary["by_category"].setdefault(r["category"], {"UZS": 0.0, "USD": 0.0})
        sign = 1 if r["type"] == "income" else -1
        cat[r["currency"]] += sign * r["amount"]
        if r["type"] == "expense":
            group = cat_group_map.get(r["category"], "boshqa_operatsion")
            summary["by_group"].setdefault(group, {"UZS": 0.0, "USD": 0.0})
            summary["by_group"][group][r["currency"]] += r["amount"]
        elif r["category"] == SERVICE_REVENUE_CATEGORY:
            summary["revenue_extra"][r["currency"]] += r["amount"]

    conn = get_conn()
    q3 = "SELECT * FROM bar_transactions"
    params3 = []
    if upto_date:
        q3 += " WHERE date<=?"
        params3.append(upto_date)
    bar_txs = [dict(r) for r in conn.execute(q3, params3).fetchall()]
    conn.close()

    for bt in bar_txs:
        if bt["ttype"] == "sale":
            summary["income"][bt["currency"]] += bt["amount"]
            summary["revenue_extra"][bt["currency"]] += bt["amount"]
        else:
            summary["expense"][bt["currency"]] += bt["amount"]
            summary["by_group"]["tannarx"][bt["currency"]] += bt["amount"]
    return summary


# ---- Bronlar keshi (o'sib boruvchi sinxronizatsiya uchun) ----
# Har bir bron xom JSON holida saqlanadi. Har safar yangilashda Exely'ning
# bron RO'YXATI (arzon, sahifalab) bilan solishtirilib, faqat haqiqatan ham
# yangi yoki o'zgargan bronlarning TO'LIQ tafsiloti (qimmat) qayta so'raladi.
# `modified_at` ustuni ATAYLAB har doim RO'YXAT javobidagi modifiedDateTime
# bilan to'ldiriladi (tafsilot javobidagi emas) — chunki Exely'da bu ikkisi
# bir xil bron uchun ~1 soniyaga farq qilishi aniqlandi; agar ikki xil
# manbadan olingan qiymatlar solishtirilsa, deyarli har bir bron "o'zgargan"
# deb noto'g'ri aniqlanadi.

def upsert_bookings(raw_bookings, modified_map=None):
    if not raw_bookings:
        return
    modified_map = modified_map or {}
    conn = get_conn()
    conn.executemany(
        "INSERT INTO bookings_cache (number, raw_json, modified_at, updated_at) VALUES (?,?,?,datetime('now'))"
        " ON CONFLICT(number) DO UPDATE SET raw_json=excluded.raw_json, modified_at=excluded.modified_at,"
        " updated_at=excluded.updated_at",
        [
            (b["number"], json.dumps(b, ensure_ascii=False), modified_map.get(b["number"], b.get("modifiedDateTime")))
            for b in raw_bookings if b.get("number")
        ],
    )
    conn.commit()
    conn.close()


def load_all_bookings():
    conn = get_conn()
    rows = conn.execute("SELECT raw_json FROM bookings_cache").fetchall()
    conn.close()
    return [json.loads(r["raw_json"]) for r in rows]


def get_cached_modified_map():
    """{bron_raqami: modified_at} — Exely bron ro'yxatidan kelgan joriy
    modifiedDateTime bilan solishtirib, faqat o'zgargan/yangi bronlarni
    aniqlash uchun (server tomonda modifiedFrom filtri ishlamagani sababli
    bu taqqoslash mijoz tomonida qilinadi)."""
    conn = get_conn()
    rows = conn.execute("SELECT number, modified_at FROM bookings_cache").fetchall()
    conn.close()
    return {r["number"]: r["modified_at"] for r in rows}


# ---- Дт/Кт (kontragentlar bilan hisob-kitob) ----
# "Xarajatlar" (transactions) sahifasidagi kontragent ko'rsatilgan yozuvlar
# manba hisoblanadi: xarid/sotib olingan
# xizmat = Kt (biz qarzdormiz), daromad/sotilgan xizmat = Dt (bizga
# qarzdor). Har bir manba yozuviga nisbatan alohida "to'lov" (payments)
# qo'shiladi — qisman to'lovlar ham qo'llab-quvvatlanadi. Qoldiq har doim
# manba summasi - shu manbaga tegishli barcha to'lovlar yig'indisi sifatida
# HISOBLAB chiqariladi (alohida saqlanmaydi), shuning uchun har doim aniq.

def _debt_entries():
    conn = get_conn()
    rows = []
    service_tx_ids = {
        r["transaction_id"] for r in conn.execute(
            "SELECT transaction_id FROM services WHERE transaction_id IS NOT NULL"
        ).fetchall()
    }
    for r in conn.execute(
        "SELECT * FROM transactions WHERE counterparty IS NOT NULL AND trim(counterparty)<>''"
    ).fetchall():
        r = dict(r)
        polarity = "dt" if r["type"] == "income" else "kt"
        rows.append({
            "source_type": "transaction", "source_id": r["id"], "counterparty": r["counterparty"],
            "date": r["date"], "amount": r["amount"], "currency": r["currency"], "polarity": polarity,
            "origin": "service" if r["id"] in service_tx_ids else "transaction",
        })
    for r in conn.execute(
        "SELECT * FROM bar_transactions WHERE ttype='restock' AND counterparty IS NOT NULL AND trim(counterparty)<>''"
    ).fetchall():
        r = dict(r)
        rows.append({
            "source_type": "bar_transaction", "source_id": r["id"], "counterparty": r["counterparty"],
            "date": r["date"], "amount": r["amount"], "currency": r["currency"], "polarity": "kt",
            "origin": "bar_transaction",
        })
    # Kassa/Bank (cash_transactions): kontragenti belgilangan har bir pul
    # harakati ham Дт/Кт'da aks etadi — xizmat ko'rsatilgani (chiqim, Kt)
    # yoki mablag' olingani (kirim, Dt) bo'yicha, xuddi accrual tomon kabi.
    for r in conn.execute(
        "SELECT * FROM cash_transactions WHERE counterparty IS NOT NULL AND trim(counterparty)<>''"
        " AND transaction_id IS NULL"
    ).fetchall():
        r = dict(r)
        polarity = "dt" if r["type"] == "income" else "kt"
        rows.append({
            "source_type": "cash_transaction", "source_id": r["id"], "counterparty": r["counterparty"],
            "date": r["date"], "amount": r["amount"], "currency": r["currency"], "polarity": polarity,
            "origin": "cash_transaction",
        })
    conn.close()
    return rows


def _movements_by_counterparty(currency):
    """Har bir kontragent uchun (qutb, sana, summa) harakatlar ro'yxati:
    manba yozuvining o'zi + unga to'langan har bir to'lov (to'lov har doim
    manbaning QARAMA-QARSHI qutbida hisoblanadi — masalan Kt qarzni to'lash
    Dt harakati sifatida yoziladi, standart buxgalteriya amaliyoti kabi)."""
    entries = [e for e in _debt_entries() if e["currency"] == currency]
    conn = get_conn()
    pay_rows = conn.execute("SELECT * FROM payments WHERE currency=?", (currency,)).fetchall()
    conn.close()
    payments_by_source = {}
    for r in pay_rows:
        key = (r["source_type"], r["source_id"])
        payments_by_source.setdefault(key, []).append(dict(r))

    by_cp = {}
    for e in entries:
        by_cp.setdefault(e["counterparty"], []).append((e["polarity"], e["date"], e["amount"]))
        opposite = "kt" if e["polarity"] == "dt" else "dt"
        for p in payments_by_source.get((e["source_type"], e["source_id"]), []):
            by_cp[e["counterparty"]].append((opposite, p["date"], p["amount"]))
    return by_cp


def _balance(items, upto=None):
    dt = sum(a for pol, d, a in items if pol == "dt" and (upto is None or d <= upto))
    kt = sum(a for pol, d, a in items if pol == "kt" and (upto is None or d <= upto))
    return dt, kt


def counterparty_ledger(year=None, month=None, currency="UZS"):
    """Har bir kontragent bo'yicha: davr boshi qoldig'i, davr ichidagi
    Dt/Kt aylanma, davr oxiri qoldig'i (skrinshotdagi "Ведомости Дт-Кт"
    tuzilmasiga mos)."""
    by_cp = _movements_by_counterparty(currency)
    if year and month:
        y, m = int(year), int(month)
        period_start = f"{y:04d}-{m:02d}-01"
        period_end = month_end_date(f"{y:04d}-{m:02d}")
        prev_day = (date(y, m, 1) - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        period_start = period_end = prev_day = None

    result = []
    for cp, items in sorted(by_cp.items()):
        open_dt, open_kt = _balance(items, prev_day) if prev_day else (0.0, 0.0)
        open_net = open_dt - open_kt
        turn_dt = sum(
            a for pol, d, a in items
            if pol == "dt" and (period_start is None or d >= period_start) and (period_end is None or d <= period_end)
        )
        turn_kt = sum(
            a for pol, d, a in items
            if pol == "kt" and (period_start is None or d >= period_start) and (period_end is None or d <= period_end)
        )
        close_dt, close_kt = _balance(items, period_end)
        close_net = close_dt - close_kt
        if not any([open_net, turn_dt, turn_kt, close_net]):
            continue
        result.append({
            "counterparty": cp,
            "open_dt": max(open_net, 0.0), "open_kt": max(-open_net, 0.0),
            "turn_dt": turn_dt, "turn_kt": turn_kt,
            "close_dt": max(close_net, 0.0), "close_kt": max(-close_net, 0.0),
        })
    return result


def outstanding_balance(currency, upto_date=None):
    """Barcha kontragentlar bo'yicha JAMI debitorlik (Dt) va kreditorlik
    (Kt) — har bir kontragent ALOHIDA svernutoy holda (ijobiy/manfiy)
    hisoblanadi, keyin ikkalasi yig'iladi (standart amaliyot: bir
    kontragentning Dt qoldig'i boshqasining Kt qoldig'i bilan
    "tenglashtirilmaydi"). Forma 1'ga beriladi."""
    by_cp = _movements_by_counterparty(currency)
    dt_total = kt_total = 0.0
    for items in by_cp.values():
        dt, kt = _balance(items, upto_date)
        net = dt - kt
        if net > 0:
            dt_total += net
        else:
            kt_total += -net
    return dt_total, kt_total


def counterparty_entries(counterparty, currency=None):
    """Bitta kontragentga tegishli barcha manba yozuvlari, har biri uchun
    to'langan va qolgan summa bilan — to'lov qo'shish sahifasi uchun."""
    entries = [e for e in _debt_entries() if e["counterparty"] == counterparty]
    if currency:
        entries = [e for e in entries if e["currency"] == currency]
    conn = get_conn()
    pay_rows = conn.execute("SELECT * FROM payments").fetchall()
    conn.close()
    paid_map = {}
    for r in pay_rows:
        key = (r["source_type"], r["source_id"])
        paid_map[key] = paid_map.get(key, 0.0) + r["amount"]
    result = []
    for e in entries:
        paid = paid_map.get((e["source_type"], e["source_id"]), 0.0)
        e = dict(e)
        e["paid"] = paid
        e["remaining"] = round(e["amount"] - paid, 2)
        result.append(e)
    result.sort(key=lambda x: x["date"], reverse=True)
    return result


def list_all_counterparties():
    return sorted({e["counterparty"] for e in _debt_entries()})


def add_payment(source_type, source_id, date, amount, currency, note=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO payments (source_type, source_id, date, amount, currency, note) VALUES (?,?,?,?,?,?)",
        (source_type, source_id, date, amount, currency, note),
    )
    conn.commit()
    conn.close()


def delete_payment(payment_id):
    conn = get_conn()
    conn.execute("DELETE FROM payments WHERE id=?", (payment_id,))
    conn.commit()
    conn.close()


def get_payment(payment_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM payments WHERE id=?", (payment_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_payments_for(source_type, source_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM payments WHERE source_type=? AND source_id=? ORDER BY date DESC, id DESC",
        (source_type, source_id),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---- Asosiy vositalar (fixed assets) — Forma 1 aktivi ----

def add_fixed_asset(name, value, currency, purchase_date):
    conn = get_conn()
    conn.execute(
        "INSERT INTO fixed_assets (name, value, currency, purchase_date) VALUES (?,?,?,?)",
        (name, value, currency, purchase_date),
    )
    conn.commit()
    conn.close()


def delete_fixed_asset(asset_id):
    conn = get_conn()
    conn.execute("DELETE FROM fixed_assets WHERE id=?", (asset_id,))
    conn.commit()
    conn.close()


def list_fixed_assets():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM fixed_assets ORDER BY purchase_date DESC, id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def total_fixed_assets_value(currency, upto_date=None):
    conn = get_conn()
    q = "SELECT COALESCE(SUM(value),0) v FROM fixed_assets WHERE currency=?"
    params = [currency]
    if upto_date:
        q += " AND purchase_date<=?"
        params.append(upto_date)
    row = conn.execute(q, params).fetchone()
    conn.close()
    return row["v"]


# ---- Bar / mini-bar (mehmonxona xonasidagi tovar zaxirasi: sotib olinadi,
#      ustiga foyda qo'yib mehmonlarga sotiladi — masalan kofe, suv, ichimlik) ----
# Har mahsulot uchun bitta tan narx va bitta sotish narxi (doimiy katalog)
# saqlanadi; sotuv/kirim vaqtida narx katalogdan olinadi. Har kirim/sotuv
# zaxirani (stock_qty) yangilaydi va Kassa/Bank'ga avtomatik pul harakati
# sifatida yoziladi (kassa balansi va Forma 1/3 to'g'ri bo'lishi uchun).

def add_bar_product(name, unit, cost_price, sale_price, currency):
    conn = get_conn()
    conn.execute(
        "INSERT INTO bar_products (name, unit, cost_price, sale_price, currency) VALUES (?,?,?,?,?)",
        (name, unit, cost_price, sale_price, currency),
    )
    conn.commit()
    conn.close()


def update_bar_product(product_id, name, unit, cost_price, sale_price, currency):
    conn = get_conn()
    conn.execute(
        "UPDATE bar_products SET name=?, unit=?, cost_price=?, sale_price=?, currency=? WHERE id=?",
        (name, unit, cost_price, sale_price, currency, product_id),
    )
    conn.commit()
    conn.close()


def delete_bar_product(product_id):
    conn = get_conn()
    used = conn.execute(
        "SELECT COUNT(*) c FROM bar_transactions WHERE product_id=?", (product_id,)
    ).fetchone()["c"]
    if used:
        conn.close()
        raise ValueError("product_in_use")
    conn.execute("DELETE FROM bar_products WHERE id=?", (product_id,))
    conn.commit()
    conn.close()


def get_bar_product(product_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM bar_products WHERE id=?", (product_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_bar_products():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM bar_products ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def bar_stock_value():
    conn = get_conn()
    rows = conn.execute("SELECT stock_qty, cost_price, currency FROM bar_products").fetchall()
    conn.close()
    value = {"UZS": 0.0, "USD": 0.0}
    for r in rows:
        value[r["currency"]] += r["stock_qty"] * r["cost_price"]
    return value


def add_bar_transaction(date, product_id, ttype, qty, source, counterparty="", description="", status="paid"):
    """`status='unpaid'` faqat 'restock' (kirim) uchun mantiqiy — tovar
    darhol omborga qo'shiladi, lekin Kassa/Bank'dan pul DARHOL chiqmaydi;
    o'rniga yetkazib beruvchiga qarz sifatida Дт/Кт'da ko'rinadi va
    keyinroq (qisman yoki to'liq) to'lov qo'shish mumkin bo'ladi."""
    product = get_bar_product(product_id)
    if not product:
        raise ValueError("product_not_found")
    qty = float(qty)
    if qty <= 0:
        raise ValueError("invalid_qty")

    if ttype == "sale":
        if product["stock_qty"] + 1e-9 < qty:
            raise ValueError("insufficient_stock")
        unit_price = product["sale_price"]
        new_stock = product["stock_qty"] - qty
        cash_ttype, cash_category = "income", BAR_SALE_CATEGORY
    elif ttype == "restock":
        unit_price = product["cost_price"]
        new_stock = product["stock_qty"] + qty
        cash_ttype, cash_category = "expense", BAR_RESTOCK_CATEGORY
    else:
        raise ValueError("invalid_ttype")

    amount = round(qty * unit_price, 2)
    currency = product["currency"]
    note = description or f"{product['name']} x{qty:g}"

    conn = get_conn()
    cash_id = None
    if status == "paid":
        cur = conn.execute(
            "INSERT INTO cash_transactions (date, source, type, section, category, counterparty, description, amount, currency)"
            " VALUES (?,?,?,'operatsion',?,?,?,?,?)",
            (date, source, cash_ttype, cash_category, counterparty, note, amount, currency),
        )
        cash_id = cur.lastrowid
    bt_cur = conn.execute(
        "INSERT INTO bar_transactions (date, product_id, product_name, ttype, qty, unit_price, amount, currency,"
        " source, counterparty, description, cash_transaction_id, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (date, product_id, product["name"], ttype, qty, unit_price, amount, currency,
         source, counterparty, description, cash_id, status),
    )
    if status == "paid":
        conn.execute(
            "INSERT INTO payments (source_type, source_id, date, amount, currency, note) VALUES ('bar_transaction',?,?,?,?,?)",
            (bt_cur.lastrowid, date, amount, currency, ""),
        )
    conn.execute("UPDATE bar_products SET stock_qty=? WHERE id=?", (new_stock, product_id))
    conn.commit()
    conn.close()


def get_bar_transaction(bt_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM bar_transactions WHERE id=?", (bt_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_bar_transaction(bt_id, date, qty, source, counterparty, description):
    """Mahsulot/turi (sotish/kirim) va holati tahrirlanmaydi — ular ombor
    va to'lov mantiqini belgilaydi; sana/miqdor/hisob/kontragent/izoh
    tahrirlanadi. Miqdor o'zgarsa ombor qoldig'i va (bog'langan bo'lsa)
    Kassa/Bank yozuvi ham sinxron yangilanadi."""
    row = get_bar_transaction(bt_id)
    if not row:
        return
    product = get_bar_product(row["product_id"])
    qty = float(qty)
    if qty <= 0:
        raise ValueError("invalid_qty")

    reversed_stock = product["stock_qty"] + (row["qty"] if row["ttype"] == "sale" else -row["qty"])
    if row["ttype"] == "sale":
        if reversed_stock + 1e-9 < qty:
            raise ValueError("insufficient_stock")
        new_stock = reversed_stock - qty
    else:
        new_stock = reversed_stock + qty

    amount = round(qty * row["unit_price"], 2)

    conn = get_conn()
    conn.execute(
        "UPDATE bar_transactions SET date=?, qty=?, amount=?, source=?, counterparty=?, description=? WHERE id=?",
        (date, qty, amount, source, counterparty, description, bt_id),
    )
    conn.execute("UPDATE bar_products SET stock_qty=? WHERE id=?", (new_stock, row["product_id"]))
    if row["cash_transaction_id"]:
        conn.execute(
            "UPDATE cash_transactions SET date=?, amount=?, source=?, counterparty=?, description=? WHERE id=?",
            (date, amount, source, counterparty, description, row["cash_transaction_id"]),
        )
    conn.execute(
        "UPDATE payments SET date=?, amount=? WHERE source_type='bar_transaction' AND source_id=?",
        (date, amount, bt_id),
    )
    conn.commit()
    conn.close()


def delete_bar_transaction(bt_id):
    row = get_bar_transaction(bt_id)
    if not row:
        return
    conn = get_conn()
    reversed_qty = row["qty"] if row["ttype"] == "sale" else -row["qty"]
    conn.execute(
        "UPDATE bar_products SET stock_qty = stock_qty + ? WHERE id=?", (reversed_qty, row["product_id"])
    )
    if row["cash_transaction_id"]:
        conn.execute("DELETE FROM cash_transactions WHERE id=?", (row["cash_transaction_id"],))
    conn.execute("DELETE FROM payments WHERE source_type='bar_transaction' AND source_id=?", (bt_id,))
    conn.execute("DELETE FROM bar_transactions WHERE id=?", (bt_id,))
    conn.commit()
    conn.close()


def list_bar_transactions(year=None, month=None, product_id=None, ttype=None):
    conn = get_conn()
    q = "SELECT * FROM bar_transactions WHERE 1=1"
    params = []
    if year and month:
        q += " AND substr(date,1,7)=?"
        params.append(f"{int(year):04d}-{int(month):02d}")
    if product_id:
        q += " AND product_id=?"
        params.append(product_id)
    if ttype:
        q += " AND ttype=?"
        params.append(ttype)
    q += " ORDER BY date DESC, id DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def bar_product_report(year=None, month=None):
    """Hisobotlar sahifasidagi "Bar" tabi uchun: har bir mahsulot bo'yicha
    davr ichidagi sotuv/xarid va joriy (bugungi) ombor qoldig'i."""
    products = {p["id"]: p for p in list_bar_products()}
    agg = {}
    for bt in list_bar_transactions(year, month):
        b = agg.setdefault(bt["product_id"], {
            "name": bt["product_name"],
            "sold_qty": 0.0, "sold": {"UZS": 0.0, "USD": 0.0},
            "purchased_qty": 0.0, "purchased": {"UZS": 0.0, "USD": 0.0},
        })
        if bt["ttype"] == "sale":
            b["sold_qty"] += bt["qty"]
            b["sold"][bt["currency"]] += bt["amount"]
        else:
            b["purchased_qty"] += bt["qty"]
            b["purchased"][bt["currency"]] += bt["amount"]
    rows = []
    for pid, b in agg.items():
        p = products.get(pid)
        rows.append({
            "name": b["name"], "unit": p["unit"] if p else "",
            "sold_qty": b["sold_qty"], "sold": b["sold"],
            "purchased_qty": b["purchased_qty"], "purchased": b["purchased"],
            "stock_qty": p["stock_qty"] if p else 0.0,
        })
    rows.sort(key=lambda r: r["sold"]["UZS"] + r["sold"]["USD"], reverse=True)
    return rows


def summarize_bar_segment(year=None, month=None):
    """Bar/mini-bar segmentining o'z ichidagi yalpi foydasi — Forma 2'ning
    "Segment bo'yicha foyda" kartasi uchun. Faqat savdo (daromad) va tovar
    tannarxi (xarid) hisobga olinadi; boshqa umumiy xarajatlar (ijara, ish
    haqi va h.k.) Bar segmentiga taqsimlanmaydi — ular to'liq Hostel
    segmentida qoladi."""
    revenue = {"UZS": 0.0, "USD": 0.0}
    cost = {"UZS": 0.0, "USD": 0.0}
    for bt in list_bar_transactions(year, month):
        if bt["ttype"] == "sale":
            revenue[bt["currency"]] += bt["amount"]
        else:
            cost[bt["currency"]] += bt["amount"]
    profit = {cur: revenue[cur] - cost[cur] for cur in ("UZS", "USD")}
    return {"revenue": revenue, "cost": cost, "profit": profit}


# ---- Sozlamalar (kalit-qiymat) ----

def get_setting(key, default=None):
    conn = get_conn()
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key, value):
    conn = get_conn()
    conn.execute(
        "INSERT INTO app_settings (key, value) VALUES (?,?)"
        " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value)),
    )
    conn.commit()
    conn.close()


# ---- Valyuta kursi (KUNLIK — istalgan sanaga qo'yiladi, keyingi yozuv
#      kiritilmaguncha o'sha kurs "amal qiladi" deb hisoblanadi) ----

def set_exchange_rate(date, rate, currency="USD"):
    """`currency` — 'USD' (standart) yoki 'EUR'. Bir xil sana uchun ikkala
    valyuta kursi alohida-alohida saqlanadi (bir qatorda, ikki ustunda) —
    biri yangilanganda ikkinchisi tegilmay qoladi."""
    conn = get_conn()
    existing = conn.execute(
        "SELECT uzs_per_usd, uzs_per_eur FROM exchange_rates WHERE date=?", (date,)
    ).fetchone()
    usd_val = existing["uzs_per_usd"] if existing else 0.0
    eur_val = existing["uzs_per_eur"] if existing else None
    if currency == "EUR":
        eur_val = rate
    else:
        usd_val = rate
    conn.execute(
        "INSERT INTO exchange_rates (date, uzs_per_usd, uzs_per_eur, updated_at) VALUES (?,?,?,datetime('now'))"
        " ON CONFLICT(date) DO UPDATE SET uzs_per_usd=excluded.uzs_per_usd, uzs_per_eur=excluded.uzs_per_eur,"
        " updated_at=excluded.updated_at",
        (date, usd_val, eur_val),
    )
    conn.commit()
    conn.close()


def delete_exchange_rate(date, currency="USD"):
    """Faqat berilgan valyuta ustunini bo'shatadi (0/NULL) — sananing
    o'zi va ikkinchi valyuta kursi saqlanib qoladi."""
    conn = get_conn()
    if currency == "EUR":
        conn.execute("UPDATE exchange_rates SET uzs_per_eur=NULL WHERE date=?", (date,))
    else:
        conn.execute("UPDATE exchange_rates SET uzs_per_usd=0 WHERE date=?", (date,))
    conn.execute(
        "DELETE FROM exchange_rates WHERE date=? AND (uzs_per_usd IS NULL OR uzs_per_usd=0) AND uzs_per_eur IS NULL",
        (date,),
    )
    conn.commit()
    conn.close()


def get_exchange_rate_on(upto_date=None, currency="USD"):
    """Berilgan sanada AMALDA bo'lgan kurs — shu sanagacha (yoki teng)
    kiritilgan ENG SO'NGGI kurs. `upto_date=None` bo'lsa — umuman eng
    so'nggi (bugungi) kurs qaytariladi."""
    col = "uzs_per_eur" if currency == "EUR" else "uzs_per_usd"
    conn = get_conn()
    if upto_date:
        row = conn.execute(
            f"SELECT {col} v FROM exchange_rates WHERE date<=? AND {col} IS NOT NULL AND {col}>0 ORDER BY date DESC LIMIT 1",
            (upto_date,),
        ).fetchone()
    else:
        row = conn.execute(
            f"SELECT {col} v FROM exchange_rates WHERE {col} IS NOT NULL AND {col}>0 ORDER BY date DESC LIMIT 1"
        ).fetchone()
    conn.close()
    return row["v"] if row else None


def fetch_cbu_rate(date_str, currency="USD"):
    """O'zbekiston Markaziy banki (cbu.uz) rasmiy saytidan berilgan sana
    uchun USD yoki EUR / UZS kursini oladi. Tarmoq xatosida yoki kurs
    topilmasa ValueError ko'taradi."""
    import requests
    url = f"https://cbu.uz/uz/arkhiv-kursov-valyut/json/{currency}/{date_str}/"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        raise ValueError("cbu_no_data")
    return float(data[0]["Rate"])


def list_exchange_rates():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM exchange_rates ORDER BY date DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---- Kassa / Bank (pul mablag'lari harakati — Forma 1/3 uchun asos) ----

def add_cash_transaction(date, source, ttype, section, category, counterparty, description, amount, currency,
                          note_label="", forma2_category=None):
    """`forma2_category` — IXTIYORIY: berilsa, shu kassa/bank harakati
    UCHUN QO'SHIMCHA ravishda `transactions` (accrual, Forma 2)ga ham
    mos xarajat/daromad yozuvi avtomatik yaratiladi (Bar/Xizmatlar
    ko'prigi bilan bir xil naqsh) — berilmasa, harakat FAQAT Cash Flow
    (Kassa/Bank, Forma 1/3) tomonida qoladi."""
    tx_id = None
    if forma2_category:
        f2_ttype = "expense" if forma2_category in all_category_group_map() else "income"
        tx_id = add_transaction(
            date=date, ttype=f2_ttype, category=forma2_category, counterparty=counterparty,
            description=description, amount=amount, currency=currency, status="paid",
        )

    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO cash_transactions (date, source, type, section, category, counterparty, description, amount, currency, note_label, transaction_id)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (date, source, ttype, section, category, counterparty, description, amount, currency, note_label or None, tx_id),
    )
    if counterparty and counterparty.strip() and not tx_id:
        # Kassa/bank harakati sana-o'zida yakunlangan (kechiktirilgan to'lov
        # tushunchasi yo'q), shuning uchun Дт/Кт'da darhol o'z-o'zini
        # to'lagan deb hisoblanadi (transactions/bar_transaction'dagi
        # status='paid' bilan bir xil naqsh). Agar `tx_id` mavjud bo'lsa
        # (Forma 2'ga ko'prik yaratilgan bo'lsa) — kontragent Дт/Кт'da
        # ALLAQACHON o'sha `transactions` yozuvi orqali ko'rinadi, shuning
        # uchun bu yerda IKKINCHI marta (ikkilanib) qo'shilmaydi.
        conn.execute(
            "INSERT INTO payments (source_type, source_id, date, amount, currency, note) VALUES ('cash_transaction',?,?,?,?,?)",
            (cur.lastrowid, date, amount, currency, ""),
        )
    conn.commit()
    cash_id = cur.lastrowid
    conn.close()
    return cash_id


def delete_cash_transaction(cash_id):
    conn = get_conn()
    row = conn.execute("SELECT transaction_id FROM cash_transactions WHERE id=?", (cash_id,)).fetchone()
    conn.close()
    if row and row["transaction_id"]:
        delete_transaction(row["transaction_id"])
    conn = get_conn()
    conn.execute("DELETE FROM payments WHERE source_type='cash_transaction' AND source_id=?", (cash_id,))
    conn.execute("DELETE FROM cash_transactions WHERE id=?", (cash_id,))
    conn.commit()
    conn.close()


def get_cash_transaction(cash_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM cash_transactions WHERE id=?", (cash_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_cash_transaction(cash_id, date, source, counterparty, description, amount, currency, note_label=""):
    """Faqat "strukturaviy bo'lmagan" maydonlar tahrirlanadi (sana, hisob,
    summa, valyuta, kontragent, izoh) — turi/statya/Forma2 ko'prigi
    o'zgarmaydi, chunki ular yozuv yaratilgandagi buxgalteriya bog'lanishini
    belgilaydi. Agar yozuv Forma2'ga bog'langan bo'lsa (transaction_id), mos
    `transactions` yozuvi va uning to'lovi ham sinxron yangilanadi."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM cash_transactions WHERE id=?", (cash_id,)).fetchone()
    if not row:
        conn.close()
        return
    conn.execute(
        "UPDATE cash_transactions SET date=?, source=?, counterparty=?, description=?, amount=?, currency=?,"
        " note_label=? WHERE id=?",
        (date, source, counterparty, description, amount, currency, note_label or None, cash_id),
    )
    if row["transaction_id"]:
        conn.execute(
            "UPDATE transactions SET date=?, counterparty=?, description=?, amount=?, currency=? WHERE id=?",
            (date, counterparty, description, amount, currency, row["transaction_id"]),
        )
        conn.execute(
            "UPDATE payments SET date=?, amount=?, currency=? WHERE source_type='transaction' AND source_id=?",
            (date, amount, currency, row["transaction_id"]),
        )
        # Agar bu transaction aslida Xizmatlar (services) yozuvidan kelgan
        # bo'lsa, `services` jadvalidagi QQS breakdown ham sinxron
        # qayta hisoblanadi — aks holda Xizmatlar sahifasi eskirgan
        # summani ko'rsatib qoladi.
        svc = conn.execute(
            "SELECT id FROM services WHERE transaction_id=?", (row["transaction_id"],)
        ).fetchone()
        if svc:
            amount_no_vat = round(amount / (1 + VAT_RATE), 2)
            vat_amount = round(amount - amount_no_vat, 2)
            conn.execute(
                "UPDATE services SET date=?, counterparty=?, amount_no_vat=?, vat_amount=?, total=?, currency=?,"
                " description=? WHERE id=?",
                (date, counterparty, amount_no_vat, vat_amount, amount, currency, description, svc["id"]),
            )
    else:
        conn.execute(
            "UPDATE payments SET date=?, amount=?, currency=? WHERE source_type='cash_transaction' AND source_id=?",
            (date, amount, currency, cash_id),
        )
    conn.commit()
    conn.close()


def _cash_transactions_where(year, month, source, ttype, category, counterparty, search=None):
    q = " WHERE 1=1"
    params = []
    if year and month:
        q += " AND substr(date,1,7)=?"
        params.append(f"{int(year):04d}-{int(month):02d}")
    if source:
        q += " AND source=?"
        params.append(source)
    if ttype:
        q += " AND type=?"
        params.append(ttype)
    if category:
        q += " AND category=?"
        params.append(category)
    if counterparty:
        q += " AND counterparty=?"
        params.append(counterparty)
    if search:
        like = f"%{search}%"
        q += (" AND (date LIKE ? OR category LIKE ? OR note_label LIKE ?"
              " OR counterparty LIKE ? OR description LIKE ? OR CAST(amount AS TEXT) LIKE ?)")
        params += [like, like, like, like, like, like]
    return q, params


def list_cash_transactions(year=None, month=None, source=None, ttype=None, category=None, counterparty=None,
                            search=None, limit=None, offset=0):
    conn = get_conn()
    where, params = _cash_transactions_where(year, month, source, ttype, category, counterparty, search)
    q = "SELECT * FROM cash_transactions" + where + " ORDER BY date DESC, id DESC"
    if limit:
        q += " LIMIT ? OFFSET ?"
        params = params + [limit, offset]
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_cash_transactions(year=None, month=None, source=None, ttype=None, category=None, counterparty=None, search=None):
    conn = get_conn()
    where, params = _cash_transactions_where(year, month, source, ttype, category, counterparty, search)
    row = conn.execute("SELECT COUNT(*) c FROM cash_transactions" + where, params).fetchone()
    conn.close()
    return row["c"]


def list_cash_counterparties():
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT counterparty FROM cash_transactions WHERE counterparty IS NOT NULL AND trim(counterparty)<>'' ORDER BY counterparty"
    ).fetchall()
    conn.close()
    return [r["counterparty"] for r in rows]


def get_cash_opening(currency, source=None):
    """Boshlang'ich qoldiq — Kassa va Bank uchun ALOHIDA saqlanadi
    (`cash_opening_kassa_uzs`, `cash_opening_bank_usd` va h.k.). `source`
    berilmasa (masalan Forma 3'ning umumiy ochilish qoldig'i uchun) —
    ikkalasining yig'indisi qaytariladi (bir marta hisoblanadi, ikki marta
    emas — avvalgi versiyada Kassa va Bank balanslari alohida so'ralganda
    to'liq boshlang'ich qoldiq HAR IKKALASIGA ham qo'shilib, "Jami"
    kartada ikki marta hisoblanib ketardi)."""
    cur = currency.lower()
    if source:
        return float(get_setting(f"cash_opening_{source}_{cur}", "0") or 0)
    return (
        float(get_setting(f"cash_opening_kassa_{cur}", "0") or 0)
        + float(get_setting(f"cash_opening_bank_{cur}", "0") or 0)
    )


def get_cash_opening_date():
    """Boshlang'ich qoldiq QAYSI SANAGA tegishli (masalan inventarizatsiya
    kuni) — shu sanadan KEYINGI operatsiyalargina qoldiqqa qo'shib
    boriladi. Bo'sh bo'lsa (hech qachon kiritilmagan) — eski xulq-atvor:
    boshlang'ich qoldiq HAMMA operatsiyalardan oldin deb hisoblanadi."""
    return get_setting("cash_opening_date", "") or None


def get_cash_balance(currency, upto_date=None, source=None):
    """Kassa/bank qoldig'i: boshlang'ich qoldiq + shu sanagacha (kiritilgan bo'lsa)
    barcha kirim - chiqim. `upto_date` berilmasa — joriy (barcha vaqt) qoldiq.
    Boshlang'ich qoldiqqa sana belgilangan bo'lsa, faqat shu sanadan KEYINGI
    operatsiyalar hisobga olinadi (boshlang'ich qoldiq shu sanadagi
    "suratga tushirilgan" — snapshot — qoldiq deb qaraladi)."""
    opening = get_cash_opening(currency, source)
    opening_date = get_cash_opening_date()
    conn = get_conn()
    q = "SELECT type, SUM(amount) AS total FROM cash_transactions WHERE currency=?"
    params = [currency]
    if source:
        q += " AND source=?"
        params.append(source)
    if opening_date:
        q += " AND date>?"
        params.append(opening_date)
    if upto_date:
        q += " AND date<=?"
        params.append(upto_date)
    q += " GROUP BY type"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    income = sum(r["total"] for r in rows if r["type"] == "income")
    expense = sum(r["total"] for r in rows if r["type"] == "expense")
    return opening + income - expense


def list_custom_categories():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM custom_categories ORDER BY name COLLATE NOCASE").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_custom_category(name, group_key):
    if group_key not in FORMA2_GROUP_LABELS:
        raise ValueError("invalid_group")
    conn = get_conn()
    conn.execute(
        "INSERT INTO custom_categories (name, group_key) VALUES (?,?)",
        (name.strip(), group_key),
    )
    conn.commit()
    conn.close()


def delete_custom_category(cat_id):
    conn = get_conn()
    conn.execute("DELETE FROM custom_categories WHERE id=?", (cat_id,))
    conn.commit()
    conn.close()


def all_categories():
    """CATEGORIES (o'rnatilgan) + Sozlamalar orqali qo'shilgan turkumlar."""
    return CATEGORIES + [{"name": c["name"], "group": c["group_key"]} for c in list_custom_categories()]


def all_category_group_map():
    m = dict(CATEGORY_GROUP)
    m.update({c["name"]: c["group_key"] for c in list_custom_categories()})
    return m


def list_custom_cash_categories():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM custom_cash_categories ORDER BY code").fetchall()
    conn.close()
    return [dict(r) for r in rows]


_CASH_CODE_BANDS = {
    ("operatsion", "income"): (1000, 1999), ("operatsion", "expense"): (2000, 2999),
    ("investitsion", "income"): (3000, 3499), ("investitsion", "expense"): (3500, 3999),
    ("moliyaviy", "income"): (4000, 4499), ("moliyaviy", "expense"): (4500, 4999),
}


def _next_cash_category_code(section, ttype):
    """Bo'lim+tur uchun keyingi bo'sh kodni hosil qiladi — mavjud kodlash
    sxemasiga mos: operatsion 1xxx(income)/2xxx(expense), investitsion
    3xxx(income)/35xx(expense), moliyaviy 4xxx(income)/45xx(expense)."""
    lo, hi = _CASH_CODE_BANDS[(section, ttype)]
    used = [int(c["code"]) for c in CASH_CATEGORIES + list_custom_cash_categories() if lo <= int(c["code"]) <= hi]
    return str(max(used, default=lo - 1) + 1)


def add_custom_cash_category(name, section, ttype):
    if section not in CASH_SECTION_LABELS:
        raise ValueError("invalid_section")
    if ttype not in ("income", "expense"):
        raise ValueError("invalid_type")
    code = _next_cash_category_code(section, ttype)
    conn = get_conn()
    conn.execute(
        "INSERT INTO custom_cash_categories (code, name, section, type) VALUES (?,?,?,?)",
        (code, name.strip(), section, ttype),
    )
    conn.commit()
    conn.close()


def delete_custom_cash_category(cat_id):
    conn = get_conn()
    conn.execute("DELETE FROM custom_cash_categories WHERE id=?", (cat_id,))
    conn.commit()
    conn.close()


def all_cash_categories():
    """CASH_CATEGORIES (o'rnatilgan) + Sozlamalar orqali qo'shilgan turkumlar."""
    return CASH_CATEGORIES + [
        {"code": c["code"], "name": c["name"], "section": c["section"], "type": c["type"]}
        for c in list_custom_cash_categories()
    ]


def all_cash_category_map():
    m = dict(CASH_CATEGORY_MAP)
    m.update({c["name"]: c for c in all_cash_categories() if c["name"] not in CASH_CATEGORY_MAP})
    return m


def list_counterparties():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM counterparties ORDER BY name COLLATE NOCASE").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_counterparty(name, inn=""):
    """Bir xil nom (katta-kichik harfga qaramay) allaqachon mavjud bo'lsa,
    YANGI qator yaratilmaydi — agar bergan INN mavjud yozuvda yo'q bo'lsa,
    o'sha yozuv yangilanadi (dublikatlarning oldini olish uchun)."""
    name = name.strip()
    inn = (inn or "").strip()
    conn = get_conn()
    existing = conn.execute(
        "SELECT id, inn FROM counterparties WHERE name=? COLLATE NOCASE", (name,)
    ).fetchone()
    if existing:
        if inn and not existing["inn"]:
            conn.execute("UPDATE counterparties SET inn=? WHERE id=?", (inn, existing["id"]))
            conn.commit()
        conn.close()
        return
    conn.execute("INSERT OR IGNORE INTO counterparties (name, inn) VALUES (?,?)", (name, inn))
    conn.commit()
    conn.close()


def update_counterparty(cp_id, name, inn=""):
    conn = get_conn()
    conn.execute(
        "UPDATE counterparties SET name=?, inn=? WHERE id=?",
        (name.strip(), (inn or "").strip(), cp_id),
    )
    conn.commit()
    conn.close()


def delete_counterparty(cp_id):
    conn = get_conn()
    conn.execute("DELETE FROM counterparties WHERE id=?", (cp_id,))
    conn.commit()
    conn.close()


def import_existing_counterparties():
    """Xarajatlar/Kassa-Bank/Bar-Sklad/Xizmatlar sahifalarida allaqachon
    erkin matn sifatida kiritilgan barcha kontragent nomlarini
    `counterparties` ma'lumotnomasiga bir martalik ko'chirib qo'yadi.
    Oxiridagi 7-12 xonali raqam (INN) topilsa, u nomdan ajratib alohida
    saqlanadi. Bir xil nom uchun `add_counterparty` o'zi dublikat
    yaratmaydi (qayta ishga tushirish xavfsiz)."""
    before = {c["id"] for c in list_counterparties()}
    for raw in list_all_counterparties():
        raw = raw.strip()
        if not raw:
            continue
        m = re.match(r"^(.*?)\s+(\d{7,12})$", raw)
        if m:
            name, inn = m.group(1).strip(), m.group(2)
        else:
            name, inn = raw, ""
        add_counterparty(name, inn)
    after = list_counterparties()
    return sum(1 for c in after if c["id"] not in before)


def cash_income_by_counterparty(currency):
    """Har bir kontragent nomi bo'yicha Kassa/Bank'ga kirim qilingan JAMI
    summa (barcha vaqt) — OTA platforma qarzini "yopish" uchun: platforma
    haqiqatda pul o'tkazganda, xodim Kassa/Bank'ga oddiy kirim yozadi va
    kontragent maydoniga platforma nomini kiritadi (masalan "Booking.com");
    shu summa o'sha platformaning hisoblangan qarzidan avtomatik ayiriladi."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT counterparty, SUM(amount) s FROM cash_transactions "
        "WHERE type='income' AND currency=? AND counterparty IS NOT NULL AND counterparty!='' "
        "GROUP BY counterparty",
        (currency,),
    ).fetchall()
    conn.close()
    return {r["counterparty"]: r["s"] for r in rows}


def cash_flow_by_category(year, month):
    """Forma 3 (batafsil) uchun: har bir Cash Flow turkumi (kod) bo'yicha
    Bank va Kassa alohida-alohida kirim/chiqim yig'indisi."""
    rows = list_cash_transactions(year, month)
    data = {}
    for r in rows:
        bucket = data.setdefault(r["category"], {
            "bank": {"income": {"UZS": 0.0, "USD": 0.0}, "expense": {"UZS": 0.0, "USD": 0.0}},
            "kassa": {"income": {"UZS": 0.0, "USD": 0.0}, "expense": {"UZS": 0.0, "USD": 0.0}},
        })
        bucket[r["source"]][r["type"]][r["currency"]] += r["amount"]
    return data


# ---- Oylarni yopish (ketma-ket, tekshiruv ro'yxati bilan) ----
# Oylar QAT'IY ketma-ketlikda yopiladi (avvalgi oy yopilmagan bo'lsa, keyingisini
# yopib bo'lmaydi). Yopilgan oyga tegishli yozuvlarni (tranzaksiya/kassa/xizmat)
# hech kim (Super Admin ham) to'g'ridan-to'g'ri tahrirlay olmaydi — avval o'sha
# oy qayta ochilishi kerak.

def _current_year_month():
    return datetime.now().strftime("%Y-%m")


def _earliest_data_month():
    conn = get_conn()
    months = []
    for table in ("transactions", "cash_transactions", "bar_transactions"):
        row = conn.execute(f"SELECT MIN(date) m FROM {table}").fetchone()
        if row and row["m"]:
            months.append(row["m"][:7])
    conn.close()
    return min(months) if months else _current_year_month()


def _months_range(start_ym, end_ym):
    y1, m1 = (int(x) for x in start_ym.split("-"))
    y2, m2 = (int(x) for x in end_ym.split("-"))
    months = []
    y, m = y1, m1
    while (y, m) <= (y2, m2):
        months.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def list_relevant_months():
    """Yopish sahifasida ko'rsatiladigan oylar: eng birinchi ma'lumot oyidan
    joriy oygacha, xronologik tartibda (eskisi oldin)."""
    return _months_range(_earliest_data_month(), _current_year_month())


def is_month_closed(year_month):
    conn = get_conn()
    row = conn.execute("SELECT 1 FROM closed_months WHERE year_month=?", (year_month,)).fetchone()
    conn.close()
    return row is not None


def is_date_locked(date_str):
    return is_month_closed(date_str[:7])


def month_close_status(year_month):
    """'ongoing' (hali tugamagan) | 'closed' (yopilgan) | 'next' (navbatda,
    hozir yopish mumkin) | 'waiting' (navbat kutmoqda)."""
    current = _current_year_month()
    if year_month >= current:
        return "ongoing"
    if is_month_closed(year_month):
        return "closed"
    prior = [m for m in _months_range(_earliest_data_month(), current) if m < year_month]
    if all(is_month_closed(m) for m in prior):
        return "next"
    return "waiting"


def month_end_date(year_month):
    y, m = (int(x) for x in year_month.split("-"))
    last_day = calendar.monthrange(y, m)[1]
    return f"{y:04d}-{m:02d}-{last_day:02d}"


def month_checklist(year_month):
    """Oyni yopishdan oldingi tekshiruvlar ro'yxati + shu oy oxiridagi kassa
    qoldiqlari (UZS, USD)."""
    status = month_close_status(year_month)
    month_end = month_end_date(year_month)
    bal_uzs = get_cash_balance("UZS", upto_date=month_end)
    bal_usd = get_cash_balance("USD", upto_date=month_end)
    y, m = (int(x) for x in year_month.split("-"))
    cats = {c["name"] for c in all_cash_categories()}
    rows = list_cash_transactions(y, m)
    checks = [
        {"key": "not_closed", "ok": status != "closed"},
        {"key": "sequence", "ok": status in ("next", "closed")},
        {"key": "ended", "ok": status != "ongoing"},
        {"key": "rate", "ok": get_exchange_rate_on(month_end) is not None},
        {"key": "no_negative", "ok": bal_uzs >= -0.01 and bal_usd >= -0.01},
        {"key": "codes", "ok": all(r["category"] in cats for r in rows)},
    ]
    return checks, bal_uzs, bal_usd


def close_month(year_month, user_id):
    checks, bal_uzs, bal_usd = month_checklist(year_month)
    if not all(c["ok"] for c in checks):
        raise ValueError("checklist_failed")
    snapshot = json.dumps({"cash_uzs": bal_uzs, "cash_usd": bal_usd}, ensure_ascii=False)
    conn = get_conn()
    conn.execute(
        "INSERT INTO closed_months (year_month, closed_by, snapshot_json) VALUES (?,?,?)",
        (year_month, user_id, snapshot),
    )
    conn.commit()
    conn.close()


def reopen_month(year_month):
    """Faqat eng oxirgi yopilgan oyni qayta ochish mumkin (ketma-ketlikni
    saqlash uchun) — aks holda undan keyingi (allaqachon yopiq) oy bilan
    nomuvofiqlik yuzaga keladi."""
    conn = get_conn()
    later_closed = conn.execute(
        "SELECT COUNT(*) c FROM closed_months WHERE year_month > ?", (year_month,)
    ).fetchone()["c"]
    if later_closed:
        conn.close()
        raise ValueError("later_month_closed")
    conn.execute("DELETE FROM closed_months WHERE year_month=?", (year_month,))
    conn.commit()
    conn.close()


# ---- Foydalanuvchilar / huquqlar ----

def _user_from_row(row):
    if row is None:
        return None
    d = dict(row)
    d["permissions"] = json.loads(d["permissions"] or "[]")
    return d


def get_user_by_username(username):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return _user_from_row(row)


def get_user_by_id(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return _user_from_row(row)


def list_users():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
    conn.close()
    return [_user_from_row(r) for r in rows]


def add_user(username, password, full_name, role_id):
    conn = get_conn()
    conn.execute(
        "INSERT INTO users (username, password_hash, full_name, role, role_id) VALUES (?,?,?,'custom',?)",
        (username, generate_password_hash(password), full_name, role_id),
    )
    conn.commit()
    conn.close()


def update_user(user_id, full_name, role_id, is_active, password=None):
    conn = get_conn()
    if password:
        conn.execute(
            "UPDATE users SET full_name=?, role_id=?, is_active=?, password_hash=? WHERE id=?",
            (full_name, role_id, int(is_active), generate_password_hash(password), user_id),
        )
    else:
        conn.execute(
            "UPDATE users SET full_name=?, role_id=?, is_active=? WHERE id=?",
            (full_name, role_id, int(is_active), user_id),
        )
    conn.commit()
    conn.close()


def delete_user(user_id):
    conn = get_conn()
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()


def has_permission(user, module, action):
    if not user:
        return False
    if user["role"] == "super_admin":
        return True
    role = get_role(user["role_id"]) if user.get("role_id") else None
    if not role:
        return False
    return bool(role["permissions"].get(module, {}).get(action, False))


def _role_from_row(row):
    if row is None:
        return None
    d = dict(row)
    d["permissions"] = json.loads(d["permissions"] or "{}")
    return d


def list_roles():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM roles ORDER BY id").fetchall()
    conn.close()
    return [_role_from_row(r) for r in rows]


def get_role(role_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM roles WHERE id=?", (role_id,)).fetchone()
    conn.close()
    return _role_from_row(row)


def role_user_count(role_id):
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) c FROM users WHERE role_id=?", (role_id,)).fetchone()["c"]
    conn.close()
    return n


def add_role(name, description, permissions):
    conn = get_conn()
    conn.execute(
        "INSERT INTO roles (name, description, permissions) VALUES (?,?,?)",
        (name, description, json.dumps(permissions)),
    )
    conn.commit()
    conn.close()


def update_role(role_id, name, description, permissions):
    conn = get_conn()
    conn.execute(
        "UPDATE roles SET name=?, description=?, permissions=? WHERE id=?",
        (name, description, json.dumps(permissions), role_id),
    )
    conn.commit()
    conn.close()


def delete_role(role_id):
    """Tizim rollari (is_system=1) yoki hozir kamida bitta foydalanuvchiga
    biriktirilgan rollarni o'chirishga urinish xatolik qaytaradi."""
    conn = get_conn()
    row = conn.execute("SELECT is_system FROM roles WHERE id=?", (role_id,)).fetchone()
    if row is None:
        conn.close()
        return
    if row["is_system"]:
        conn.close()
        raise ValueError("system_role")
    if role_user_count(role_id):
        conn.close()
        raise ValueError("role_in_use")
    conn.execute("DELETE FROM roles WHERE id=?", (role_id,))
    conn.commit()
    conn.close()

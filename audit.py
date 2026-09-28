# -*- coding: utf-8 -*-
"""Butun loyiha uchun audit jurnali: kim, qachon, qayerdan, nima qildi.

Yozib boriladi:
  * login / login_failed / logout;
  * har bir o'zgartiruvchi (POST) so'rov: create / update / delete / import,
    yuborilgan forma maydonlari va so'rov natijasi (flash xabar) bilan;
  * eksport (fayl yuklab olish, Content-Disposition: attachment).

Maxfiy maydonlar (parol, kalit, token) qiymati YOZILMAYDI. Jurnal faqat yuborilgan
(yangi) qiymatlarni saqlaydi — o'zgarishdan oldingi qiymatni emas.
"""
import json
import re

from db import get_conn

REDACT = re.compile(r"pass|parol|secret|token|pwd|key|pasport", re.IGNORECASE)   # "pass" pasport (passport) ni ham qamraydi
SKIP_PREFIXES = ("/webhooks/exely/",)      # vebhukning o'z jurnali bor
MAX_ROWS = 200_000
MAX_FIELDS = 40
MAX_VALUE = 200

CREATE_WORDS = ("add", "create", "new", "checkin", "restock", "sale", "open")
DELETE_WORDS = ("delete", "remove")


def classify(endpoint, path):
    text = f"{endpoint or ''} {path or ''}".lower()
    if any(w in text for w in DELETE_WORDS):
        return "delete"
    if "import" in text or "exely" in text or "sync" in text:
        return "import"
    if "export" in text:
        return "export"
    if any(w in text for w in CREATE_WORDS):
        return "create"
    return "update"


def _clip(v, n=MAX_VALUE):
    v = str(v)
    return v if len(v) <= n else v[:n] + "…"


def summarize_request(req):
    """So'rov mazmuni: forma maydonlari (maxfiylari yashirin), fayl nomlari, URL parametrlari."""
    out = {}
    fields = {}
    for k in list(req.form.keys())[:MAX_FIELDS]:
        if k == "csrf_token":
            continue
        fields[k] = "[yashirildi]" if REDACT.search(k) else _clip(", ".join(req.form.getlist(k)))
    if fields:
        out["form"] = fields
    files = {k: {"name": f.filename, "type": f.mimetype} for k, f in req.files.items() if f and f.filename}
    if files:
        out["files"] = files
    if req.args:
        out["query"] = {k: _clip(v, 100) for k, v in list(req.args.items())[:10]}
    js = req.get_json(silent=True)
    if isinstance(js, dict):
        out["json"] = {k: ("[yashirildi]" if REDACT.search(k) else _clip(v)) for k, v in list(js.items())[:MAX_FIELDS]}
    return out


def log_event(action, *, user=None, username=None, ip="", method="", path="", endpoint="", status=None, detail=None):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO audit_log (at, user_id, username, ip, action, method, path, endpoint, status, detail)"
        " VALUES (datetime('now','localtime'),?,?,?,?,?,?,?,?,?)",
        (user["id"] if user else None, (user["username"] if user else username) or "", ip, action, method,
         path, endpoint or "", status, json.dumps(detail, ensure_ascii=False)[:6000] if detail else None),
    )
    conn.execute("DELETE FROM audit_log WHERE id <= ?", (cur.lastrowid - MAX_ROWS,))
    conn.commit()
    conn.close()


def query(user_id=None, action=None, q=None, date_from=None, date_to=None, limit=50, offset=0):
    where, params = [], []
    if user_id:
        where.append("user_id=?"); params.append(user_id)
    if action:
        where.append("action=?"); params.append(action)
    if q:
        where.append("(path LIKE ? OR detail LIKE ? OR username LIKE ? OR ip LIKE ?)")
        params += [f"%{q}%"] * 4
    if date_from:
        where.append("at >= ?"); params.append(date_from + " 00:00:00")
    if date_to:
        where.append("at <= ?"); params.append(date_to + " 23:59:59")
    w = (" WHERE " + " AND ".join(where)) if where else ""
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) c FROM audit_log" + w, params).fetchone()["c"]
    rows = conn.execute("SELECT * FROM audit_log" + w + " ORDER BY id DESC LIMIT ? OFFSET ?",
                        params + [limit, offset]).fetchall()
    conn.close()
    return [dict(r) for r in rows], total


def actor_list():
    conn = get_conn()
    rows = conn.execute("SELECT DISTINCT user_id, username FROM audit_log WHERE user_id IS NOT NULL ORDER BY username").fetchall()
    conn.close()
    return [dict(r) for r in rows]

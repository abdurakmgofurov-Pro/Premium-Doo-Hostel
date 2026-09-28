# -*- coding: utf-8 -*-
"""Xonalar (hostel xonalari) boshqaruv moduli — biznes mantig'i.

Uch alohida narsa:
  * xona turlari va xonalar (sozlamalar) — `room_types`, `rooms`;
  * BRONLAR (Excel'dan import) — `hostel_bookings`: "kim kelishi kerak";
    Exely'dan faqat shu olinadi, `bookings_cache`dan mustaqil;
  * HAQIQIY joylashtirish — `stays`: "kim hozir qaysi xonada". Bron asosida
    yoki bronsiz yaratiladi; bron o'chirilsa/o'zgarsa joylashtirish
    tarixi saqlanib qoladi.

Xato kodlari ValueError orqali qaytariladi (app.py ularni tarjima qiladi).
"""
import hashlib
from datetime import date, datetime, timedelta

from db import get_conn

MANUAL_STATUSES = ("cleaning", "maintenance")


def today_str():
    return date.today().strftime("%Y-%m-%d")


def _fail(conn, code):
    conn.close()
    raise ValueError(code)


# ---------------------------------------------------------------- xona turlari

def list_room_types():
    conn = get_conn()
    rows = conn.execute(
        "SELECT t.*, (SELECT COUNT(*) FROM rooms r WHERE r.room_type_id=t.id) AS rooms_count"
        " FROM room_types t ORDER BY t.capacity, t.name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_room_type(name, capacity, price, currency):
    name = (name or "").strip()
    conn = get_conn()
    if not name or int(capacity) <= 0:
        _fail(conn, "invalid_input")
    if conn.execute("SELECT 1 FROM room_types WHERE name=?", (name,)).fetchone():
        _fail(conn, "duplicate_name")
    conn.execute(
        "INSERT INTO room_types (name, capacity, price, currency) VALUES (?,?,?,?)",
        (name, int(capacity), float(price or 0), currency),
    )
    conn.commit()
    conn.close()


def update_room_type(type_id, name, capacity, price, currency):
    name = (name or "").strip()
    conn = get_conn()
    if not name or int(capacity) <= 0:
        _fail(conn, "invalid_input")
    if conn.execute("SELECT 1 FROM room_types WHERE name=? AND id<>?", (name, type_id)).fetchone():
        _fail(conn, "duplicate_name")
    conn.execute(
        "UPDATE room_types SET name=?, capacity=?, price=?, currency=? WHERE id=?",
        (name, int(capacity), float(price or 0), currency, type_id),
    )
    conn.commit()
    conn.close()


def delete_room_type(type_id):
    conn = get_conn()
    if conn.execute("SELECT 1 FROM rooms WHERE room_type_id=?", (type_id,)).fetchone():
        _fail(conn, "room_type_in_use")
    conn.execute("DELETE FROM room_types WHERE id=?", (type_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------- xonalar

def list_rooms(include_inactive=True):
    conn = get_conn()
    q = ("SELECT r.*, t.name AS type_name FROM rooms r"
         " LEFT JOIN room_types t ON t.id=r.room_type_id")
    if not include_inactive:
        q += " WHERE r.active=1"
    q += " ORDER BY r.floor, CAST(r.number AS INTEGER), r.number"
    rows = conn.execute(q).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_room(room_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT r.*, t.name AS type_name FROM rooms r LEFT JOIN room_types t ON t.id=r.room_type_id WHERE r.id=?",
        (room_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def _open_count(conn, room_id):
    return conn.execute(
        "SELECT COUNT(*) c FROM stays WHERE room_id=? AND check_out IS NULL", (room_id,)
    ).fetchone()["c"]


def add_room(number, floor, room_type_id, capacity, price, currency, note=""):
    number = (number or "").strip()
    conn = get_conn()
    if not number or int(capacity) <= 0:
        _fail(conn, "invalid_input")
    if conn.execute("SELECT 1 FROM rooms WHERE number=?", (number,)).fetchone():
        _fail(conn, "duplicate_number")
    conn.execute(
        "INSERT INTO rooms (number, floor, room_type_id, capacity, price, currency, note) VALUES (?,?,?,?,?,?,?)",
        (number, int(floor or 1), room_type_id or None, int(capacity), float(price or 0), currency, note),
    )
    conn.commit()
    conn.close()


def update_room(room_id, number, floor, room_type_id, capacity, price, currency, active, note=""):
    number = (number or "").strip()
    conn = get_conn()
    if not number or int(capacity) <= 0:
        _fail(conn, "invalid_input")
    if conn.execute("SELECT 1 FROM rooms WHERE number=? AND id<>?", (number, room_id)).fetchone():
        _fail(conn, "duplicate_number")
    occupants = _open_count(conn, room_id)
    if int(capacity) < occupants:
        _fail(conn, "capacity_below_occupants")
    if not active and occupants:
        _fail(conn, "room_not_empty")
    conn.execute(
        "UPDATE rooms SET number=?, floor=?, room_type_id=?, capacity=?, price=?, currency=?, active=?, note=? WHERE id=?",
        (number, int(floor or 1), room_type_id or None, int(capacity), float(price or 0), currency,
         1 if active else 0, note, room_id),
    )
    conn.commit()
    conn.close()


def delete_room(room_id):
    conn = get_conn()
    if conn.execute("SELECT 1 FROM stays WHERE room_id=?", (room_id,)).fetchone():
        # Tarix (bandlik foizi) buzilmasligi uchun joylashtirish tarixi bor
        # xonani o'chirib bo'lmaydi — faqat "faol emas" qilinadi.
        _fail(conn, "room_has_history")
    conn.execute("DELETE FROM rooms WHERE id=?", (room_id,))
    conn.commit()
    conn.close()


def set_manual_status(room_id, status):
    """status: '' (bo'sh/normal), 'cleaning' yoki 'maintenance'."""
    if status and status not in MANUAL_STATUSES:
        raise ValueError("invalid_input")
    conn = get_conn()
    if status and _open_count(conn, room_id):
        _fail(conn, "room_not_empty")
    conn.execute("UPDATE rooms SET manual_status=? WHERE id=?", (status or "", room_id))
    conn.commit()
    conn.close()


def effective_status(room, occupants_count):
    """free / partial / full / cleaning / maintenance."""
    if room["manual_status"] in MANUAL_STATUSES:
        return room["manual_status"]
    if occupants_count <= 0:
        return "free"
    return "full" if occupants_count >= room["capacity"] else "partial"


def board(floor=None, type_id=None, status=None, q=None):
    """Joriy holat: faol xonalar + ulardagi (hali chiqmagan) mehmonlar."""
    conn = get_conn()
    stays = conn.execute("SELECT * FROM stays WHERE check_out IS NULL ORDER BY check_in, id").fetchall()
    conn.close()
    by_room = {}
    for s in stays:
        by_room.setdefault(s["room_id"], []).append(dict(s))
    q_low = (q or "").strip().lower()
    result = []
    for room in list_rooms(include_inactive=False):
        occ = by_room.get(room["id"], [])
        room["occupants"] = occ
        room["occupied"] = len(occ)
        room["free_beds"] = max(room["capacity"] - len(occ), 0)
        room["status"] = effective_status(room, len(occ))
        if floor not in (None, "") and str(room["floor"]) != str(floor):
            continue
        if type_id not in (None, "") and str(room["room_type_id"]) != str(type_id):
            continue
        if status and room["status"] != status:
            continue
        if q_low and q_low not in room["number"].lower() and not any(q_low in o["guest_name"].lower() for o in occ):
            continue
        result.append(room)
    return result


def summary(board_rows):
    total_rooms = len(board_rows)
    beds = sum(r["capacity"] for r in board_rows)
    occupied_beds = sum(min(r["occupied"], r["capacity"]) for r in board_rows)
    counts = {k: 0 for k in ("free", "partial", "full", "cleaning", "maintenance")}
    for r in board_rows:
        counts[r["status"]] += 1
    occupied_rooms = counts["partial"] + counts["full"]
    return {
        "rooms": total_rooms, "beds": beds, "occupied_beds": occupied_beds, "free_beds": beds - occupied_beds,
        "counts": counts, "occupied_rooms": occupied_rooms,
        "room_pct": round(occupied_rooms / total_rooms * 100, 1) if total_rooms else 0.0,
        "bed_pct": round(occupied_beds / beds * 100, 1) if beds else 0.0,
    }


# ---------------------------------------------------------- joylashtirish (stays)

def _validate_dates(check_in, expected_departure=None):
    if not check_in or check_in > today_str():
        raise ValueError("future_checkin")
    if expected_departure and expected_departure < check_in:
        raise ValueError("departure_before_arrival")


def clean_passport(value):
    """Pasport seriyasi/raqami: bo'shliqlarsiz, KATTA harflarda, 20 belgigacha."""
    return "".join((value or "").split()).upper()[:20]


def check_in(room_id, guest_name, check_in_date, expected_departure=None, booking_id=None, note="", passport=""):
    guest_name = (guest_name or "").strip()
    if not guest_name:
        raise ValueError("invalid_input")
    _validate_dates(check_in_date, expected_departure)
    conn = get_conn()
    room = conn.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()
    if not room or not room["active"]:
        _fail(conn, "room_unavailable")
    if room["manual_status"] == "maintenance":
        _fail(conn, "room_unavailable")
    if _open_count(conn, room_id) >= room["capacity"]:
        _fail(conn, "room_full")
    if booking_id:
        bk = conn.execute("SELECT * FROM hostel_bookings WHERE id=?", (booking_id,)).fetchone()
        if not bk:
            _fail(conn, "booking_not_found")
        if bk["is_cancelled"]:
            _fail(conn, "booking_cancelled")
        if bk["stay_id"] and conn.execute(
                "SELECT 1 FROM stays WHERE id=? AND check_out IS NULL", (bk["stay_id"],)).fetchone():
            _fail(conn, "booking_already_placed")
    cur = conn.execute(
        "INSERT INTO stays (room_id, guest_name, check_in, expected_departure, booking_id, note, passport) VALUES (?,?,?,?,?,?,?)",
        (room_id, guest_name, check_in_date, expected_departure or None, booking_id or None, note, clean_passport(passport) or None),
    )
    stay_id = cur.lastrowid
    if room["manual_status"] == "cleaning":
        conn.execute("UPDATE rooms SET manual_status='' WHERE id=?", (room_id,))
    if booking_id:
        conn.execute("UPDATE hostel_bookings SET stay_id=? WHERE id=?", (stay_id, booking_id))
    conn.commit()
    conn.close()
    return stay_id


def get_stay(stay_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM stays WHERE id=?", (stay_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def check_out(stay_id, out_date=None):
    out_date = out_date or today_str()
    conn = get_conn()
    stay = conn.execute("SELECT * FROM stays WHERE id=?", (stay_id,)).fetchone()
    if not stay or stay["check_out"]:
        _fail(conn, "stay_not_active")
    if out_date < stay["check_in"] or out_date > today_str():
        _fail(conn, "invalid_checkout_date")
    conn.execute("UPDATE stays SET check_out=? WHERE id=?", (out_date, stay_id))
    conn.commit()
    conn.close()


def move_stay(stay_id, new_room_id, move_date=None):
    """Mehmonni boshqa xonaga ko'chiradi. Bandlik tarixi to'g'ri qolishi
    uchun eski joylashtirish `move_date`da yopiladi va yangisi shu sanadan
    ochiladi (bir kunning ichida kirib-ko'chirilgan bo'lsa — shunchaki xona
    almashtiriladi)."""
    move_date = move_date or today_str()
    conn = get_conn()
    stay = conn.execute("SELECT * FROM stays WHERE id=?", (stay_id,)).fetchone()
    if not stay or stay["check_out"]:
        _fail(conn, "stay_not_active")
    if int(new_room_id) == stay["room_id"]:
        _fail(conn, "same_room")
    if move_date < stay["check_in"] or move_date > today_str():
        _fail(conn, "invalid_checkout_date")
    room = conn.execute("SELECT * FROM rooms WHERE id=?", (new_room_id,)).fetchone()
    if not room or not room["active"] or room["manual_status"] == "maintenance":
        _fail(conn, "room_unavailable")
    if _open_count(conn, new_room_id) >= room["capacity"]:
        _fail(conn, "room_full")
    old_room = conn.execute("SELECT number FROM rooms WHERE id=?", (stay["room_id"],)).fetchone()
    if move_date == stay["check_in"]:
        conn.execute("UPDATE stays SET room_id=? WHERE id=?", (new_room_id, stay_id))
        new_id = stay_id
    else:
        conn.execute("UPDATE stays SET check_out=? WHERE id=?", (move_date, stay_id))
        note = ((stay["note"] or "") + f" [⇄ {old_room['number'] if old_room else '?'} → {room['number']}]").strip()
        cur = conn.execute(
            "INSERT INTO stays (room_id, guest_name, check_in, expected_departure, booking_id, note, passport) VALUES (?,?,?,?,?,?,?)",
            (new_room_id, stay["guest_name"], move_date, stay["expected_departure"], stay["booking_id"], note, stay["passport"]),
        )
        new_id = cur.lastrowid
        if stay["booking_id"]:
            conn.execute("UPDATE hostel_bookings SET stay_id=? WHERE id=?", (new_id, stay["booking_id"]))
    if room["manual_status"] == "cleaning":
        conn.execute("UPDATE rooms SET manual_status='' WHERE id=?", (new_room_id,))
    conn.commit()
    conn.close()
    return new_id


# ------------------------------------------------------ bronlar (Excel'dan import)

def _norm(s):
    return " ".join(str(s or "").lower().split())


def dedup_key(ref, guest, arrival, departure, room_text):
    """Bron raqami bor bo'lsa — faqat u (shu bron keyingi importda
    YANGILANADI, dublikat bo'lmaydi); yo'q bo'lsa — mehmon+sanalar+xona."""
    if ref:
        raw = "ref|" + _norm(ref)
    else:
        raw = "|".join(["k", _norm(guest), arrival or "", departure or "", _norm(room_text)])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def is_cancelled_text(status_text):
    s = _norm(status_text)
    return any(w in s for w in ("cancel", "отмен", "bekor", "annul", "no-show", "no show", "noshow", "незаезд"))


def preview_import(rows):
    """Yangi / o'zgargan / o'zgarmagan bronlar sonini import QILMASDAN sanaydi."""
    conn = get_conn()
    new = changed = same = 0
    out = []
    for r in rows:
        key = dedup_key(r["ref"], r["guest"], r["arrival"], r["departure"], r["room"])
        cur = conn.execute("SELECT * FROM hostel_bookings WHERE dedup_key=?", (key,)).fetchone()
        if not cur:
            state = "new"; new += 1
        elif _row_differs(cur, r):
            state = "changed"; changed += 1
        else:
            state = "same"; same += 1
        out.append({**r, "state": state})
    conn.close()
    return out, {"new": new, "changed": changed, "same": same}


# Exely PMS'dan keladigan qo'shimcha maydonlar; Excel qatorlarida bo'lmasligi mumkin (u holda tegilmaydi)
EXTRA_FIELDS = ("customer_name", "phone", "adults", "children", "check_in_at", "check_out_at", "actual_in_at",
                "actual_out_at", "total_amount", "paid_amount", "refund_amount", "currency")


def _norm_extra(v):
    return "" if v is None else v


def _row_differs(cur, r):
    return (
        (cur["guest_name"] or "") != r["guest"] or (cur["arrival"] or "") != (r["arrival"] or "")
        or (cur["departure"] or "") != (r["departure"] or "") or (cur["room_type_text"] or "") != r["room_type"]
        or (cur["room_text"] or "") != r["room"] or (cur["status_text"] or "") != r["status"]
        or (cur["note"] or "") != r["note"]
        or any(k in r and _norm_extra(cur[k]) != _norm_extra(r[k]) for k in EXTRA_FIELDS)
    )


def import_bookings(rows):
    """Upsert: bron raqami (yoki mehmon+sana+xona) bo'yicha. Mavjud bron
    o'zgargan bo'lsa (masalan holati "Bekor qilindi" bo'lsa) YANGILANADI —
    stay_id (joylashtirish bog'i) saqlanib qoladi. Qaytaradi (yangi, yangilangan, o'zgarmagan)."""
    conn = get_conn()
    added = updated = unchanged = 0
    for r in rows:
        key = dedup_key(r["ref"], r["guest"], r["arrival"], r["departure"], r["room"])
        cancelled = 1 if is_cancelled_text(r["status"]) else 0
        extra = {k: r[k] for k in EXTRA_FIELDS if k in r}
        cur = conn.execute("SELECT * FROM hostel_bookings WHERE dedup_key=?", (key,)).fetchone()
        if not cur:
            cols = ["dedup_key", "ref", "guest_name", "arrival", "departure", "room_type_text", "room_text",
                    "status_text", "is_cancelled", "note"] + list(extra)
            vals = [key, r["ref"] or None, r["guest"], r["arrival"], r["departure"] or None, r["room_type"], r["room"],
                    r["status"], cancelled, r["note"]] + list(extra.values())
            conn.execute(f"INSERT INTO hostel_bookings ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", vals)
            added += 1
        elif _row_differs(cur, r):
            sets = ["guest_name=?", "arrival=?", "departure=?", "room_type_text=?", "room_text=?", "status_text=?",
                    "is_cancelled=?", "note=?"] + [f"{k}=?" for k in extra]
            vals = [r["guest"], r["arrival"], r["departure"] or None, r["room_type"], r["room"], r["status"],
                    cancelled, r["note"]] + list(extra.values()) + [cur["id"]]
            conn.execute(f"UPDATE hostel_bookings SET {', '.join(sets)}, updated_at=datetime('now') WHERE id=?", vals)
            updated += 1
        else:
            unchanged += 1
    conn.commit()
    conn.close()
    return added, updated, unchanged


def _bookings_where(search, only_unplaced, hide_cancelled):
    where, params = [], []
    if search:
        where.append("(guest_name LIKE ? OR ref LIKE ? OR room_text LIKE ?)")
        params += [f"%{search}%"] * 3
    if hide_cancelled:
        where.append("is_cancelled=0")
    if only_unplaced:
        where.append("NOT EXISTS (SELECT 1 FROM stays s WHERE s.booking_id=hostel_bookings.id)")
    return ((" WHERE " + " AND ".join(where)) if where else ""), params


def list_bookings(search=None, only_unplaced=False, hide_cancelled=True, limit=100, offset=0):
    conn = get_conn()
    w, params = _bookings_where(search, only_unplaced, hide_cancelled)
    total = conn.execute("SELECT COUNT(*) c FROM hostel_bookings" + w, params).fetchone()["c"]
    rows = conn.execute(
        "SELECT b.*, s.room_id AS placed_room_id, s.check_out AS placed_check_out,"
        " (SELECT number FROM rooms WHERE id=s.room_id) AS placed_room_number"
        " FROM (SELECT * FROM hostel_bookings" + w + " ORDER BY arrival DESC, id DESC LIMIT ? OFFSET ?) b"
        " LEFT JOIN stays s ON s.id=b.stay_id",
        params + [limit, offset],
    ).fetchall()
    conn.close()
    out = [dict(r) for r in rows]
    for r in out:
        r["balance"] = _balance(r)
    return out, total


def bookings_totals(search=None, only_unplaced=False):
    """Filtrga mos (bekor qilinmagan) bronlar summasi valyutalar bo'yicha:
    [{currency, count, total, paid, balance}] — narxi ma'lum bronlar uchun."""
    conn = get_conn()
    w, params = _bookings_where(search, only_unplaced, True)
    w += (" AND " if w else " WHERE ") + "total_amount IS NOT NULL"
    rows = conn.execute(
        "SELECT COALESCE(NULLIF(currency,''),'?') cur, COUNT(*) n, SUM(total_amount) total,"
        " SUM(COALESCE(paid_amount,0)) paid, SUM(COALESCE(refund_amount,0)) refund"
        " FROM hostel_bookings" + w + " GROUP BY cur ORDER BY total DESC", params).fetchall()
    conn.close()
    return [{"currency": r["cur"], "count": r["n"], "total": round(r["total"] or 0, 2), "paid": round(r["paid"] or 0, 2),
             "balance": round((r["total"] or 0) - (r["paid"] or 0) + (r["refund"] or 0), 2)} for r in rows]


def get_booking(booking_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM hostel_bookings WHERE id=?", (booking_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_booking(booking_id):
    conn = get_conn()
    conn.execute("DELETE FROM hostel_bookings WHERE id=?", (booking_id,))
    conn.execute("UPDATE stays SET booking_id=NULL WHERE booking_id=?", (booking_id,))
    conn.commit()
    conn.close()


# ------------------------------------------------------------- bandlik foizi

def _stays_all():
    conn = get_conn()
    rows = conn.execute("SELECT room_id, check_in, check_out FROM stays").fetchall()
    conn.close()
    return [(r["room_id"], r["check_in"], r["check_out"]) for r in rows]


def _day_occupancy(day, rooms, stays):
    occ = {}
    for room_id, ci, co in stays:
        if ci <= day and (co is None or co > day):
            occ[room_id] = occ.get(room_id, 0) + 1
    rooms_occ = sum(1 for r in rooms if occ.get(r["id"], 0) > 0)
    beds_occ = sum(min(occ.get(r["id"], 0), r["capacity"]) for r in rooms)
    return rooms_occ, beds_occ


def occupancy_series(days=30, granularity="day", end=None, exely=None):
    """Oxirgi `days` kun (bugungacha) uchun bandlik. Tarix HOZIRGI faol
    xonalar to'plamiga nisbatan hisoblanadi (xona sig'imi/faolligi tarixi
alohida saqlanmaydi). Haftalik/oylik — kunlik foizlarning o'rtachasi.
    `exely` — {sana: {"occ", "total"}}: berilsa, har qatorga Exely'ning bandligi
    (ex_occ/ex_total/ex_pct; ma'lumot bo'lmasa None) qo'shiladi."""
    end_d = datetime.strptime(end or today_str(), "%Y-%m-%d").date()
    start_d = end_d - timedelta(days=days - 1)
    rooms = list_rooms(include_inactive=False)
    stays = _stays_all()
    total_rooms = len(rooms)
    total_beds = sum(r["capacity"] for r in rooms)
    daily = []
    d = start_d
    while d <= end_d:
        ds = d.strftime("%Y-%m-%d")
        ro, bo = _day_occupancy(ds, rooms, stays)
        daily.append({
            "date": ds, "rooms_occ": ro, "rooms_total": total_rooms, "beds_occ": bo, "beds_total": total_beds,
            "room_pct": round(ro / total_rooms * 100, 1) if total_rooms else 0.0,
            "bed_pct": round(bo / total_beds * 100, 1) if total_beds else 0.0,
        })
        ex = (exely or {}).get(ds)
        daily[-1].update(ex_occ=ex["occ"] if ex else None, ex_total=ex["total"] if ex else None,
                         ex_pct=round(ex["occ"] / ex["total"] * 100, 1) if ex and ex["total"] else None)
        d += timedelta(days=1)
    if granularity == "day":
        for x in daily:
            x["label"] = x["date"]
        return daily
    groups = {}
    for x in daily:
        dt = datetime.strptime(x["date"], "%Y-%m-%d").date()
        key = (dt - timedelta(days=dt.weekday())).strftime("%Y-%m-%d") if granularity == "week" else x["date"][:7]
        groups.setdefault(key, []).append(x)
    result = []
    for key in sorted(groups):
        g = groups[key]
        n = len(g)
        result.append({
            "date": key, "label": key, "days": n,
            "rooms_occ": round(sum(i["rooms_occ"] for i in g) / n, 1), "rooms_total": total_rooms,
            "beds_occ": round(sum(i["beds_occ"] for i in g) / n, 1), "beds_total": total_beds,
            "room_pct": round(sum(i["room_pct"] for i in g) / n, 1),
            "bed_pct": round(sum(i["bed_pct"] for i in g) / n, 1),
            **_avg_exely(g),
        })
    return result


def _avg_exely(group):
    have = [i for i in group if i["ex_pct"] is not None]
    if not have:
        return {"ex_occ": None, "ex_total": None, "ex_pct": None}
    n = len(have)
    return {"ex_occ": round(sum(i["ex_occ"] for i in have) / n, 1), "ex_total": have[-1]["ex_total"],
            "ex_pct": round(sum(i["ex_pct"] for i in have) / n, 1)}


# ------------------------------------------------------------------ shaxmatka

def _d(text):
    try:
        return datetime.strptime((text or "")[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _balance(b):
    """Bron balansi: jami - to'langan + qaytarilgan (Exely'dagidek); ma'lumot bo'lmasa None."""
    if b.get("total_amount") is None:
        return None
    return round((b["total_amount"] or 0) - (b.get("paid_amount") or 0) + (b.get("refund_amount") or 0), 2)


def _booking_class(status_text):
    s = status_text or ""
    if "CheckedOut" in s:
        return "out"
    if "CheckedIn" in s:
        return "in"
    return "new"


def chart_data(start, days, today=None):
    """Shaxmatka (Exely'dagi kabi): qatorlar — o'rinlar (101.1, 101.2 ...) tur bo'yicha guruhlangan,
    ustunlar — kunlar, chiziqlar — bronlar (kelish kunining o'rtasidan ketish kunining o'rtasigacha).
    Bronlar `hostel_bookings`dan (Exely/Excel), xonasi bo'lmaganlari «xona tayinlanmagan» qatorida.
    Qaytaradi: {"days": [...], "groups": [...], "cards": {...}}."""
    today = today or date.today()
    end = start + timedelta(days=days)
    day_list = [start + timedelta(days=i) for i in range(days)]
    # tartib Exely'dagidek: sig'im bo'yicha, har bir sig'imda avval erkaklar, keyin ayollar
    type_order = {t["name"]: (t["capacity"], 1 if "ayollar" in t["name"] else 0, t["name"]) for t in list_room_types()}
    rooms = list_rooms(include_inactive=False)

    groups = {}
    bed_index = {}                       # "101.2" -> (guruh nomi, bed dict)
    for r in rooms:
        g = groups.setdefault(r["type_name"] or "", {"name": r["type_name"] or "", "beds": [], "beds_total": 0})
        for i in range(1, r["capacity"] + 1):
            bed = {"label": f"{r['number']}.{i}", "bars": []}
            g["beds"].append(bed)
            bed_index[bed["label"]] = (g["name"], bed)
        g["beds_total"] += r["capacity"]
    ordered = sorted(groups.values(), key=lambda g: type_order.get(g["name"], (10**6, 0, g["name"])))
    for g in ordered:
        g["occupied"] = [0] * days
        g["unassigned"] = [0] * days
        g["un_list"] = [[] for _ in range(days)]

    conn = get_conn()
    all_rows = [dict(r) for r in conn.execute("SELECT * FROM hostel_bookings WHERE is_cancelled=0")]
    conn.close()

    def span(b):
        a = _d(b["arrival"])
        dep = _d(b["departure"])
        if not a:
            return None, None
        if not dep or dep <= a:
            dep = a + timedelta(days=1)
        return a, dep

    fallback = ordered[0] if ordered else None
    for b in all_rows:
        a, dep = span(b)
        if not a or dep <= start or a >= end:
            continue
        ai, di = (a - start).days, (dep - start).days
        room_key = (b["room_text"] or "").strip()
        gname, bed = bed_index.get(room_key, (None, None))
        grp = groups.get(gname) if gname is not None else groups.get(b["room_type_text"] or "", fallback)
        if grp is None:
            continue
        for idx in range(max(ai, 0), min(di, days)):
            grp["occupied"][idx] += 1
            if bed is None:
                grp["unassigned"][idx] += 1
                grp["un_list"][idx].append({
                    "id": b["id"], "ref": b["ref"] or "", "guest": b["guest_name"],
                    "arrival_at": b["check_in_at"] or b["arrival"], "departure_at": b["check_out_at"] or (b["departure"] or ""),
                    "paid": b["paid_amount"], "balance": _balance(b), "currency": b["currency"] or ""})
        if bed is not None:
            left = max(ai + 0.5, 0)
            right = min(di + 0.5, days)
            if right > left:
                who = b["guest_name"] + ("" if not b["note"] else " · " + b["note"].split(" · ")[0])
                channel, _, comment = (b["note"] or "").partition(" · ")
                bed["bars"].append({
                    "left": round(left, 2), "width": round(right - left, 2), "name": who,
                    "cls": _booking_class(b["status_text"]),
                    "info": {   # sichqoncha ustiga borganda ko'rsatiladigan ma'lumot (batafsili — bosilganda serverdan)
                        "id": b["id"], "guest": b["guest_name"], "arrival": b["arrival"], "departure": b["departure"] or "",
                        "arrival_at": b["check_in_at"] or b["arrival"], "departure_at": b["check_out_at"] or (b["departure"] or ""),
                        "nights": (dep - a).days, "bed": bed["label"], "status": _booking_class(b["status_text"]),
                        "channel": channel, "comment": comment, "ref": b["ref"] or "",
                        "total": b["total_amount"], "paid": b["paid_amount"], "balance": _balance(b), "currency": b["currency"] or "",
                    },
                })
    for g in ordered:
        g["free"] = [g["beds_total"] - o for o in g["occupied"]]

    # bugungi kartalar (butun bronlar bo'yicha, ko'rinish oralig'iga bog'liq emas)
    total_beds = sum(g["beds_total"] for g in ordered)
    arrivals = checked = departures = staying = not_arrived = 0
    for b in all_rows:
        a, dep = span(b)
        if not a:
            continue
        cls = _booking_class(b["status_text"])
        if a == today:
            arrivals += 1
            checked += 1 if cls != "new" else 0
            not_arrived += 1 if cls == "new" else 0
        if dep == today:
            departures += 1
        if a <= today < dep:
            staying += 1
    cleaning = sum(1 for r in rooms if r["manual_status"] == "cleaning")
    maintenance = sum(1 for r in rooms if r["manual_status"] == "maintenance")
    cards = {
        "total_beds": total_beds, "staying": staying, "load_pct": round(staying / total_beds * 100) if total_beds else 0,
        "arrivals": arrivals, "arrivals_checked_in": checked, "departures": departures, "not_arrived": not_arrived,
        "free": max(total_beds - staying, 0), "rooms": len(rooms), "cleaning": cleaning, "maintenance": maintenance,
        "ready": len(rooms) - cleaning - maintenance,
    }
    return {"days": day_list, "groups": ordered, "cards": cards, "has_data": bool(all_rows)}

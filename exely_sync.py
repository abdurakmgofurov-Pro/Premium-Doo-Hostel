# -*- coding: utf-8 -*-
"""Exely PMS'dan Xonalar moduliga ma'lumot olib kelish (FAQAT O'QISH).

  * xonalar sinxronlash: Exely'dagi xona/o'rinlar (`101.1`, `101.2` ...) bizdagi
    xona (`101`) + sig'im (o'rinlar soni) + tur + qavat bo'lib keladi;
  * bronlar: Exely bronlari `hostel_bookings` qatorlariga aylantiriladi
    (Excel importi bilan bir xil dedup/upsert mantig'i).

Bu modul Exely'ga hech narsa yozmaydi (qarang: exely_pms.py).
"""
import json
import re
import threading
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

from db import get_conn
from exely_pms import ExelyPmsError


# ----------------------------------------------------------------- xonalar

def normalize_type_name(name):
    """«4-местный номер (мужчины)» -> «4 kishilik (erkaklar)»; tanib bo'lmasa — o'zgarmaydi."""
    name = (name or "").strip()
    m = re.match(r"^(\d+)\s*-?\s*мест", name, re.IGNORECASE)
    if not m:
        return name
    low = name.lower()
    gender = " (erkaklar)" if "мужч" in low else " (ayollar)" if "женщ" in low else ""
    return f"{m.group(1)} kishilik{gender}"


def _type_capacity(exely_name, beds):
    m = re.match(r"^(\d+)", (exely_name or "").strip())
    return int(m.group(1)) if m else beds


def fetch_desired_rooms(client):
    """Exely'dan kerakli xona tuzilmasi: {"types": [...], "rooms": [...]}.
    Yozuvlar: xona nomi `101.2` -> xona `101` (nuqtagacha), o'rin — nuqtadan keyin."""
    beds = client.rooms()
    floors = client.floors_by_room_name()
    type_names = client.room_type_names()
    by_room = {}
    for b in beds:
        number = b["displayName"].split(".")[0].strip()
        by_room.setdefault(number, []).append(b)
    types = {}
    rooms = []
    for number, group in by_room.items():
        type_id = Counter(b["roomTypeId"] for b in group).most_common(1)[0][0]
        exely_type = type_names.get(str(type_id), "")
        tname = normalize_type_name(exely_type) or None
        if tname and tname not in types:
            types[tname] = {"name": tname, "capacity": _type_capacity(exely_type, len(group))}
        floor_txt = floors.get(group[0]["displayName"], "")
        rooms.append({
            "number": number, "floor": int(floor_txt) if floor_txt.strip().isdigit() else 1,
            "type_name": tname, "capacity": len(group),
        })
    rooms.sort(key=lambda r: (r["floor"], int(r["number"]) if r["number"].isdigit() else 10**9, r["number"]))
    return {"types": list(types.values()), "rooms": rooms}


def diff_rooms(desired):
    """Joriy baza bilan taqqoslab reja tuzadi (bazaga tegmaydi)."""
    conn = get_conn()
    local_types = {r["name"]: r for r in conn.execute("SELECT * FROM room_types")}
    local_rooms = {r["number"]: r for r in conn.execute("SELECT * FROM rooms")}
    type_by_id = {r["id"]: r["name"] for r in local_types.values()}
    open_stays = {r["room_id"]: r["c"] for r in conn.execute(
        "SELECT room_id, COUNT(*) c FROM stays WHERE check_out IS NULL GROUP BY room_id")}
    conn.close()

    types = [{**t, "action": "same" if t["name"] in local_types else "new"} for t in desired["types"]]
    rooms, seen = [], set()
    for d in desired["rooms"]:
        seen.add(d["number"])
        cur = local_rooms.get(d["number"])
        if not cur:
            rooms.append({**d, "action": "new", "changes": []})
            continue
        changes = []
        if cur["floor"] != d["floor"]:
            changes.append(("floor", cur["floor"], d["floor"]))
        if d["capacity"] != cur["capacity"]:
            changes.append(("capacity", cur["capacity"], d["capacity"]))
        cur_type = type_by_id.get(cur["room_type_id"])
        if d["type_name"] and cur_type != d["type_name"]:
            changes.append(("type", cur_type or "—", d["type_name"]))
        if not changes:
            rooms.append({**d, "action": "same", "changes": []})
        elif d["capacity"] < open_stays.get(cur["id"], 0):
            rooms.append({**d, "action": "blocked", "changes": changes})   # ichida odam bor — kichraytirib bo'lmaydi
        else:
            rooms.append({**d, "action": "update", "changes": changes})
    only_local = sorted(n for n in local_rooms if n not in seen)
    counts = Counter(r["action"] for r in rooms)
    return {"types": types, "rooms": rooms, "only_local": only_local, "counts": dict(counts),
            "new_types": sum(1 for t in types if t["action"] == "new")}


def apply_rooms(desired):
    """Rejani bazaga qo'llaydi: yo'q turlar/xonalar qo'shiladi, mavjudlarning
    faqat qavat/sig'im/turi yangilanadi (narx, izoh, faollik, qo'lda holat —
    tegilmaydi). Exely'da yo'q xonalar o'chirilmaydi. Qaytaradi (yangi, yangilangan)."""
    plan = diff_rooms(desired)
    conn = get_conn()
    try:
        for t in plan["types"]:
            if t["action"] == "new":
                conn.execute("INSERT INTO room_types (name, capacity, price, currency) VALUES (?,?,0,'UZS')",
                             (t["name"], t["capacity"]))
        type_ids = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM room_types")}
        added = updated = 0
        for r in plan["rooms"]:
            tid = type_ids.get(r["type_name"]) if r["type_name"] else None
            if r["action"] == "new":
                conn.execute(
                    "INSERT INTO rooms (number, floor, room_type_id, capacity, price, currency) VALUES (?,?,?,?,0,'UZS')",
                    (r["number"], r["floor"], tid, r["capacity"]))
                added += 1
            elif r["action"] == "update":
                conn.execute("UPDATE rooms SET floor=?, capacity=?, room_type_id=COALESCE(?, room_type_id) WHERE number=?",
                             (r["floor"], r["capacity"], tid, r["number"]))
                updated += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return added, updated


# ------------------------------------------------------------------ bronlar

def _person_name(pn):
    parts = [(pn or {}).get(k, "") for k in ("firstName", "middleName", "lastName")]
    return " ".join(p.strip() for p in parts if p and p.strip())


def reservation_to_rows(res, guest_name_of, room_names, type_names):
    """Bitta Exely broni -> hostel_bookings qatorlari (har bir roomStay = 1 o'rin = 1 qator).
    Bron raqami ref bo'ladi (bitta o'rinli bronda), ko'p o'rinlida `raqam/stayId`."""
    stays = res.get("roomStays") or []
    number = res["number"]
    customer = res.get("customer") or {}
    channel = ((res.get("channelInformation") or {}).get("channelName") or "").strip()
    comment = (res.get("customerComment") or "").strip().replace("\n", " ")[:120]
    note = " · ".join(x for x in (channel, comment) if x)
    rows = []
    for st in stays:
        status = res.get("reservationStatus") or ""
        if st.get("status") and st["status"] not in ("New", status):
            status = f"{status} / {st['status']}"
        gid = (st.get("guestsIds") or [None])[0]
        name = guest_name_of(gid, customer) or "—"
        rows.append({
            "ref": number if len(stays) == 1 else f"{number}/{st['pmsRoomStayId']}",
            "guest": name,
            "arrival": (st.get("checkInDateTime") or "")[:10],
            "departure": (st.get("checkOutDateTime") or "")[:10],
            "room_type": type_names.get(str(st.get("roomTypeId")), ""),
            "room": room_names.get(str(st.get("roomId")), ""),
            "status": status, "note": note,
        })
    return rows


class BookingFetchJob:
    """Fon oqimida Exely bronlarini yuklaydi (yuzlab tafsilot so'rovi — bir necha daqiqa)."""

    def __init__(self, client, start, end, by_modified):
        self.id = uuid.uuid4().hex[:12]
        self.client, self.start, self.end, self.by_modified = client, start, end, by_modified
        self.state = "running"          # running | done | error
        self.phase = "list"             # list | details
        self.done = self.total = 0
        self.rows, self.failed, self.error = [], [], None
        self.started = datetime.now()   # keyingi "yangilanganlarni olish" shu paytdan boshlanadi
        self.ts = time.time()
        self._lock = threading.Lock()
        self._guests = {}

    def _guest_name_of(self, gid, customer):
        if not gid or gid == customer.get("pmsPersonId"):
            return _person_name(customer.get("personName"))
        with self._lock:
            if gid in self._guests:
                return self._guests[gid]
        try:
            name = _person_name(self.client.guest(gid).get("guest", {}).get("personName"))
        except ExelyPmsError:
            name = ""
        name = name or _person_name(customer.get("personName"))
        with self._lock:
            self._guests[gid] = name
        return name

    def _one(self, number, room_names, type_names):
        try:
            res = self.client.reservation(number)
            rows = reservation_to_rows(res, self._guest_name_of, room_names, type_names)
        except Exception:
            with self._lock:
                self.failed.append(number)
                self.done += 1
            return
        with self._lock:
            self.rows.extend(rows)
            self.done += 1

    def run(self):
        try:
            numbers = []
            for state in ("Active", "Cancelled"):    # standart qidiruv bekor qilinganlarni QAYTARMAYDI
                numbers += self.client.search_reservation_numbers(self.start, self.end, self.by_modified, state)
            numbers = list(dict.fromkeys(numbers))
            room_names = {str(r["id"]): r["displayName"] for r in self.client.rooms()}
            type_names = {k: normalize_type_name(v) for k, v in self.client.room_type_names().items()}
            self.total, self.phase = len(numbers), "details"
            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(lambda n: self._one(n, room_names, type_names), numbers))
            self.state = "done"
        except Exception as e:                       # noqa: BLE001 — foydalanuvchiga xabar beramiz
            self.error = str(e)[:300]
            self.state = "error"


JOBS = {}
JOBS_LOCK = threading.Lock()


def start_booking_job(client, start, end, by_modified=False):
    """Bitta vaqtda bitta ish: agar yugurayotgani bo'lsa — o'sha qaytariladi."""
    with JOBS_LOCK:
        for old in [k for k, j in JOBS.items() if j.state != "running" and time.time() - j.ts > 3600]:
            del JOBS[old]
        for j in JOBS.values():
            if j.state == "running":
                return j
        job = BookingFetchJob(client, start, end, by_modified)
        JOBS[job.id] = job
    threading.Thread(target=job.run, daemon=True).start()
    return job


def get_job(job_id):
    with JOBS_LOCK:
        return JOBS.get(job_id)


# --------------------------------------------------- Exely bandlik (kunlik)

OCC_CHUNK_DAYS = 31          # Exely bir so'rovda shundan ko'p kun bermaydi
_last_recent_fetch = 0.0
RECENT_TTL = 300             # yangi (o'zgarishi mumkin) kunlarni 5 daqiqada bir marta qayta olamiz


def _chunks(days):
    """Saralangan sanalar ro'yxatini ketma-ket, <=31 kunlik bo'laklarga ajratadi."""
    out = []
    for d in days:
        if out and d == out[-1][1] + timedelta(days=1) and (d - out[-1][0]).days < OCC_CHUNK_DAYS:
            out[-1][1] = d
        else:
            out.append([d, d])
    return out


def exely_occupancy(client, start, end):
    """{sana(str): {"occ": band o'rinlar, "total": jami o'rinlar}}, xato(str|None).
    O'tib ketgan (qotgan) kunlar bazada saqlanadi — Exely'dan faqat yetishmagan
    yoki yangi kunlar so'raladi. Exely'ga faqat GET yuboriladi."""
    global _last_recent_fetch
    conn = get_conn()
    cached = {r["date"]: dict(r) for r in conn.execute(
        "SELECT * FROM exely_occupancy WHERE date BETWEEN ? AND ?", (start.isoformat(), end.isoformat()))}
    conn.close()

    recent_ok = time.time() - _last_recent_fetch < RECENT_TTL
    need, d = [], start
    while d <= end:
        c = cached.get(d.isoformat())
        final = c and c["fetched_at"][:10] >= (d + timedelta(days=2)).isoformat()
        if not final and not (c and recent_ok):
            need.append(d)
        d += timedelta(days=1)

    error = None
    if need:
        fetched = {}

        def load(chunk):
            total, rows = client.daily_occupancy(chunk[0], chunk[1])
            return [(r["date"], int(r.get("occupancyRoomCount") or 0), int(total)) for r in rows]

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(load, ch) for ch in _chunks(need)]
            for f in futures:
                try:
                    for ds, occ, total in f.result():
                        fetched[ds] = (occ, total)
                except Exception as e:                 # noqa: BLE001
                    error = str(e)[:200]
        if fetched:
            now = datetime.now().isoformat(timespec="seconds")
            conn = get_conn()
            conn.executemany(
                "INSERT INTO exely_occupancy (date, occ, total, fetched_at) VALUES (?,?,?,?)"
                " ON CONFLICT(date) DO UPDATE SET occ=excluded.occ, total=excluded.total, fetched_at=excluded.fetched_at",
                [(ds, occ, total, now) for ds, (occ, total) in fetched.items()])
            conn.commit()
            conn.close()
            for ds, (occ, total) in fetched.items():
                cached[ds] = {"date": ds, "occ": occ, "total": total, "fetched_at": now}
            if not error:
                _last_recent_fetch = time.time()
    return {ds: {"occ": c["occ"], "total": c["total"]} for ds, c in cached.items()}, error


# ------------------------------------------------------------------ vebhuklar

_RESERVATION_NO = re.compile(r"\b\d{8}-\d+-\d+\b")      # masalan 20260927-513623-1259437226


def extract_reservation_numbers(body_text):
    """Xabar tuzilmasiga bog'liq bo'lmagan holda matndan bron raqamlarini ajratadi."""
    return list(dict.fromkeys(_RESERVATION_NO.findall(body_text or "")))[:20]


_EVENT_TYPE = re.compile(r'"eventType"\s*:\s*"([^"]+)"')


def extract_event_types(body_text):
    """Exely xabaridagi hodisa turlari (masalan webpms:change_check_out_datetime)."""
    return list(dict.fromkeys(_EVENT_TYPE.findall(body_text or "")))[:10]


def record_event(source_ip, body, numbers):
    conn = get_conn()
    cur = conn.execute("INSERT INTO webhook_events (received_at, source_ip, body, numbers) VALUES (datetime('now','localtime'),?,?,?)",
                       (source_ip, body, ",".join(numbers)))
    event_id = cur.lastrowid
    conn.execute("DELETE FROM webhook_events WHERE id <= ?", (event_id - 2000,))   # jadval o'smasin
    conn.commit()
    conn.close()
    return event_id


def finish_event(event_id, status, note=""):
    conn = get_conn()
    conn.execute("UPDATE webhook_events SET status=?, note=? WHERE id=?", (status, note[:300], event_id))
    conn.commit()
    conn.close()


def list_events(limit=50):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM webhook_events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def sync_reservations(client, numbers):
    """Berilgan bronlarni Exely'dan (GET) olib hostel_bookings'ga upsert qiladi.
    Qaytaradi: (qatorlar soni, yuklanmagan bron raqamlari)."""
    import rooms as rm
    job = BookingFetchJob(client, None, None, False)
    room_names = {str(r["id"]): r["displayName"] for r in client.rooms()}
    type_names = {k: normalize_type_name(v) for k, v in client.room_type_names().items()}
    for n in numbers:
        job._one(n, room_names, type_names)
    if job.rows:
        rm.import_bookings(job.rows)
    return len(job.rows), job.failed


ACCESS_LOG_MAX = 5000
_HIDDEN_HEADERS = {"cookie", "authorization", "x-api-key", "proxy-authorization"}


def log_access(*, client_ip, remote_addr, method, outcome, headers, body_size, body_preview, event_id=None):
    """Vebhuk endpointiga kelgan har bir so'rovni yozadi. Maxfiy sarlavhalar (cookie,
    authorization, api-key) yashiriladi; URL'dagi kalit umuman saqlanmaydi."""
    safe = {k: ("[yashirildi]" if k.lower() in _HIDDEN_HEADERS else v) for k, v in headers.items()}
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO webhook_access_log (at, client_ip, remote_addr, x_forwarded_for, user_agent, method, path,"
        " outcome, content_type, body_size, body_preview, headers, event_id)"
        " VALUES (datetime('now','localtime'),?,?,?,?,?,?,?,?,?,?,?,?)",
        (client_ip, remote_addr, safe.get("X-Forwarded-For", ""), (safe.get("User-Agent", "") or "")[:300], method,
         "/webhooks/exely/***", outcome, safe.get("Content-Type", ""), body_size, (body_preview or "")[:500],
         json.dumps(safe, ensure_ascii=False)[:4000], event_id))
    conn.execute("DELETE FROM webhook_access_log WHERE id <= ?", (cur.lastrowid - ACCESS_LOG_MAX,))
    conn.commit()
    conn.close()


def list_access(limit=100):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM webhook_access_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def poll_modified(client, since, until):
    """Zaxira tekshiruv: [since, until] oralig'ida o'zgargan bronlarni (faol va bekor
    qilinganlarini) Exely'dan o'qib, hostel_bookings'ga upsert qiladi (faqat GET).
    Qaytaradi: (topilgan bronlar soni, qatorlar soni, yuklanmaganlar)."""
    numbers = []
    for state in ("Active", "Cancelled"):
        numbers += client.search_reservation_numbers(since, until, True, state)
    numbers = list(dict.fromkeys(numbers))
    if not numbers:
        return 0, 0, []
    rows, failed = sync_reservations(client, numbers)
    return len(numbers), rows, failed

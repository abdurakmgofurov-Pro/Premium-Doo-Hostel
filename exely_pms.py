# -*- coding: utf-8 -*-
"""Exely PMS API — FAQAT O'QISH klienti (xonalar, bronlar, mehmonlar).

Xavfsizlik qoidasi: bu modul Exely'dagi ma'lumotni HECH QACHON o'zgartirmaydi.
Barcha so'rovlar `_get` orqali faqat GET; yagona POST — OAuth token olish
(autentifikatsiya, ma'lumotga ta'sir qilmaydi). Yozuvchi endpointlar
(check-in, assign-rooms, process-payment va h.k.) bu yerda umuman yo'q.

Bazaviy manzillar:
  PMS:     https://connect.hopenapi.com/api/pms/v2/properties/{id}
  Content: https://connect.hopenapi.com/api/content/v1/properties/{id}
"""
import threading
import time
from datetime import datetime, timedelta

import requests

AUTH_URL = "https://connect.hopenapi.com/auth/token"
API = "https://connect.hopenapi.com/api"
RETRY_STATUSES = (429, 500, 502, 503, 504)


class ExelyPmsError(Exception):
    """Exely'dan javob olinmadi yoki xato javob keldi."""


class ExelyPmsClient:
    def __init__(self, client_id, client_secret, property_id):
        self.client_id = client_id
        self.client_secret = client_secret
        self.property_id = property_id
        self._token = None
        self._token_expiry = datetime.min
        self._token_lock = threading.Lock()
        self._local = threading.local()

    def _session(self):
        s = getattr(self._local, "s", None)
        if s is None:
            s = self._local.s = requests.Session()
        return s

    def _ensure_token(self):
        with self._token_lock:
            if self._token and datetime.now() < self._token_expiry:
                return self._token
            last = None
            for attempt in range(4):
                try:
                    resp = requests.post(AUTH_URL, data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id, "client_secret": self.client_secret,
                    }, timeout=20)
                    resp.raise_for_status()
                    payload = resp.json()
                    self._token = payload["access_token"]
                    self._token_expiry = datetime.now() + timedelta(seconds=payload.get("expires_in", 900) - 60)
                    return self._token
                except requests.RequestException as e:
                    last = e
                    time.sleep(1.5 * (attempt + 1))
            raise ExelyPmsError(f"token olinmadi: {last}")

    def _get(self, url, params=None):
        """Yagona so'rov yo'li (faqat GET). Tarmoq uzilishi va 429/5xx'da qayta uriniladi."""
        last = None
        for attempt in range(4):
            try:
                resp = self._session().get(
                    url, params=params, headers={"Authorization": f"Bearer {self._ensure_token()}"},
                    timeout=(10, 40),
                )
            except requests.RequestException as e:
                last = e
                self._local.s = None        # eskirgan ulanishni tashlab, yangisini olamiz
                time.sleep(1.5 * (attempt + 1))
                continue
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in RETRY_STATUSES:
                last = ExelyPmsError(f"HTTP {resp.status_code}")
                time.sleep(1.5 * (attempt + 1))
                continue
            raise ExelyPmsError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        raise ExelyPmsError(f"so'rov bajarilmadi: {last}")

    @property
    def _pms(self):
        return f"{API}/pms/v2/properties/{self.property_id}"

    # ------------------------------------------------------------ tuzilma

    def rooms(self):
        """Barcha xonalar/o'rinlar: [{id, displayName, roomTypeId, floorId}] (sahifalab)."""
        out, token = [], None
        for _ in range(100):
            params = {"pageToken": token} if token else {"maxPageSize": 100}
            data = self._get(self._pms + "/rooms", params)
            out.extend(data.get("rooms", []))
            token = data.get("nextPageToken")
            if not data.get("hasNextPage") or not token:
                return out
        raise ExelyPmsError("rooms: sahifalash tugamadi")

    def floors_by_room_name(self):
        """{displayName: qavat nomi} — bino/qavat tuzilmasidan."""
        inv = self._get(self._pms + "/obtain-accommodation-inventory")["accommodationInventory"]
        out = {}
        for b in inv.get("buildings", []):
            for f in b.get("floors", []):
                for r in f.get("rooms", []):
                    out[r["displayName"]] = f.get("name", "")
        return out

    def room_type_names(self):
        """{roomTypeId: nom} — Content API'dan."""
        data = self._get(f"{API}/content/v1/properties/{self.property_id}")
        return {str(rt["id"]): rt.get("name", "") for rt in data.get("roomTypes", [])}

    # ------------------------------------------------------------- bronlar

    def search_reservation_numbers(self, start, end, by_modified=False, state=None):
        """[(bron raqami)] — `start`/`end` datetime. by_modified=False: shu davrda
        turish (yashash) bor bronlar; True: shu davrda o'zgargan bronlar.
        Exely chegarasi: davr <= 365 kun.
        state: None (standart), "Active" yoki "Cancelled"."""
        fmt = "%Y-%m-%dT%H:%M"
        key = "Modify" if by_modified else "AffectPeriod"
        numbers, seen, token = [], set(), None
        for _ in range(1000):
            if token:
                params = {"pageToken": token}
            else:
                params = {f"start{key}DateTime": start.strftime(fmt), f"end{key}DateTime": end.strftime(fmt),
                          "maxPageSize": 100}
                if state:
                    params["state"] = state
            data = self._get(self._pms + "/reservations/search", params)
            for r in data.get("reservations", []):
                if r["number"] not in seen:     # sahifalar orasida takrorlar uchraydi
                    seen.add(r["number"])
                    numbers.append(r["number"])
            token = data.get("nextPageToken")
            if not data.get("hasNextPage") or not token:
                return numbers
        raise ExelyPmsError("reservations/search: sahifalash tugamadi")

    def reservation(self, number):
        return self._get(self._pms + f"/reservations/{number}")["reservation"]

    def guest(self, person_id):
        return self._get(self._pms + f"/guests/{person_id}")

    # ------------------------------------------------------------ tahlil

    def daily_occupancy(self, start_date, end_date):
        """Kunlik bandlik (PMS Analytics). Exely bir so'rovda ~31 kungacha beradi.
        Qaytaradi: (propertyRoomCount, [{date, occupancyRoomCount, ...}])."""
        data = self._get(
            f"{API}/pms-analytics/v1/properties/{self.property_id}/daily-occupancy",
            {"startStayDate": start_date.isoformat(), "endStayDate": end_date.isoformat()},
        )
        return data.get("propertyRoomCount") or 0, data.get("dailyOccupancies", [])

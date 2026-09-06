# -*- coding: utf-8 -*-
"""
Exely rasmiy Public API klienti (OAuth2 client_credentials).
================================================================
Bu modul Playwright/brauzer avtomatlashtirishsiz, to'g'ridan-to'g'ri
Exely'ning rasmiy API'siga ulanadi:
  - Auth:              https://connect.hopenapi.com/auth/token
  - Read Reservation:  https://connect.hopenapi.com/api/read-reservation/v1

API kalitlari: Exely Extranet -> Property settings -> API connections
(client_id / client_secret) config.json'da saqlanadi.
"""
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait as futures_wait
from datetime import datetime, timedelta

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Ba'zi tarmoq muhitlarida DNS/soket darajasidagi tiqilib qolish `requests`'ning
# o'z timeout parametriga bo'ysunmasligi mumkin. Global soket timeout shu turdagi
# "abadiy osilib qolish"ning oldini oladigan qo'shimcha himoya qatlami.
socket.setdefaulttimeout(25)

AUTH_URL = "https://connect.hopenapi.com/auth/token"
RESERVATION_BASE = "https://connect.hopenapi.com/api/read-reservation/v1"

# Read Reservation API cheklovlari (hujjatga ko'ra):
#   ro'yxat (bookings):  3 so'rov/sek, 100/daq
#   tafsilot (booking):  10 so'rov/sek, 200/daq
LIST_MIN_INTERVAL = 1.0 / 3
DETAIL_MIN_INTERVAL = 1.0 / 9  # xavfsizlik uchun 10 emas, 9 so'rov/sek


class ExelyApiClient:
    def __init__(self, client_id, client_secret, property_id):
        self.client_id = client_id
        self.client_secret = client_secret
        self.property_id = property_id
        self._token = None
        self._token_expiry = datetime.min
        self._last_list_call = 0.0
        self._last_detail_call = 0.0
        self._lock = threading.Lock()
        self._token_lock = threading.Lock()
        self._session_lock = threading.Lock()
        self._session = self._new_session()

    def _new_session(self):
        session = requests.Session()
        retry = Retry(
            total=3, backoff_factor=0.6,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry, pool_maxsize=20, pool_connections=20)
        session.mount("https://", adapter)
        return session

    def _recycle_session(self):
        """Yangi ulanishlar bilan yangi sessiya yaratadi (eskirgan/qotib qolgan
        keep-alive ulanishlar bilan bog'liq muammolarni oldini olish uchun)."""
        with self._session_lock:
            try:
                self._session.close()
            except Exception:
                pass
            self._session = self._new_session()

    def _get_session(self):
        with self._session_lock:
            return self._session

    def _ensure_token(self):
        with self._token_lock:
            if self._token and datetime.now() < self._token_expiry:
                return self._token
            resp = self._get_session().post(
                AUTH_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=20,
            )
            resp.raise_for_status()
            payload = resp.json()
            self._token = payload["access_token"]
            # xavfsizlik zaxirasi bilan 60 soniya oldin yangilaymiz
            self._token_expiry = datetime.now() + timedelta(seconds=payload.get("expires_in", 900) - 60)
            return self._token

    def _headers(self):
        return {"Authorization": f"Bearer {self._ensure_token()}"}

    def _throttle(self, which):
        """Thread-safe darajada so'rovlar orasidagi minimal intervalni ta'minlaydi.

        Lock faqat vaqt hisoblash uchun ushlanadi, sleep esa lock DAN TASHQARIDA
        chaqiriladi — aks holda bitta sekin oqim boshqa hammasini bloklab qo'yadi."""
        last_attr = "_last_list_call" if which == "list" else "_last_detail_call"
        min_interval = LIST_MIN_INTERVAL if which == "list" else DETAIL_MIN_INTERVAL
        with self._lock:
            now = time.monotonic()
            wait = min_interval - (now - getattr(self, last_attr))
            setattr(self, last_attr, max(now, getattr(self, last_attr) + min_interval))
        if wait > 0:
            time.sleep(wait)

    # Sahifalash sikllari uchun qattiq chegara — server "hasMoreData: true"ni
    # bir xil/tsiklik continueToken bilan cheksiz qaytarib yuborsa ham, fon
    # oqimi abadiy osilib qolmasligi uchun (har sahifada 1000 tagacha bron
    # kelishini hisobga olsak, bu chegara haqiqiy foydalanishda hech qachon
    # yetib bo'lmaydigan darajada katta).
    MAX_PAGES = 10000

    def list_booking_numbers(self, modified_from=None):
        """Barcha bron raqamlarini (sahifalab) qaytaradi."""
        numbers = []
        continue_token = None
        for _ in range(self.MAX_PAGES):
            self._throttle("list")
            params = {}
            if continue_token:
                params["continueToken"] = continue_token
            elif modified_from:
                params["modifiedFrom"] = modified_from
            resp = self._get_session().get(
                f"{RESERVATION_BASE}/properties/{self.property_id}/bookings",
                headers=self._headers(), params=params, timeout=(10, 20),
            )
            resp.raise_for_status()
            data = resp.json()
            for s in data.get("bookingSummaries", []):
                numbers.append(s["number"])
            if not data.get("hasMoreData"):
                return numbers
            continue_token = data.get("continueToken")
            if not continue_token:
                return numbers
        raise RuntimeError(f"list_booking_numbers: {self.MAX_PAGES} sahifadan keyin ham tugamadi")

    def list_booking_summaries(self):
        """Barcha bronlarning qisqa ma'lumotini (number, status, modifiedDateTime)
        qaytaradi — bron ro'yxati javobida bu maydonlar bepul keladi, shuning
        uchun bu chaqiruv har doim BARCHA bronlarni qamrab oladi (server tomonda
        `modifiedFrom` bo'yicha filtrlash ishlamasligi aniqlandi — sinovda bu
        parametr natijaga hech qanday ta'sir qilmadi), lekin o'zi arzon
        (sahifalab, 1000 tadan)."""
        summaries = []
        continue_token = None
        for _ in range(self.MAX_PAGES):
            self._throttle("list")
            params = {"continueToken": continue_token} if continue_token else {}
            resp = self._get_session().get(
                f"{RESERVATION_BASE}/properties/{self.property_id}/bookings",
                headers=self._headers(), params=params, timeout=(10, 20),
            )
            resp.raise_for_status()
            data = resp.json()
            summaries.extend(data.get("bookingSummaries", []))
            if not data.get("hasMoreData"):
                return summaries
            continue_token = data.get("continueToken")
            if not continue_token:
                return summaries
        raise RuntimeError(f"list_booking_summaries: {self.MAX_PAGES} sahifadan keyin ham tugamadi")

    def get_booking(self, number):
        self._throttle("detail")
        resp = self._get_session().get(
            f"{RESERVATION_BASE}/properties/{self.property_id}/bookings/{number}",
            headers=self._headers(), timeout=(10, 20),
        )
        resp.raise_for_status()
        return resp.json()["booking"]

    def _fetch_batch(self, numbers, max_workers, stall_timeout):
        """Bitta partiyani (numbers ro'yxati) parallel yuklaydi, to'xtab qolishdan himoyalangan holda."""
        results = [None] * len(numbers)
        done_flags = [False] * len(numbers)
        done = 0
        lock = threading.Lock()

        def worker(i, num):
            nonlocal done
            try:
                res = self.get_booking(num)
            except requests.exceptions.RequestException as e:
                res = {"number": num, "_error": str(e)}
            except Exception as e:  # kutilmagan xato ham butun jarayonni to'xtatmasin
                res = {"number": num, "_error": f"{type(e).__name__}: {e}"}
            with lock:
                results[i] = res
                done_flags[i] = True
                done += 1
            return res

        pool = ThreadPoolExecutor(max_workers=max_workers)
        try:
            futures = [pool.submit(worker, i, num) for i, num in enumerate(numbers)]
            last_done = 0
            last_progress_time = time.monotonic()
            while True:
                futures_wait(futures, timeout=3)
                with lock:
                    current_done = done
                if current_done >= len(numbers):
                    break
                if current_done > last_done:
                    last_done = current_done
                    last_progress_time = time.monotonic()
                elif time.monotonic() - last_progress_time > stall_timeout:
                    break  # bu partiya to'xtab qoldi — qolganini "timeout" deb belgilab, keyingi partiyaga o'tamiz
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

        for i, num in enumerate(numbers):
            if not done_flags[i]:
                results[i] = {"number": num, "_error": "timeout: so'rov belgilangan vaqtda javob bermadi"}
        return results

    def fetch_bookings_by_number(self, numbers, progress_cb=None, max_workers=6, stall_timeout=30, batch_size=100):
        """Berilgan bron raqamlari ro'yxati uchun to'liq tafsilotlarni yuklaydi.

        Ba'zi tarmoq muhitlarida uzoq davom etadigan ulanishlar vaqti-vaqti bilan
        "qotib qolishi" mumkin. Buning oldini olish uchun so'rovlar kichik
        partiyalarga (`batch_size`) bo'lib yuboriladi, har partiyadan keyin
        HTTP-sessiya yangilanadi (yangi ulanishlar bilan) va bitta partiyaning
        to'xtab qolishi butun jarayonni abadiy bloklamaydi — shu partiyaning
        qolgan a'zolari "timeout" deb belgilanib, keyingi partiyaga o'tiladi."""
        all_results = []
        total = len(numbers)
        for start in range(0, total, batch_size):
            batch = numbers[start:start + batch_size]
            batch_results = self._fetch_batch(batch, max_workers=max_workers, stall_timeout=stall_timeout)
            all_results.extend(batch_results)
            if progress_cb:
                progress_cb(len(all_results), total)
            self._recycle_session()

        # Tarmoq beqarorligi tufayli xato bo'lgan so'rovlarni bitta marta,
        # sekinroq va kichikroq partiyalarda qayta urinib ko'ramiz — bu
        # ma'lumot to'liqligini sezilarli darajada oshiradi.
        failed_idx = [i for i, r in enumerate(all_results) if r and r.get("_error")]
        if failed_idx:
            self._recycle_session()
            retry_numbers = [all_results[i]["number"] for i in failed_idx]
            retry_results = self._fetch_batch(retry_numbers, max_workers=max(2, max_workers // 2), stall_timeout=stall_timeout)
            for i, res in zip(failed_idx, retry_results):
                all_results[i] = res
            if progress_cb:
                progress_cb(total, total)

        return all_results

    def fetch_all_bookings(self, progress_cb=None, max_workers=6, stall_timeout=30, batch_size=100):
        """Barcha bronlarning to'liq tafsilotlarini qaytaradi (ro'yxat + parallel detail so'rovlari)."""
        numbers = self.list_booking_numbers()
        return self.fetch_bookings_by_number(
            numbers, progress_cb=progress_cb, max_workers=max_workers,
            stall_timeout=stall_timeout, batch_size=batch_size,
        )

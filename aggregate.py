# -*- coding: utf-8 -*-
"""Exely Public API'dan kelgan xom bron ma'lumotlarini moliyaviy hisobot uchun yig'ish."""
from collections import defaultdict
from datetime import datetime

CHANNEL_NAMES = {
    "Channel:BGC": "Booking.com",
    "Channel:HSW": "Hostelworld",
    "Channel:CTP": "Trip.com",
    "Channel:AGD": "Agoda",
    "Channel:EXP": "Expedia",
    "Channel:AB2": "Airbnb",
    "BookingEngine:Mobile": "Mobil sayt",
    "BookingEngine:PropertySite": "Rasmiy sayt",
    "PMS:None": "Stoykadan (to'g'ridan-to'g'ri)",
}

PAYMENT_METHOD_NAMES = {
    "Card": "Karta",
    "Cash": "Naqd pul",
    "ExternalSystem": "Tashqi tizim (OTA/onlayn to'lov)",
    "BankTransfer": "Bank o'tkazmasi",
    "Company": "Kompaniya hisobidan",
    "Voucher": "Vaucher",
    "Loyalty": "Bonus/loyalty",
    "AtArrival": "Kelganda to'lanadi (joyida)",
    "BankCardGuarantee": "Bank kartasi (kafolat)",
}


def channel_key(booking):
    src = booking.get("source") or {}
    return f"{src.get('type')}:{src.get('code')}"


def channel_name(key):
    return CHANNEL_NAMES.get(key, key)


def payment_method_name(code):
    return PAYMENT_METHOD_NAMES.get(code, code)


def _room_stay_info(booking):
    """roomStays'dan asosiy xona turi, tarif rejasi, kechalar soni va mehmonlar sonini oladi."""
    room_type = None
    rate_plan = None
    nights = None
    adults = 0
    children = 0
    for rs in booking.get("roomStays") or []:
        rt_name = (rs.get("roomType") or {}).get("name")
        if rt_name and not room_type:
            room_type = rt_name
        rate_plans = rs.get("ratePlans") or []
        if rate_plans and not rate_plan:
            rate_plan = rate_plans[0].get("name")
        guest_count = rs.get("guestCount") or {}
        adults += guest_count.get("adultCount") or 0
        children += len(guest_count.get("childAges") or [])
        if nights is None:
            stay_dates = rs.get("stayDates") or {}
            arr, dep = stay_dates.get("arrivalDateTime"), stay_dates.get("departureDateTime")
            if arr and dep:
                try:
                    # Faqat kalendar sanalar solishtiriladi (soatlar emas) —
                    # 20-may 14:00 dan 21-may 12:00 gacha 1 kecha, garchi
                    # oradan 24 soat o'tmagan bo'lsa ham.
                    d1 = datetime.fromisoformat(arr[:19]).date()
                    d2 = datetime.fromisoformat(dep[:19]).date()
                    nights = (d2 - d1).days
                except ValueError:
                    nights = None
    return room_type, rate_plan, nights, adults, children


def _payment_method(booking):
    guarantees = (booking.get("guaranteeInfo") or {}).get("guarantees") or []
    if not guarantees:
        return None
    code = guarantees[0].get("paymentMethod")
    return payment_method_name(code) if code else None


def _taxes_and_discounts(total):
    """Exely javobida bor, lekin hozirgacha o'qilmagan `total.taxes`/`total.discounts`."""
    taxes = [
        {"name": t.get("name") or t.get("code") or f"Soliq {t.get('index', '')}".strip(),
         "amount": t.get("amount") or 0.0}
        for t in (total.get("taxes") or [])
    ]
    discounts = [
        {"name": d.get("name") or d.get("discountType") or "Chegirma",
         "amount": d.get("amount") or 0.0, "percent": d.get("percent")}
        for d in (total.get("discounts") or [])
    ]
    return taxes, discounts


def _room_services(booking):
    """roomStays[].services — xonaga qo'shilgan xizmatlar (nonushta, parking, wifi va h.k.)."""
    services = []
    for rs in booking.get("roomStays") or []:
        for s in rs.get("services") or []:
            services.append({
                "name": s.get("name"),
                "price": (s.get("total") or {}).get("priceBeforeTax") or 0.0,
                "inclusive": bool(s.get("inclusive")),
            })
    return services


def _daily_rates(booking):
    """roomStays[].dailyRates — har bir kecha uchun alohida narx."""
    rates = []
    for rs in booking.get("roomStays") or []:
        for dr in rs.get("dailyRates") or []:
            rates.append({"date": (dr.get("date") or "")[:10], "price": dr.get("priceBeforeTax") or 0.0})
    return rates


def _extra_charges(booking):
    """roomStays[].extraStayCharges — erta kelish / kech ketish uchun qo'shimcha to'lov."""
    charges = []
    for rs in booking.get("roomStays") or []:
        ec = rs.get("extraStayCharges") or {}
        for key, label in (("earlyArrival", "Erta kelish"), ("lateDeparture", "Kech ketish")):
            item = ec.get(key)
            if item:
                price = (item.get("total") or {}).get("priceBeforeTax") or 0.0
                if price:
                    charges.append({"label": label, "amount": price})
    return charges


def _all_guests(booking):
    """roomStays[].guests — xonadagi BARCHA mehmonlar (bosh mehmon emas)."""
    names = []
    for rs in booking.get("roomStays") or []:
        for g in rs.get("guests") or []:
            name = f"{g.get('firstName', '')} {g.get('lastName', '')}".strip()
            if name and name not in names:
                names.append(name)
    return names


def flatten(booking):
    total = booking.get("total") or {}
    guarantee = booking.get("guaranteeInfo") or {}
    room_stays = booking.get("roomStays") or []
    arrival = None
    if room_stays:
        dates = [rs.get("stayDates", {}).get("arrivalDateTime") for rs in room_stays if rs.get("stayDates")]
        dates = [d for d in dates if d]
        if dates:
            arrival = min(dates)
    customer = booking.get("customer") or {}
    room_type, rate_plan, nights, adults, children = _room_stay_info(booking)

    currency = booking.get("currencyCode")
    revenue = total.get("priceBeforeTax") or 0.0
    prepaid = guarantee.get("totalPrepaid") or 0.0
    tax_amount = total.get("taxAmount") or 0.0
    price_after_tax = total.get("priceAfterTax") or 0.0
    if currency and currency not in ("UZS", "USD"):
        # Bron kamdan-kam EUR (yoki boshqa) valyutada kelishi mumkin — tizim
        # faqat UZS/USD bilan ishlagani uchun, Markaziy bank kursi asosida
        # darhol UZS'ga aylantiriladi (kurs topilmasa, xom valyutada qoladi
        # va boshqa joyda e'tiborsiz qoldiriladi).
        import db
        rate = db.get_exchange_rate_on(arrival[:10] if arrival else None, currency)
        if not rate:
            # Shu sanaga tegishli tarixiy kurs topilmasa (masalan EUR kursi
            # kuzatilishi hali yaqinda boshlangan bo'lsa) — eng so'nggi
            # ma'lum kursdan foydalaniladi, xom valyutada qoldirib
            # umuman hisobga olinmasligidan ko'ra to'g'riroq.
            rate = db.get_exchange_rate_on(None, currency)
        if rate:
            revenue *= rate
            prepaid *= rate
            tax_amount *= rate
            price_after_tax *= rate
            currency = "UZS"

    taxes, discounts = _taxes_and_discounts(total)
    cancellation = booking.get("cancellation") or {}

    return {
        "number": booking.get("number"),
        "status": booking.get("status"),
        "currency": currency,
        "revenue": revenue,
        "prepaid": prepaid,
        "channel_key": channel_key(booking),
        "channel_name": channel_name(channel_key(booking)),
        "created": booking.get("createdDateTime"),
        "arrival": arrival,
        "guest": f"{customer.get('firstName','')} {customer.get('lastName','')}".strip(),
        "room_type": room_type,
        "rate_plan": rate_plan,
        "nights": nights,
        "adults": adults,
        "children": children,
        "payment_method": _payment_method(booking),
        # Exely'dan kelib, ilgari hech qayerda ishlatilmagan qo'shimcha maydonlar:
        "tax_amount": tax_amount,
        "price_after_tax": price_after_tax,
        "taxes": taxes,
        "discounts": discounts,
        "room_services": _room_services(booking),
        "daily_rates": _daily_rates(booking),
        "extra_charges": _extra_charges(booking),
        "guests_all": _all_guests(booking),
        "cancel_penalty": cancellation.get("penaltyAmount"),
        "cancel_at": cancellation.get("cancelledDateTime"),
        "source_url": (booking.get("source") or {}).get("sourceUrl") or None,
    }


def aggregate_bookings(bookings):
    rows = [flatten(b) for b in bookings if not b.get("_error")]
    active = [r for r in rows if r["status"] == "Active"]
    cancelled = [r for r in rows if r["status"] == "Cancelled"]

    revenue_by_currency = defaultdict(float)
    prepaid_by_currency = defaultdict(float)
    count_by_currency = defaultdict(int)
    for r in active:
        revenue_by_currency[r["currency"]] += r["revenue"]
        prepaid_by_currency[r["currency"]] += r["prepaid"]
        count_by_currency[r["currency"]] += 1

    by_channel = defaultdict(lambda: {"count": 0, "revenue": defaultdict(float), "currency": None})
    for r in active:
        c = by_channel[r["channel_name"]]
        c["count"] += 1
        c["revenue"][r["currency"]] += r["revenue"]
        c["currency"] = r["currency"]

    by_month = defaultdict(lambda: defaultdict(float))
    count_month = defaultdict(lambda: defaultdict(int))
    for r in active:
        if r["arrival"]:
            try:
                dt = datetime.fromisoformat(r["arrival"].replace("Z", "+00:00"))
            except ValueError:
                continue
            key = dt.strftime("%Y-%m")
            by_month[key][r["currency"]] += r["revenue"]
            count_month[key][r["currency"]] += 1

    cancelled_value = defaultdict(float)
    for r in cancelled:
        cancelled_value[r["currency"]] += r["revenue"]

    by_room_type = defaultdict(lambda: {"count": 0, "nights_sum": 0, "revenue": defaultdict(float), "currency": None})
    by_rate_plan = defaultdict(lambda: {"count": 0, "revenue": defaultdict(float), "currency": None})
    by_payment_method = defaultdict(lambda: {"count": 0, "revenue": defaultdict(float), "currency": None})
    nights_sum, nights_count = 0, 0
    adults_sum, solo_count, group_count, with_children_count = 0, 0, 0, 0
    for r in active:
        if r["room_type"]:
            c = by_room_type[r["room_type"]]
            c["count"] += 1
            c["revenue"][r["currency"]] += r["revenue"]
            c["currency"] = r["currency"]
            if r["nights"]:
                c["nights_sum"] += r["nights"]
        if r["rate_plan"]:
            c = by_rate_plan[r["rate_plan"]]
            c["count"] += 1
            c["revenue"][r["currency"]] += r["revenue"]
            c["currency"] = r["currency"]
        pm = r["payment_method"] or "-"
        c = by_payment_method[pm]
        c["count"] += 1
        c["revenue"][r["currency"]] += r["revenue"]
        c["currency"] = r["currency"]
        if r["nights"]:
            nights_sum += r["nights"]
            nights_count += 1
        adults_sum += r["adults"] or 0
        if (r["adults"] or 0) <= 1 and not r["children"]:
            solo_count += 1
        else:
            group_count += 1
        if r["children"]:
            with_children_count += 1

    return {
        "total_bookings": len(rows),
        "active_count": len(active),
        "cancelled_count": len(cancelled),
        "cancellation_rate": round(len(cancelled) / len(rows) * 100, 1) if rows else 0,
        "revenue_by_currency": dict(revenue_by_currency),
        "prepaid_by_currency": dict(prepaid_by_currency),
        "count_by_currency": dict(count_by_currency),
        "cancelled_value_by_currency": dict(cancelled_value),
        "by_channel": {
            k: {"count": v["count"], "revenue": dict(v["revenue"]), "currency": v["currency"]}
            for k, v in by_channel.items()
        },
        "by_month": {k: dict(v) for k, v in by_month.items()},
        "count_month": {k: dict(v) for k, v in count_month.items()},
        "by_room_type": {
            k: {"count": v["count"], "avg_nights": round(v["nights_sum"] / v["count"], 1) if v["count"] else 0,
                "revenue": dict(v["revenue"]), "currency": v["currency"]}
            for k, v in by_room_type.items()
        },
        "by_rate_plan": {
            k: {"count": v["count"], "revenue": dict(v["revenue"]), "currency": v["currency"]}
            for k, v in by_rate_plan.items()
        },
        "by_payment_method": {
            k: {"count": v["count"], "revenue": dict(v["revenue"]), "currency": v["currency"]}
            for k, v in by_payment_method.items()
        },
        "stay_stats": {
            "avg_nights": round(nights_sum / nights_count, 1) if nights_count else 0,
            "avg_adults": round(adults_sum / len(active), 2) if active else 0,
            "solo_count": solo_count,
            "group_count": group_count,
            "with_children_count": with_children_count,
        },
        "rows": rows,
    }

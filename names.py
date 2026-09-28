# -*- coding: utf-8 -*-
"""Exely'dan kelgan xona turi va tarif rejasi nomlarini birlashtirish va tilga qarab ko'rsatish.

Exely bir xil narsani ba'zan ruscha, ba'zan inglizcha nom bilan qaytaradi
(«8-местный номер (мужчины)» / «8-bed room (men)»; «От стойки» / «From the counter»),
shuning uchun hisobotda bitta tur ikki marta chiqib qolardi. Har bir nom avval yagona
(kanonik) shaklga keltiriladi, ko'rsatishda esa foydalanuvchi tiliga o'giriladi.
Tanilmagan nomlar o'zgarishsiz qoladi.
"""
import re

# ------------------------------------------------------------------ xona turlari

_LEAD = re.compile(r"^\s*(\d+)\s*-?\s*(мест|bed|kishilik|person|people)", re.IGNORECASE)
_CANON = re.compile(r"^(\d+) kishilik(?: \((erkaklar|ayollar)\))?$")


def canon_room_type(name):
    """«8-местный номер (мужчины)» / «8-bed room (men)» -> «8 kishilik (erkaklar)»."""
    if not isinstance(name, str) or not name.strip():
        return name
    m = _LEAD.match(name)
    if not m:
        return name.strip()
    low = name.lower()
    if re.search(r"женщ|women|female|ayol", low):
        gender = " (ayollar)"
    elif re.search(r"мужч|\bmen\b|\bmale\b|erkak", low):
        gender = " (erkaklar)"
    else:
        gender = ""
    return f"{m.group(1)} kishilik{gender}"


def label_room_type(name, lang):
    if not isinstance(name, str):
        return name
    m = _CANON.match(name.strip())
    if not m:
        return name
    n, gender = m.groups()
    if lang == "ru":
        return f"{n}-местный" + {"erkaklar": " (мужчины)", "ayollar": " (женщины)"}.get(gender, "")
    if lang == "en":
        return f"{n}-bed dorm" + {"erkaklar": " (men)", "ayollar": " (women)"}.get(gender, "")
    return name


# ------------------------------------------------------------------ tarif rejalari

# kalit -> (turli tillardagi nomlar [kichik harfda], {til: ko'rsatiladigan nom})
_PLANS = {
    "from_counter": (("from the counter", "от стойки"),
                     {"ru": "От стойки", "en": "From the counter", "uz": "Resepshn narxi"}),
    "long_stay_breakfast": (("long stay with breakfast", "длительное проживание с завтраком"),
                            {"ru": "Длительное проживание с завтраком", "en": "Long stay with breakfast",
                             "uz": "Uzoq muddatli, nonushta bilan"}),
    "favorable": (("favorable pricing plan", "favorable tariff", "выгодный тариф"),
                  {"ru": "Выгодный тариф", "en": "Favorable pricing plan", "uz": "Qulay tarif"}),
    "favorable_agoda": (("favorable tariff & agoda", "favorable pricing plan & agoda", "выгодный тариф & agoda"),
                        {"ru": "Выгодный тариф & Agoda", "en": "Favorable tariff & Agoda", "uz": "Qulay tarif & Agoda"}),
    "standard_breakfast": (("standard rate with breakfast", "стандартный тариф с завтраком"),
                           {"ru": "Стандартный тариф с завтраком", "en": "Standard rate with breakfast",
                            "uz": "Standart tarif, nonushta bilan"}),
    "early_booking_breakfast": (("early booking with breakfast", "раннее бронирование с завтраком"),
                                {"ru": "Раннее бронирование с завтраком", "en": "Early booking with breakfast",
                                 "uz": "Erta bron, nonushta bilan"}),
}
_PLAN_BY_NAME = {n: key for key, (names, _) in _PLANS.items() for n in names}
_PLAN_BY_CANON = {labels["en"]: key for key, (_, labels) in _PLANS.items()}


def canon_rate_plan(name):
    """Tanilgan tarif nomlari yagona (inglizcha) shaklga keltiriladi; boshqalari o'zgarishsiz."""
    if not isinstance(name, str) or not name.strip():
        return name
    key = _PLAN_BY_NAME.get(" ".join(name.lower().split()))
    return _PLANS[key][1]["en"] if key else name.strip()


def label_rate_plan(name, lang):
    key = _PLAN_BY_CANON.get(name) if isinstance(name, str) else None
    return _PLANS[key][1].get(lang, name) if key else name

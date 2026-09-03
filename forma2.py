# -*- coding: utf-8 -*-
"""Forma 2 (Moliyaviy natijalar to'g'risidagi hisobot) qatorlarini hisoblash.

Ichki (boshqaruv) hisobot uchun soddalashtirilgan tuzilma — rasmiy
taqdim etishdan oldin buxgalter tomonidan tekshirilishi kerak."""


def build_forma2(agg, manual):
    rev = agg.get("revenue_by_currency", {}) if agg else {}
    grp = manual.get("by_group", {})

    def g(key, cur):
        return grp.get(key, {}).get(cur, 0.0)

    rows = []

    def add(key, label, uzs, usd, bold=False, indent=0):
        rows.append({"key": key, "label": label, "uzs": uzs, "usd": usd, "bold": bold, "indent": indent})

    extra_rev = manual.get("revenue_extra", {})
    tannarx_uzs, tannarx_usd = g("tannarx", "UZS"), g("tannarx", "USD")
    rev_uzs = rev.get("UZS", 0.0) + extra_rev.get("UZS", 0.0)
    rev_usd = rev.get("USD", 0.0) + extra_rev.get("USD", 0.0)
    yalpi_uzs, yalpi_usd = rev_uzs - tannarx_uzs, rev_usd - tannarx_usd

    sotish_uzs, sotish_usd = g("sotish", "UZS"), g("sotish", "USD")
    mamuriy_uzs, mamuriy_usd = g("mamuriy", "UZS"), g("mamuriy", "USD")
    boshqa_op_uzs, boshqa_op_usd = g("boshqa_operatsion", "UZS"), g("boshqa_operatsion", "USD")
    davr_uzs = sotish_uzs + mamuriy_uzs + boshqa_op_uzs
    davr_usd = sotish_usd + mamuriy_usd + boshqa_op_usd

    asosiy_uzs, asosiy_usd = yalpi_uzs - davr_uzs, yalpi_usd - davr_usd

    moliyaviy_uzs, moliyaviy_usd = g("moliyaviy", "UZS"), g("moliyaviy", "USD")
    soliqqacha_uzs, soliqqacha_usd = asosiy_uzs - moliyaviy_uzs, asosiy_usd - moliyaviy_usd

    soliq_uzs, soliq_usd = g("soliq", "UZS"), g("soliq", "USD")
    sof_uzs, sof_usd = soliqqacha_uzs - soliq_uzs, soliqqacha_usd - soliq_usd

    add("f2.010", "010. Mahsulot (xizmat)larni sotishdan sof tushum", rev_uzs, rev_usd)
    add("f2.020", "020. Sotilgan xizmatlar tannarxi", tannarx_uzs, tannarx_usd)
    add("f2.030", "030. Yalpi foyda (zarar)", yalpi_uzs, yalpi_usd, bold=True)
    add("f2.040", "040. Davr xarajatlari, jami:", davr_uzs, davr_usd)
    add("f2.040_sotish", "— Sotish xarajatlari", sotish_uzs, sotish_usd, indent=1)
    add("f2.040_mamuriy", "— Ma'muriy xarajatlar", mamuriy_uzs, mamuriy_usd, indent=1)
    add("f2.040_boshqa", "— Boshqa operatsion xarajatlar", boshqa_op_uzs, boshqa_op_usd, indent=1)
    add("f2.050", "050. Asosiy faoliyatdan foyda (zarar)", asosiy_uzs, asosiy_usd, bold=True)
    add("f2.060", "060. Moliyaviy xarajatlar", moliyaviy_uzs, moliyaviy_usd)
    add("f2.080", "080. Soliqqacha foyda (zarar)", soliqqacha_uzs, soliqqacha_usd, bold=True)
    add("f2.090", "090. Soliqlar va majburiy to'lovlar", soliq_uzs, soliq_usd)
    add("f2.100", "100. Sof foyda (zarar)", sof_uzs, sof_usd, bold=True)

    return rows

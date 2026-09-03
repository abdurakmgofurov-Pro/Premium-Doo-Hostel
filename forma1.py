# -*- coding: utf-8 -*-
"""Forma 1 (Balans hisoboti) — ikki tomonlama (Aktivlar = Majburiyat + Kapital).

Aktivlar: pul mablag'lari (kassa+bank) + debitorlik qarzi (kontragentlar
bizga qarzdor) + asosiy vositalar.
Majburiyat va kapital: kreditorlik qarzi (biz kontragentlarga qarzdormiz)
+ ustav kapitali + taqsimlanmagan foyda (davr boshidan buyon jamg'arilgan
sof foyda).

Bu — ichki (boshqaruv) hisobot: debitor/kreditor "Xarajatlar"/"Xizmatlar"
sahifasidagi kontragent+to'lov yozuvlaridan hisoblanadi, asosiy vositalar
va ustav kapitali qo'lda (Sozlamalar sahifasida) kiritiladi. Rasmiy
taqdim etishdan oldin buxgalter tomonidan tekshirilishi tavsiya etiladi."""


def build_forma1(cash, receivables, inventory, fixed_assets, payables, charter, retained):
    """Har bir argument — {"UZS": x, "USD": y} ko'rinishidagi dict."""
    rows = []

    def add(key, uzs, usd, bold=False, indent=0):
        rows.append({"key": key, "uzs": uzs, "usd": usd, "bold": bold, "indent": indent})

    assets_uzs = cash["UZS"] + receivables["UZS"] + inventory["UZS"] + fixed_assets["UZS"]
    assets_usd = cash["USD"] + receivables["USD"] + inventory["USD"] + fixed_assets["USD"]

    add("f1.section_assets", 0, 0, bold=True)
    add("f1.cash", cash["UZS"], cash["USD"], indent=1)
    add("f1.receivables", receivables["UZS"], receivables["USD"], indent=1)
    add("f1.inventory", inventory["UZS"], inventory["USD"], indent=1)
    add("f1.fixed_assets", fixed_assets["UZS"], fixed_assets["USD"], indent=1)
    add("f1.assets_total", assets_uzs, assets_usd, bold=True)

    liab_uzs = payables["UZS"]
    liab_usd = payables["USD"]
    equity_uzs = charter["UZS"] + retained["UZS"]
    equity_usd = charter["USD"] + retained["USD"]
    total_le_uzs = liab_uzs + equity_uzs
    total_le_usd = liab_usd + equity_usd

    add("f1.section_liab_equity", 0, 0, bold=True)
    add("f1.payables", payables["UZS"], payables["USD"], indent=1)
    add("f1.liabilities_total", liab_uzs, liab_usd, bold=True, indent=1)
    add("f1.charter_capital", charter["UZS"], charter["USD"], indent=1)
    add("f1.retained_earnings", retained["UZS"], retained["USD"], indent=1)
    add("f1.equity_total", equity_uzs, equity_usd, bold=True, indent=1)
    add("f1.liabilities_equity_total", total_le_uzs, total_le_usd, bold=True)

    add("f1.balance_diff", assets_uzs - total_le_uzs, assets_usd - total_le_usd)

    return rows

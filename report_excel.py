# -*- coding: utf-8 -*-
"""Aggregate qilingan API ma'lumoti + qo'lda kiritilgan tranzaksiyalardan Excel hisobot yaratish.
Barcha matnlar (varaq nomlari, sarlavhalar, izohlar, kategoriya/kanal/holat nomlari) `lang` bo'yicha tarjima qilinadi."""
from datetime import datetime

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

import names
from forma2 import build_forma2
from i18n import t, t_cat, t_cash_cat, t_group

HEADER_FILL = PatternFill(start_color="4B2E83", end_color="4B2E83", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)
TITLE_FONT = Font(bold=True, size=14)
BOLD = Font(bold=True)


def _style_header(ws, row=1, ncols=1):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT


def _autofit(ws, widths):
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[chr(64 + i)].width = w


def build_excel_report(agg, manual, output_path, lang="uz"):
    T = lambda key: t(key, lang)
    wb = openpyxl.Workbook()

    # --- Xulosa ---
    ws1 = wb.active
    ws1.title = T("xl.sheet_summary")
    ws1["A1"] = T("xl.title")
    ws1["A1"].font = TITLE_FONT
    ws1["A2"] = T("xl.prepared").format(
        dt=f"{datetime.now():%d.%m.%Y %H:%M}", total=agg["total_bookings"], active=agg["active_count"],
        cancelled=agg["cancelled_count"], rate=agg["cancellation_rate"])
    ws1["A2"].font = Font(italic=True)

    r = 4
    for col, key in enumerate(("xl.h_currency", "xl.h_bookings_count", "xl.h_total_revenue", "xl.h_total_prepaid"), start=1):
        ws1.cell(row=r, column=col, value=T(key)).font = BOLD
    _style_header(ws1, row=r, ncols=4)
    r += 1
    for cur in sorted(agg["revenue_by_currency"]):
        ws1.cell(row=r, column=1, value=cur)
        ws1.cell(row=r, column=2, value=agg["count_by_currency"].get(cur, 0))
        ws1.cell(row=r, column=3, value=round(agg["revenue_by_currency"].get(cur, 0), 2))
        ws1.cell(row=r, column=4, value=round(agg["prepaid_by_currency"].get(cur, 0), 2))
        r += 1
    r += 1
    ws1.cell(row=r, column=1, value=T("xl.manual_title")).font = BOLD
    for label_key, src in (("xl.income", "income"), ("xl.expense", "expense"), ("xl.unpaid_expense", "unpaid_expense")):
        r += 1
        ws1.cell(row=r, column=1, value=T(label_key))
        ws1.cell(row=r, column=2, value=f"UZS: {manual[src]['UZS']:,.2f}")
        ws1.cell(row=r, column=3, value=f"USD: {manual[src]['USD']:,.2f}")
    _autofit(ws1, [40, 22, 26, 24])

    # --- Kanallar bo'yicha ---
    ws2 = wb.create_sheet(T("xl.sheet_channels"))
    ws2.append([T("xl.h_channel"), T("xl.h_currency"), T("xl.h_bookings_count"), T("xl.h_total")])
    _style_header(ws2, ncols=4)
    for name, c in sorted(agg["by_channel"].items(), key=lambda x: -sum(x[1]["revenue"].values())):
        for cur, val in c["revenue"].items():
            ws2.append([names.label_channel(name, lang), cur, c["count"], round(val, 2)])
    _autofit(ws2, [35, 10, 14, 18])

    # --- Oylar bo'yicha ---
    ws3 = wb.create_sheet(T("xl.sheet_months"))
    ws3.append([T("xl.h_month"), T("xl.h_uzs_count"), T("xl.h_uzs_sum"), T("xl.h_usd_count"), T("xl.h_usd_sum")])
    _style_header(ws3, ncols=5)
    for month in sorted(agg["by_month"]):
        ws3.append([
            month,
            agg["count_month"][month].get("UZS", 0), round(agg["by_month"][month].get("UZS", 0), 2),
            agg["count_month"][month].get("USD", 0), round(agg["by_month"][month].get("USD", 0), 2),
        ])
    _autofit(ws3, [16, 14, 16, 14, 16])

    # --- Barcha bronlar ---
    ws4 = wb.create_sheet(T("xl.sheet_bookings"))
    ws4.append([T("xl.h_number"), T("xl.h_status"), T("xl.h_guest"), T("xl.h_currency"), T("xl.h_revenue"),
                T("xl.h_prepaid"), T("xl.h_channel"), T("xl.h_created"), T("xl.h_checkin")])
    _style_header(ws4, ncols=9)
    for row in agg["rows"]:
        ws4.append([
            row["number"], names.label_booking_status(row["status"], lang), row["guest"], row["currency"],
            round(row["revenue"], 2), round(row["prepaid"], 2), names.label_channel(row["channel_name"], lang),
            row["created"], row["arrival"],
        ])
    _autofit(ws4, [30, 12, 22, 9, 14, 18, 28, 20, 20])

    # --- Forma 2 ---
    ws_f2 = wb.create_sheet(T("xl.sheet_forma2"))
    ws_f2["A1"] = T("xl.f2_title")
    ws_f2["A1"].font = TITLE_FONT
    ws_f2.merge_cells("A1:C1")
    r = 3
    ws_f2.cell(row=r, column=1, value=T("xl.f2_indicator"))
    ws_f2.cell(row=r, column=2, value="UZS")
    ws_f2.cell(row=r, column=3, value="USD")
    _style_header(ws_f2, row=r, ncols=3)
    for row in build_forma2(agg, manual):
        r += 1
        label = ("    " * row["indent"]) + (t(row["key"], lang) if row.get("key") else row["label"])
        ws_f2.cell(row=r, column=1, value=label).font = BOLD if row["bold"] else Font()
        ws_f2.cell(row=r, column=2, value=round(row["uzs"], 2)).font = BOLD if row["bold"] else Font()
        ws_f2.cell(row=r, column=3, value=round(row["usd"], 2)).font = BOLD if row["bold"] else Font()
    _autofit(ws_f2, [50, 20, 20])

    # --- Xarajatlar / kompaniyalar bilan hisob-kitob ---
    ws5 = wb.create_sheet(T("xl.sheet_expenses"))
    ws5.append([T("xl.h_date"), T("xl.h_type"), T("xl.h_category"), T("xl.h_f2group"), T("xl.h_counterparty"),
                T("xl.h_description"), T("xl.h_amount"), T("xl.h_currency"), T("xl.h_state")])
    _style_header(ws5, ncols=9)
    import db as _db
    _cat_group_map = _db.all_category_group_map()
    for tx in _db.list_transactions():
        group_key = _cat_group_map.get(tx["category"])
        group_label = t_group(group_key, lang) if (tx["type"] == "expense" and group_key) else "—"
        ws5.append([tx["date"], T("common.income") if tx["type"] == "income" else T("common.expense"),
                    t_cat(tx["category"], lang), group_label, tx["counterparty"], tx["description"],
                    tx["amount"], tx["currency"], T("xl.st_paid") if tx["status"] == "paid" else T("xl.st_unpaid")])
    _autofit(ws5, [14, 10, 30, 34, 24, 34, 14, 10, 10])

    ws1.cell(row=ws1.max_row + 2, column=1, value=T("xl.note")).alignment = Alignment(wrap_text=True)
    ws1.merge_cells(start_row=ws1.max_row, start_column=1, end_row=ws1.max_row, end_column=4)

    wb.save(output_path)


def build_cash_excel_report(rows, output_path, lang="uz"):
    """Kassa/Bank (cash_transactions) ro'yxatini alohida Excel faylga eksport qiladi —
    joriy filtr (davr/turi/statya/kontragent) bilan chaqiriladi, shu ro'yxatning o'zi yoziladi."""
    T = lambda key: t(key, lang)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = T("xl.sheet_cash")
    ws.append([T("xl.h_date"), T("xl.h_type"), T("xl.h_account"), T("xl.h_label"), T("xl.h_cf_code"),
               T("xl.h_counterparty"), T("xl.h_description"), T("xl.h_amount"), T("xl.h_currency")])
    _style_header(ws, ncols=9)
    for r in rows:
        ws.append([
            r["date"], T("common.income") if r["type"] == "income" else T("common.expense"),
            T("xl.src_bank") if r["source"] == "bank" else T("xl.src_kassa"), r.get("note_label") or "",
            t_cash_cat(r["category"], lang), r["counterparty"], r["description"], r["amount"], r["currency"],
        ])
    _autofit(ws, [14, 10, 10, 24, 30, 24, 34, 14, 10])
    wb.save(output_path)

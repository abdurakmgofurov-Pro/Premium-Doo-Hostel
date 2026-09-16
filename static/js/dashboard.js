"use strict";
(() => {
  // src/dashboard.ts
  var fmt = (n) => (n ?? 0).toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  var fmtInt = (n) => Math.round(n ?? 0).toLocaleString("ru-RU");
  var SERIES = ["var(--series-1)", "var(--series-2)", "var(--series-3)", "var(--series-4)", "var(--series-5)", "var(--series-6)"];
  var fmtDisp = (n) => window.DISPLAY_CURRENCY === "UZS" ? fmtInt(n) : fmt(n);
  function toDisplay(uzs, usd) {
    uzs = uzs || 0;
    usd = usd || 0;
    const rate = window.EXCHANGE_RATE;
    if (window.DISPLAY_CURRENCY === "USD") return usd + (rate ? uzs / rate : 0);
    return uzs + (rate ? usd * rate : 0);
  }
  function setStatus(status, lastSuccess, error, progress) {
    const pill = document.getElementById("statusPill");
    pill.className = "pill " + (status === "ok" ? "ok" : status === "error" ? "error" : "loading");
    if (status === "ok") {
      const d = lastSuccess ? new Date(lastSuccess) : null;
      const locale = window.LANG === "ru" ? "ru-RU" : window.LANG === "en" ? "en-GB" : "uz-UZ";
      pill.innerHTML = `<span class="dot pulse"></span>${window.T["dash.status_live_prefix"]}${d ? d.toLocaleString(locale) : "-"}`;
    } else if (status === "error") {
      pill.innerHTML = `<span class="dot"></span>${window.T["dash.status_error_prefix"]}${error || window.T["dash.status_unknown"]}`;
    } else {
      pill.innerHTML = `<span class="dot pulse"></span>${window.T["dash.status_bookings_loading"]}`;
    }
    const note = document.getElementById("progressNote");
    note.textContent = progress && progress.total ? `${progress.done} / ${progress.total} ${window.T["dash.progress_suffix"]}` : "";
  }
  function renderBreakdown(byMap) {
    const list = Object.entries(byMap || {}).map(([name, s]) => {
      const cur = s.currency;
      const nativeVal = s.revenue && s.revenue[cur] || 0;
      return [name, s, toDisplay(cur === "UZS" ? nativeVal : 0, cur === "USD" ? nativeVal : 0)];
    });
    list.sort((a, b) => b[2] - a[2]);
    if (!list.length) return `<div class="empty">${window.T["dash.no_data"]}</div>`;
    const max = Math.max(...list.map(([, , v]) => v));
    const legend = list.map(([name], i) => `<div class="legend-item"><span class="legend-dot" style="background:${SERIES[i % SERIES.length]}"></span>${name}</div>`).join("");
    const rows = list.map(([name, s, val], i) => {
      const pct = max ? val / max * 100 : 0;
      return `<div class="hbar-row">
      <div class="hbar-label">${name.length > 18 ? name.slice(0, 17) + "\u2026" : name}</div>
      <div class="hbar-track"><div class="hbar-fill" style="width:${pct}%;background:${SERIES[i % SERIES.length]}"></div></div>
      <div class="hbar-value mono">${fmtDisp(val)} <span style="color:var(--ink-muted);font-weight:400">(${s.count})</span></div>
    </div>`;
    }).join("");
    return `<div class="legend">${legend}</div>${rows}`;
  }
  function renderDonut(byMap) {
    const list = Object.entries(byMap || {}).map(([name, s]) => {
      const cur = s.currency;
      const nativeVal = s.revenue && s.revenue[cur] || 0;
      return [name, s, toDisplay(cur === "UZS" ? nativeVal : 0, cur === "USD" ? nativeVal : 0)];
    });
    list.sort((a, b) => b[2] - a[2]);
    if (!list.length) return `<div class="empty">${window.T["dash.no_data"]}</div>`;
    const MAX_SLICES = 5;
    let shown = list.slice(0, MAX_SLICES);
    const rest = list.slice(MAX_SLICES);
    if (rest.length) {
      const restVal = rest.reduce((s, [, , v]) => s + v, 0);
      const restCount = rest.reduce((s, [, r]) => s + r.count, 0);
      shown = shown.concat([[window.T["dash.other_slice"], { count: restCount }, restVal]]);
    }
    const total = shown.reduce((s, [, , v]) => s + v, 0);
    let acc = 0;
    const segments = shown.map(([, , v], i) => {
      const pct = total ? v / total * 100 : 0;
      const start = acc;
      acc += pct;
      return `${SERIES[i % SERIES.length]} ${start}% ${acc}%`;
    }).join(", ");
    const legend = shown.map(
      ([name, s, v], i) => `
    <div class="donut-legend-row">
      <span class="dl-dot" style="background:${SERIES[i % SERIES.length]}"></span>
      <span class="dl-name">${name}</span>
      <span class="dl-value mono">${fmtDisp(v)} <span style="color:var(--ink-muted);font-weight:400">(${s.count})</span></span>
    </div>`
    ).join("");
    return `<div class="donut-card-body">
    <div class="donut" style="background:conic-gradient(${segments})">
      <div class="donut-hole">
        <div class="donut-total mono">${fmtDisp(total)}</div>
        <div class="donut-total-label">${window.DISPLAY_CURRENCY}</div>
      </div>
    </div>
    <div class="donut-legend">${legend}</div>
  </div>`;
  }
  function renderStayStats(stats) {
    if (!stats) return `<div class="empty">${window.T["dash.no_data"]}</div>`;
    const items = [
      [window.T["dash.stat_avg_nights"], stats.avg_nights],
      [window.T["dash.stat_avg_adults"], stats.avg_adults],
      [window.T["dash.stat_solo"], fmtInt(stats.solo_count)],
      [window.T["dash.stat_group"], fmtInt(stats.group_count)],
      [window.T["dash.stat_with_children"], fmtInt(stats.with_children_count)]
    ];
    return `<div class="kpi-row">` + items.map(([label, val]) => `<div class="kpi"><div class="label">${label}</div><div class="value mono">${val}</div></div>`).join("") + `</div>`;
  }
  function renderTrendChart(byMonth, countMonth) {
    const months = Object.keys(byMonth || {}).sort();
    if (!months.length) return `<div class="empty">${window.T["dash.no_data"]}</div>`;
    const values = months.map((m) => toDisplay(byMonth[m].UZS, byMonth[m].USD));
    const max = Math.max(1, ...values);
    const n = months.length;
    const xPct = (i) => n > 1 ? i / (n - 1) * 100 : 50;
    const yBottomPct = (v) => 5 + v / max * 90;
    const yTopPct = (v) => 100 - yBottomPct(v);
    const pathLine = values.map((v, i) => `${i === 0 ? "M" : "L"}${xPct(i).toFixed(2)},${yTopPct(v).toFixed(2)}`).join(" ");
    const pathArea = pathLine + ` L${xPct(n - 1).toFixed(2)},100 L${xPct(0).toFixed(2)},100 Z`;
    const dots = values.map((v, i) => {
      const monthCounts = (countMonth || {})[months[i]] || {};
      const cnt = (monthCounts.UZS || 0) + (monthCounts.USD || 0);
      return `<div class="trend-dot" style="left:${xPct(i)}%;bottom:${yBottomPct(v)}%"
      title="${months[i]}: ${fmtDisp(v)} ${window.DISPLAY_CURRENCY}, ${cnt} ${window.T["dash.booking_word"]}"></div>`;
    }).join("");
    const labelEvery = Math.max(1, Math.ceil(n / 8));
    const labels = months.map((m, i) => i % labelEvery === 0 || i === n - 1 ? `<div class="trend-label" style="left:${xPct(i)}%">${m.slice(5, 7)}/${m.slice(2, 4)}</div>` : "").join("");
    return `<div class="trend-wrap">
    <svg class="trend-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
      <defs><linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="var(--accent)" stop-opacity="0.35"/>
        <stop offset="100%" stop-color="var(--accent)" stop-opacity="0"/>
      </linearGradient></defs>
      <path d="${pathArea}" fill="url(#trendFill)" stroke="none"/>
      <path d="${pathLine}" fill="none" stroke="var(--accent-light)" stroke-width="1.4" vector-effect="non-scaling-stroke"/>
    </svg>
    <div class="trend-dots">${dots}</div>
    <div class="trend-labels">${labels}</div>
  </div>`;
  }
  function renderNetResultHero(agg, manual) {
    const revenue = toDisplay(agg.revenue_by_currency?.UZS, agg.revenue_by_currency?.USD);
    const income = toDisplay(manual.income?.UZS, manual.income?.USD);
    const expense = toDisplay(manual.expense?.UZS, manual.expense?.USD);
    const net = revenue + income - expense;
    const totalIn = revenue + income;
    const pctExpense = totalIn > 0 ? Math.min(100, expense / totalIn * 100) : 0;
    const pctNet = 100 - pctExpense;
    return `
    <div class="result-hero">
      <div class="rh-value mono ${net >= 0 ? "good" : "bad"}">${fmtDisp(net)} ${window.DISPLAY_CURRENCY}</div>
      <div class="rh-label">${window.T["dash.table_net"]}</div>
    </div>
    <div class="result-stats">
      <div class="rs-item"><div class="rs-label">${window.T["dash.table_exely_revenue"]}</div><div class="rs-value mono">${fmtDisp(revenue)}</div></div>
      <div class="rs-item"><div class="rs-label">${window.T["dash.table_extra_income"]}</div><div class="rs-value mono">${fmtDisp(income)}</div></div>
      <div class="rs-item"><div class="rs-label">${window.T["dash.table_expense"]}</div><div class="rs-value mono" style="color:var(--bad)">${fmtDisp(expense)}</div></div>
    </div>
    <div class="comp-bar">
      <span style="width:${pctNet}%;background:linear-gradient(90deg,var(--good),#22d3ee)"></span>
      <span style="width:${pctExpense}%;background:var(--bad)"></span>
    </div>
    <div class="comp-legend">
      <div class="comp-item"><span class="comp-dot" style="background:var(--good)"></span>${window.T["dash.table_net"]} (${pctNet.toFixed(0)}%)</div>
      <div class="comp-item"><span class="comp-dot" style="background:var(--bad)"></span>${window.T["dash.table_expense"]} (${pctExpense.toFixed(0)}%)</div>
    </div>
    <div class="note">${window.T["dash.net_note"]}</div>`;
  }
  var ICONS = {
    hash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="9" x2="20" y2="9"/><line x1="4" y1="15" x2="20" y2="15"/><line x1="10" y1="3" x2="8" y2="21"/><line x1="16" y1="3" x2="14" y2="21"/></svg>',
    up: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 17l6-6 4 4 6-8"/><path d="M14 7h6v6"/></svg>',
    down: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7l6 6 4-4 6 8"/><path d="M14 17h6v-6"/></svg>',
    scale: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v18"/><path d="M5 8l-3 6a4 4 0 0 0 6 0z"/><path d="M19 8l-3 6a4 4 0 0 0 6 0z"/><path d="M5 8h14"/></svg>',
    trend: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 17l6-6 4 4 8-9"/><path d="M14 6h7v7"/></svg>',
    pie: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.2 15.3A10 10 0 1 1 12 2v10z"/></svg>',
    bed: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 18v-7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v7"/><path d="M3 18v2"/><path d="M21 18v2"/><path d="M3 13V7a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>',
    tag: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.6 12.3l-8.3 8.3a2 2 0 0 1-2.8 0l-6.8-6.8a2 2 0 0 1 0-2.8L11 2.7a2 2 0 0 1 1.4-.6H19a2 2 0 0 1 2 2v6.9a2 2 0 0 1-.4 1.3z"/><circle cx="16" cy="8" r="1.5"/></svg>',
    card: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2.5" y="5.5" width="19" height="13" rx="2"/><line x1="2.5" y1="10" x2="21.5" y2="10"/></svg>'
  };
  function render(payload) {
    setStatus(payload.status, payload.last_success, payload.error, payload.progress);
    const data = payload.data;
    const manual = payload.manual || {
      income: { UZS: 0, USD: 0 },
      expense: { UZS: 0, USD: 0 },
      unpaid_expense: { UZS: 0, USD: 0 },
      unpaid_income: { UZS: 0, USD: 0 },
      revenue_extra: { UZS: 0, USD: 0 },
      by_category: {},
      by_group: {}
    };
    const content = document.getElementById("content");
    if (!data) {
      content.innerHTML = `<div class="empty">${window.T["dash.empty_wait"]}</div>`;
      return;
    }
    const revenue = data.revenue_by_currency || {};
    const counts = data.count_by_currency || {};
    const otherCurAmount = window.DISPLAY_CURRENCY === "USD" ? (revenue.UZS || 0) + (manual.income.UZS || 0) + (manual.expense.UZS || 0) : (revenue.USD || 0) + (manual.income.USD || 0) + (manual.expense.USD || 0);
    const rateWarn = !window.EXCHANGE_RATE && otherCurAmount > 0;
    content.innerHTML = `
    ${rateWarn ? '<div class="note">' + window.T["reports.no_rate_note"] + "</div>" : ""}
    <div class="kpi-row">
      <div class="kpi">
        <div class="kpi-top"><div class="label">${window.T["dash.kpi_total_bookings"]}</div><div class="kpi-icon indigo">${ICONS.hash}</div></div>
        <div class="value mono">${fmtInt(data.total_bookings)}</div><div class="sub">${window.T["dash.kpi_active_prefix"]}${fmtInt(data.active_count)}</div>
      </div>
      <div class="kpi">
        <div class="kpi-top"><div class="label">${window.T["dash.kpi_revenue"]}</div><div class="kpi-icon green">${ICONS.up}</div></div>
        <div class="value mono">${fmtDisp(toDisplay(revenue.UZS, revenue.USD))} ${window.DISPLAY_CURRENCY}</div><div class="sub">${fmtInt((counts.UZS || 0) + (counts.USD || 0))} ${window.T["dash.kpi_in_bookings_suffix"]}</div>
      </div>
      <div class="kpi ${data.cancellation_rate > 15 ? "warn" : ""}">
        <div class="kpi-top"><div class="label">${window.T["dash.kpi_cancel_rate"]}</div><div class="kpi-icon red">${ICONS.down}</div></div>
        <div class="value mono">${data.cancellation_rate}%</div><div class="sub">${fmtInt(data.cancelled_count)} ${window.T["dash.kpi_booking_suffix"]}</div>
      </div>
    </div>

    <div class="card">
      <h2><span class="card-icon">${ICONS.scale}</span>${window.T["dash.card_net_result"]}</h2>
      ${renderNetResultHero(data, manual)}
    </div>

    <div class="card">
      <h2><span class="card-icon">${ICONS.trend}</span>${window.T["dash.card_months"]}</h2>
      ${renderTrendChart(data.by_month, data.count_month)}
    </div>

    <div class="card">
      <h2><span class="card-icon">${ICONS.bed}</span>${window.T["dash.card_stay_stats"]}</h2>
      ${renderStayStats(data.stay_stats)}
    </div>

    <div class="card-grid-2" style="margin-bottom:1.6rem">
      <div class="card">
        <h2><span class="card-icon">${ICONS.pie}</span>${window.T["dash.card_channels"]}</h2>
        ${renderDonut(data.by_channel)}
      </div>
      <div class="card">
        <h2><span class="card-icon">${ICONS.card}</span>${window.T["dash.card_payment_methods"]}</h2>
        ${renderBreakdown(data.by_payment_method)}
      </div>
    </div>

    <div class="card-grid-2">
      <div class="card">
        <h2><span class="card-icon">${ICONS.bed}</span>${window.T["dash.card_room_types"]}</h2>
        ${renderBreakdown(data.by_room_type)}
      </div>
      <div class="card">
        <h2><span class="card-icon">${ICONS.tag}</span>${window.T["dash.card_rate_plans"]}</h2>
        ${renderBreakdown(data.by_rate_plan)}
      </div>
    </div>
  `;
  }
  var PERIOD_QS = new URLSearchParams(window.location.search).toString();
  async function poll() {
    try {
      const res = await fetch("/api/data" + (PERIOD_QS ? "?" + PERIOD_QS : ""));
      const payload = await res.json();
      render(payload);
    } catch (e) {
      console.error(e);
    }
  }
  document.getElementById("refreshBtn").addEventListener("click", async () => {
    await fetch("/api/refresh", { method: "POST", headers: { "X-CSRFToken": window.CSRF_TOKEN || "" } });
    poll();
  });
  if (window.CAN_VIEW_REPORTS) {
    document.getElementById("excelBtn").addEventListener("click", () => {
      window.location.href = "/download/excel";
    });
  }
  poll();
  setInterval(poll, 15e3);
})();

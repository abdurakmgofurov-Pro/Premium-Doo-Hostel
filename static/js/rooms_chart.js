"use strict";
(() => {
  // src/rooms_chart.ts
  var T = (key) => window.T[key] || key;
  var sourceLabel = (s) => s === "At front desk" ? T("rooms.src_front_desk") : s;
  var STATUS_KEY = { new: "rooms.lg_new", in: "rooms.lg_in", out: "rooms.lg_out" };
  var money = (v, cur) => v === null || v === void 0 ? "\u2014" : `${v.toLocaleString("ru-RU", { maximumFractionDigits: 2 })} ${cur}`.trim();
  var dt = (s) => s ? s.replace("T", " ").slice(0, 16) : "\u2014";
  function el(tag, value = "", cls = "") {
    const e = document.createElement(tag);
    if (value) e.textContent = value;
    if (cls) e.className = cls;
    return e;
  }
  function statusBadge(status) {
    const s = el("span");
    s.append(el("i", "", `dot ${status}`), document.createTextNode(T(STATUS_KEY[status])));
    return s;
  }
  function row(label, value, cls = "tr") {
    const r = el("div", "", cls);
    r.append(el("span", label));
    const v = el("span");
    if (typeof value === "string") v.textContent = value;
    else v.append(value);
    r.append(v);
    return r;
  }
  var tip = el("div", "", "cc-tip");
  tip.hidden = true;
  document.body.appendChild(tip);
  function showTip(bar) {
    const i = JSON.parse(bar.dataset.tip || "{}");
    const type = bar.closest(".cc-bed")?.dataset.type || "";
    tip.replaceChildren(el("div", i.guest, "tt"));
    tip.append(row(T("rooms.tip_stay"), `${dt(i.arrival_at)} \u2192 ${dt(i.departure_at)}`));
    tip.append(row(T("rooms.tip_nights"), String(i.nights)), row(T("rooms.tip_bed"), i.bed));
    if (type) tip.append(row(T("rooms.tip_type"), type));
    tip.append(row(T("rooms.tip_status"), statusBadge(i.status)));
    tip.append(row(T("rooms.tip_channel"), `${sourceLabel(i.channel) || "\u2014"}${i.ref ? ` (${i.ref})` : ""}`));
    if (i.comment) tip.append(row(T("rooms.tip_comment"), i.comment));
    if (i.total !== null) {
      tip.append(
        row(T("rooms.tip_total"), money(i.total, i.currency)),
        row(T("rooms.tip_paid"), money(i.paid, i.currency)),
        row(T("rooms.tip_balance"), money(i.balance, i.currency))
      );
    }
  }
  function showUnassignedTip(cell) {
    const list = JSON.parse(cell.dataset.un || "[]");
    tip.replaceChildren(el("div", T("rooms.chart_unassigned"), "tt"));
    list.forEach((u) => tip.append(el("div", `${u.guest} \xB7 ${dt(u.arrival_at)} \u2192 ${dt(u.departure_at)}`, "li")));
    tip.append(el("div", T("rooms.un_click"), "li hint"));
  }
  function placeTip(ev) {
    const pad = 14;
    let x = ev.clientX + pad;
    let y = ev.clientY + pad;
    const r = tip.getBoundingClientRect();
    if (x + r.width > window.innerWidth - 8) x = ev.clientX - r.width - pad;
    if (y + r.height > window.innerHeight - 8) y = ev.clientY - r.height - pad;
    tip.style.left = `${Math.max(x, 8)}px`;
    tip.style.top = `${Math.max(y, 8)}px`;
  }
  var drawer = document.getElementById("ccDrawer");
  var drawerTitle = document.getElementById("ccDrawerTitle");
  var drawerBody = document.getElementById("ccDrawerBody");
  function closeDrawer() {
    if (drawer) drawer.hidden = true;
  }
  async function openDrawer(id, fallbackTitle) {
    if (!drawer || !drawerTitle || !drawerBody) return;
    drawerTitle.textContent = fallbackTitle;
    drawerBody.replaceChildren(el("div", T("rooms.dr_loading"), "dr-msg"));
    drawer.hidden = false;
    try {
      const resp = await fetch(`/rooms/chart/booking/${id}`, { headers: { Accept: "application/json" } });
      if (!resp.ok) throw new Error(String(resp.status));
      renderDetail(await resp.json());
    } catch {
      drawerBody.replaceChildren(el("div", T("rooms.dr_error"), "dr-msg"));
    }
  }
  function renderDetail(d) {
    if (!drawerTitle || !drawerBody) return;
    drawerTitle.textContent = `${d.bed} | ${d.guest}`;
    const sections = [];
    const add = (section, label, value) => {
      if (value === null || value === void 0 || value === "") return;
      section.push(row(label, value, "tr dr"));
    };
    const s1 = [];
    add(s1, T("rooms.tip_status"), statusBadge(d.status));
    add(s1, T("rooms.tip_ref"), d.ref);
    add(s1, T("rooms.dr_customer"), d.customer);
    add(s1, T("rooms.dr_phone"), d.phone);
    const s2 = [];
    add(s2, T("rooms.dr_checkin"), dt(d.actual_in_at || d.arrival_at));
    add(s2, T("rooms.dr_checkout"), dt(d.actual_out_at || d.departure_at));
    add(s2, T("rooms.dr_booked"), d.booked_at);
    add(s2, T("rooms.tip_nights"), d.nights === null ? "" : String(d.nights));
    add(s2, T("rooms.dr_rate"), d.rate_plan);
    add(s2, T("rooms.tip_type"), d.type);
    const s3 = [];
    add(s3, T("rooms.dr_adults"), d.adults === null ? "" : `${d.adults ?? 0} | ${d.children ?? 0}`);
    add(s3, T("rooms.dr_guest"), d.guest);
    const s4 = [];
    add(s4, T("rooms.dr_services"), d.services.join(", "));
    add(s4, T("rooms.dr_source"), d.source);
    add(s4, T("rooms.dr_guarantee"), d.guarantee);
    add(s4, T("rooms.tip_comment"), d.comment);
    const s5 = [];
    if (d.total !== null) {
      add(s5, T("rooms.dr_total"), money(d.total, d.currency));
      add(s5, T("rooms.dr_paid"), money(d.paid, d.currency));
      add(s5, T("rooms.dr_balance"), money(d.balance, d.currency));
    }
    sections.push(s1, s2, s3, s4, s5);
    const nodes = [];
    sections.filter((s) => s.length).forEach((s, idx) => {
      if (idx > 0) nodes.push(el("hr"));
      nodes.push(...s);
    });
    drawerBody.replaceChildren(...nodes);
  }
  var unDialog = document.getElementById("unDialog");
  var unTitle = document.getElementById("unTitle");
  var unBody = document.getElementById("unBody");
  function openUnassigned(cell) {
    if (!unDialog || !unTitle || !unBody) return;
    const list = JSON.parse(cell.dataset.un || "[]");
    unTitle.textContent = T("rooms.un_title").replace("{date}", cell.dataset.date || "");
    unBody.replaceChildren(
      ...list.map((u) => {
        const tr = document.createElement("tr");
        const open = el("button", "\u2261", "btn small");
        open.type = "button";
        open.addEventListener("click", () => {
          unDialog.close();
          void openDrawer(u.id, u.guest);
        });
        const cells = [
          el("td", u.ref || "\u2014", "mono"),
          el("td", u.guest),
          el("td", dt(u.arrival_at)),
          el("td", dt(u.departure_at)),
          el("td", money(u.paid, u.currency)),
          el("td", money(u.balance, u.currency))
        ];
        const last = document.createElement("td");
        last.append(open);
        tr.append(...cells, last);
        return tr;
      })
    );
    unDialog.showModal();
  }
  var scroll = document.querySelector(".cc-scroll");
  if (scroll) {
    scroll.addEventListener("mouseover", (ev) => {
      const target = ev.target;
      const bar = target.closest(".cc-bar");
      const un = target.closest(".un");
      if (bar && bar.dataset.tip) showTip(bar);
      else if (un && un.dataset.un) showUnassignedTip(un);
      else return;
      tip.hidden = false;
      placeTip(ev);
    });
    scroll.addEventListener("mousemove", (ev) => {
      if (!tip.hidden) placeTip(ev);
    });
    scroll.addEventListener("mouseout", (ev) => {
      const to = ev.relatedTarget;
      if (!to || !(to.closest(".cc-bar") || to.closest(".un"))) tip.hidden = true;
    });
    scroll.addEventListener("scroll", () => {
      tip.hidden = true;
    });
    scroll.addEventListener("click", (ev) => {
      const target = ev.target;
      const bar = target.closest(".cc-bar");
      const un = target.closest(".un");
      tip.hidden = true;
      if (bar && bar.dataset.tip) {
        const i = JSON.parse(bar.dataset.tip);
        void openDrawer(i.id, `${i.bed} | ${i.guest}`);
      } else if (un && un.dataset.un) {
        openUnassigned(un);
      }
    });
  }
  document.getElementById("ccDrawerClose")?.addEventListener("click", closeDrawer);
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape") closeDrawer();
  });
  document.addEventListener("click", (ev) => {
    if (!drawer || drawer.hidden) return;
    const target = ev.target;
    if (!target.closest("#ccDrawer") && !target.closest(".cc-bar") && !target.closest("#unDialog")) closeDrawer();
  });
  document.querySelectorAll("[data-close-dialog]").forEach(
    (b) => b.addEventListener("click", () => b.closest("dialog")?.close())
  );
})();
